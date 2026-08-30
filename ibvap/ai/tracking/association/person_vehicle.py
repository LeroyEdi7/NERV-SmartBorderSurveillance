from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.geometry import bbox_center, bbox_overlap_ratio, center_distance
from ibvap.ai.tracking.models import Track


def evaluate_entry_event(person_track: Track, vehicle_track: Track, config: TrackingConfig) -> dict | None:
    ratio = bbox_overlap_ratio(person_track.bbox, vehicle_track.bbox)
    if ratio < config.overlap_threshold:
        person_track.overlap_streak = 0
        return None
    person_track.overlap_streak += 1
    if person_track.overlap_streak >= config.sustained_frames:
        return {
            "event_candidate": "vehicle_person_association",
            "confidence": min(1.0, ratio),
            "streak_frames": person_track.overlap_streak,
        }
    return None

logger = logging.getLogger(__name__)


@dataclass
class _Pending:
    person_id: int
    vehicle_id: int
    confidence: float
    streak_frames: int
    last_person_bbox: tuple[float, float, float, float]
    last_vehicle_bbox: tuple[float, float, float, float]
    since_ts: float
    emitted: bool = False


@dataclass
class PersonVehicleAssociator:
    cfg: TrackingConfig
    streaks: dict[tuple[int, int], int] = field(default_factory=dict)
    pending: dict[tuple[int, int], _Pending] = field(default_factory=dict)
    emitted_pairs: set[tuple[int, int]] = field(default_factory=set)

    def update(self, tracks: list[Track], now_ts: float) -> list[dict]:
        persons = [t for t in tracks if t.class_name == "person"]
        vehicles = [t for t in tracks if t.class_name == "vehicle"]
        events: list[dict] = []
        seen: set[tuple[int, int]] = set()
        cell = max(8, int(self.cfg.spatial_grid_cell_px))

        vehicle_cells: dict[tuple[int, int], list[Track]] = {}
        for veh in vehicles:
            cx, cy = bbox_center(veh.bbox)
            vehicle_cells.setdefault((int(cx // cell), int(cy // cell)), []).append(veh)

        for person in persons:
            pcx, pcy = bbox_center(person.bbox)
            gx, gy = int(pcx // cell), int(pcy // cell)
            nearby: list[Track] = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nearby.extend(vehicle_cells.get((gx + dx, gy + dy), []))
            if not nearby:
                nearby = vehicles

            best_vehicle: Track | None = None
            best_ratio = 0.0
            for veh in nearby:
                ratio = bbox_overlap_ratio(person.bbox, veh.bbox)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_vehicle = veh

            if best_vehicle is None or best_ratio < self.cfg.overlap_threshold:
                person.overlap_streak = 0
                continue

            key = (person.track_id, best_vehicle.track_id)
            seen.add(key)
            self.streaks[key] = self.streaks.get(key, 0) + 1
            person.overlap_streak = self.streaks[key]
            needed = self.cfg.sustained_frames
            if self.streaks[key] < needed:
                continue

            conf = min(1.0, best_ratio)
            if key not in self.pending:
                self.pending[key] = _Pending(
                    person_id=person.track_id,
                    vehicle_id=best_vehicle.track_id,
                    confidence=conf,
                    streak_frames=self.streaks[key],
                    last_person_bbox=person.bbox,
                    last_vehicle_bbox=best_vehicle.bbox,
                    since_ts=now_ts,
                )
            else:
                pend = self.pending[key]
                pend.confidence = max(pend.confidence, conf)
                pend.streak_frames = self.streaks[key]
                pend.last_person_bbox = person.bbox
                pend.last_vehicle_bbox = best_vehicle.bbox

            if not self.cfg.confirm_on_disappear and key not in self.emitted_pairs:
                events.append(self._event(self.pending[key], confirmed_enter=False))
                self.emitted_pairs.add(key)

        dropped = [k for k in list(self.streaks) if k not in seen]
        person_ids = {t.track_id for t in persons}
        vehicle_by_id = {t.track_id: t for t in vehicles}

        for key in dropped:
            streak = self.streaks.pop(key)
            person_id, vehicle_id = key
            still_visible = person_id in person_ids
            if still_visible:
                logger.info(
                    "association_near_miss person=%s vehicle=%s streak=%s reason=walk_past",
                    person_id,
                    vehicle_id,
                    streak,
                )
                self.pending.pop(key, None)
                continue
            pend = self.pending.get(key)
            veh = vehicle_by_id.get(vehicle_id)
            if pend and self.cfg.confirm_on_disappear and key not in self.emitted_pairs:
                near = True
                if veh is not None:
                    near = center_distance(pend.last_person_bbox, veh.bbox) < 2.0 * max(
                        40.0, (veh.bbox[2] - veh.bbox[0])
                    )
                if near:
                    events.append(self._event(pend, confirmed_enter=True))
                    self.emitted_pairs.add(key)
                else:
                    logger.info(
                        "association_near_miss person=%s vehicle=%s streak=%s reason=lost_elsewhere",
                        person_id,
                        vehicle_id,
                        streak,
                    )
            self.pending.pop(key, None)

        expired = [
            k
            for k, p in self.pending.items()
            if now_ts - p.since_ts > self.cfg.disappear_confirm_sec and k not in seen
        ]
        for key in expired:
            self.pending.pop(key, None)
        return events

    def _event(self, pend: _Pending, confirmed_enter: bool) -> dict:
        return {
            "event_candidate": "vehicle_person_association",
            "event_type": "vehicle_person_association",
            "track_id": pend.person_id,
            "bbox": list(pend.last_person_bbox),
            "confidence": pend.confidence,
            "streak_frames": pend.streak_frames,
            "metadata": {
                "vehicle_track_id": pend.vehicle_id,
                "confirmed_enter": confirmed_enter,
            },
        }
