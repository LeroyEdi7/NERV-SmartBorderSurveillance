import { useEffect, useState } from 'react';
import { SCENARIO_EVENTS } from '../data/scenario';

// Simulates ws://localhost:8000/ws/events by replaying the scripted
// demo scenario on a timer. To go live: delete the interval below and
// instead open a WebSocket, pushing each parsed message into setEvents
// the same way (newest event unshifted to the front).
export function useEventStream({ intervalMs = 3200, loop = true } = {}) {
  const [events, setEvents] = useState([]);
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setCursor((prev) => {
        const next = prev + 1;
        if (next > SCENARIO_EVENTS.length) {
          if (!loop) {
            clearInterval(id);
            return prev;
          }
          setEvents([]);
          return 0;
        }
        return next;
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, loop]);

  useEffect(() => {
    if (cursor === 0) return;
    setEvents(SCENARIO_EVENTS.slice(0, cursor).slice().reverse());
  }, [cursor]);

  const cameraStatus = {};
  for (const ev of events) {
    if (!cameraStatus[ev.camera_id]) {
      cameraStatus[ev.camera_id] = ev;
    }
  }

  return { events, cameraStatus, activeEvent: events[0] ?? null };
}
