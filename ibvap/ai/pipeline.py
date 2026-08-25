"""Person 3 orchestration boundary used by the camera worker or Person 4 backend."""

from __future__ import annotations

from dataclasses import dataclass

from ai.anpr.service import ANPRService, ANPRServiceOutput
from ai.contracts import CommonEvent, TrackObservation
from ai.evidence.events import JsonlEventSink, face_event, plate_event
from ai.face.service import FaceRecognitionService, FaceServiceOutput


@dataclass(frozen=True, slots=True)
class Person3Output:
    face: FaceServiceOutput | None = None
    anpr: ANPRServiceOutput | None = None
    events: tuple[CommonEvent, ...] = ()


class Person3Pipeline:
    def __init__(
        self,
        face_service: FaceRecognitionService,
        anpr_service: ANPRService,
        event_sink: JsonlEventSink | None = None,
    ) -> None:
        self.face_service = face_service
        self.anpr_service = anpr_service
        self.event_sink = event_sink

    def process(self, observation: TrackObservation) -> Person3Output:
        object_type = observation.object_type.lower()
        events: list[CommonEvent] = []
        if object_type in {"person", "human"}:
            face_output = self.face_service.process(observation)
            if face_output.track and face_output.track.event_ready:
                events.append(
                    face_event(
                        face_output.track,
                        observation.timestamp,
                        observation.bbox,
                        observation.global_entity_id,
                    )
                )
            self._publish(events)
            return Person3Output(face=face_output, events=tuple(events))
        if object_type in {"vehicle", "car", "truck", "bus", "motorcycle"}:
            anpr_output = self.anpr_service.process(observation)
            if anpr_output.track and anpr_output.track.event_ready:
                events.append(
                    plate_event(
                        anpr_output.track,
                        observation.timestamp,
                        observation.camera_id,
                        observation.bbox,
                        observation.track_id,
                        observation.global_entity_id,
                    )
                )
            self._publish(events)
            return Person3Output(anpr=anpr_output, events=tuple(events))
        return Person3Output()

    def _publish(self, events: list[CommonEvent]) -> None:
        if self.event_sink:
            for event in events:
                self.event_sink.publish(event)
