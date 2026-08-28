// Demo scenario data, modeled directly on the 8-Day MVP spec (Section 9).
// Replace with live API/WebSocket data once the backend is wired up —
// see src/hooks/useEventStream.js for the single place that would change.

export const CAMERAS = [
  {
    camera_id: 'BOP-01',
    name: 'Border outpost camera 01',
    location: 'BOP-01',
    lat: 28.6139,
    lng: 77.209,
  },
  {
    camera_id: 'CHECK-01',
    name: 'Checkpost camera 01',
    location: 'CHECK-01',
    lat: 28.6205,
    lng: 77.2165,
  },
];

// Restricted zone polygon, associated with BOP-01 (ZONE-01)
export const ZONE = {
  zone_id: 'ZONE-01',
  zone_name: 'Restricted area',
  camera_id: 'BOP-01',
  severity: 'HIGH',
  polygon: [
    [28.6148, 77.2078],
    [28.6148, 77.2102],
    [28.6128, 77.2102],
    [28.6128, 77.2078],
  ],
};

// Scripted global track for G-017, matching the spec's timeline exactly.
export const SCENARIO_EVENTS = [
  {
    event_id: 'EVT-000121',
    event_type: 'person_detected',
    timestamp: '20:31',
    camera_id: 'BOP-01',
    entity: { entity_id: 'G-017', entity_type: 'person' },
    severity: 'LOW',
    label: 'Person detected',
  },
  {
    event_id: 'EVT-000122',
    event_type: 'intrusion',
    timestamp: '20:32',
    camera_id: 'BOP-01',
    entity: { entity_id: 'G-017', entity_type: 'person' },
    severity: 'HIGH',
    zone: ZONE,
    label: 'Restricted zone intrusion',
  },
  {
    event_id: 'EVT-000123',
    event_type: 'watchlist_match',
    timestamp: '20:33',
    camera_id: 'BOP-01',
    entity: { entity_id: 'G-017', entity_type: 'person' },
    severity: 'HIGH',
    label: 'Watchlist match — pending verification',
  },
  {
    event_id: 'EVT-000124',
    event_type: 'vehicle_person_association',
    timestamp: '20:34',
    camera_id: 'BOP-01',
    entity: { entity_id: 'G-017', entity_type: 'person' },
    severity: 'MEDIUM',
    label: 'Vehicle MH04AB1234 associated',
  },
  {
    event_id: 'EVT-000125',
    event_type: 'cross_camera_match',
    timestamp: '20:35',
    camera_id: 'CHECK-01',
    entity: { entity_id: 'G-017', entity_type: 'person' },
    severity: 'MEDIUM',
    label: 'Cross-camera vehicle match',
  },
  {
    event_id: 'EVT-000126',
    event_type: 'person_detected',
    timestamp: '20:36',
    camera_id: 'CHECK-01',
    entity: { entity_id: 'G-017', entity_type: 'person' },
    severity: 'MEDIUM',
    label: 'Person G-017 re-identified',
  },
];

export const SEVERITY_COLOR = {
  HIGH: 'var(--signal-red)',
  MEDIUM: 'var(--signal-blue)',
  LOW: 'var(--signal-teal)',
};
