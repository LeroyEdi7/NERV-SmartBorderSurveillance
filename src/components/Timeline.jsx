import './Timeline.css';
import { SCENARIO_EVENTS, SEVERITY_COLOR } from '../data/scenario';

export default function Timeline({ events }) {
  const seenIds = new Set(events.map((e) => e.event_id));
  const entityId = events[0]?.entity?.entity_id ?? SCENARIO_EVENTS[0].entity.entity_id;

  return (
    <div className="timeline">
      <div className="timeline__head">
        <span>Global track</span>
        <span className="timeline__entity">{entityId}</span>
      </div>

      <div className="timeline__track">
        <div className="timeline__line" />
        {SCENARIO_EVENTS.map((ev, i) => {
          const reached = seenIds.has(ev.event_id);
          const pos = (i / (SCENARIO_EVENTS.length - 1)) * 100;
          return (
            <div
              key={ev.event_id}
              className={`timeline__node ${reached ? 'is-reached' : ''}`}
              style={{ left: `${pos}%`, '--accent': SEVERITY_COLOR[ev.severity] }}
              title={ev.label}
            >
              <span className="timeline__dot" />
              <div className="timeline__tag">
                <span className="timeline__tag-time">{ev.timestamp}</span>
                <span className="timeline__tag-label">{ev.label}</span>
                <span className="timeline__tag-cam">{ev.camera_id}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
