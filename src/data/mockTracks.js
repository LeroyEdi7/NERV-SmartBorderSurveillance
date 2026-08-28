// Data store for Global Tracks and detailed target trajectories

export const INITIAL_TRACKS = [
  {
    id: 'G-017',
    status: 'ACTIVE',
    severity: 'HIGH',
    confidence: '98.4%',
    confidence_num: 98.4,
    last_camera: 'CHECK-01',
    last_time: '20:36',
    first_seen_time: '20:31',
    gender: 'Male',
    age: '28–32',
    clothing: 'Dark Jacket, Blue Denim',
    watchlist_status: 'Match #W-804 (Priority 1)',
    vehicle: {
      plate: 'MH04AB1234',
      type: 'Silver SUV',
      associated_time: '20:34:22',
      confidence: '94.2%'
    },
    event_count: 6,
    avatar: { bg: '#e14b3c', icon: 'user' },
    camera_journey: [
      { camera_id: 'BOP-01', name: 'Border outpost camera 01', time: '20:31:00', action: 'Target First Detected' },
      { camera_id: 'BOP-01', name: 'Border outpost camera 01', time: '20:32:15', action: 'Perimeter Intrusion Alert' },
      { camera_id: 'BOP-01', name: 'Border outpost camera 01', time: '20:33:04', action: 'Watchlist Feature Match' },
      { camera_id: 'ACCESS-ROAD', name: 'Access Road South', time: '20:34:22', action: 'Boarded Vehicle MH04AB1234' },
      { camera_id: 'CHECK-01', name: 'Checkpost camera 01', time: '20:35:10', action: 'Cross-Camera Re-ID Match' },
      { camera_id: 'CHECK-01', name: 'Checkpost camera 01', time: '20:36:00', action: 'Inspection Lane Lock' }
    ],
    map_path: [
      { lat: 28.6139, lng: 77.2090, label: 'BOP-01 Entry', time: '20:31', camera_id: 'BOP-01' },
      { lat: 28.6148, lng: 77.2078, label: 'Zone 1 Intrusion', time: '20:32', camera_id: 'BOP-01' },
      { lat: 28.6141, lng: 77.2092, label: 'Vehicle Boarded', time: '20:34', camera_id: 'ACCESS-ROAD' },
      { lat: 28.6205, lng: 77.2165, label: 'CHECK-01 Cross Match', time: '20:35', camera_id: 'CHECK-01' },
      { lat: 28.6210, lng: 77.2168, label: 'Inspection Lane', time: '20:36', camera_id: 'CHECK-01' }
    ],
    alerts: [
      { id: 'ALT-2026-9101', label: 'Restricted Zone Intrusion', severity: 'HIGH', time: '20:32:15' },
      { id: 'ALT-2026-9102', label: 'Watchlist Match #W-804', severity: 'HIGH', time: '20:33:04' },
      { id: 'ALT-2026-9103', label: 'Vehicle Association MH04AB1234', severity: 'MEDIUM', time: '20:34:22' },
      { id: 'ALT-2026-9104', label: 'Cross-Camera Match (CHECK-01)', severity: 'MEDIUM', time: '20:35:10' }
    ]
  },
  {
    id: 'G-021',
    status: 'ACTIVE',
    severity: 'HIGH',
    confidence: '96.1%',
    confidence_num: 96.1,
    last_camera: 'PERIMETER-03',
    last_time: '20:20',
    first_seen_time: '20:10',
    gender: 'Male',
    age: '30–35',
    clothing: 'Black Hoodie, Cargo Pants',
    watchlist_status: 'Match #W-912 (Restricted Entry)',
    vehicle: {
      plate: 'KA03MC8812',
      type: 'Dark Sedan',
      associated_time: '20:18:00',
      confidence: '91.8%'
    },
    event_count: 5,
    avatar: { bg: '#e14b3c', icon: 'user' },
    camera_journey: [
      { camera_id: 'GATE-WEST', name: 'West Outer Gate', time: '20:10:00', action: 'Entry Attempt' },
      { camera_id: 'PERIMETER-03', name: 'Perimeter Sensor Cam 03', time: '20:15:20', action: 'Fence Crossing' },
      { camera_id: 'PERIMETER-03', name: 'Perimeter Sensor Cam 03', time: '20:20:45', action: 'IR Sensor Alarm' }
    ],
    map_path: [
      { lat: 28.6100, lng: 77.2000, label: 'West Gate Entry', time: '20:10', camera_id: 'GATE-WEST' },
      { lat: 28.6110, lng: 77.2020, label: 'Perimeter Breached', time: '20:20', camera_id: 'PERIMETER-03' }
    ],
    alerts: [
      { id: 'ALT-2026-9106', label: 'Restricted Zone Intrusion', severity: 'HIGH', time: '20:20:45' },
      { id: 'ALT-2026-9120', label: 'Unregistered Vehicle KA03MC8812', severity: 'MEDIUM', time: '20:18:00' }
    ]
  },
  {
    id: 'G-024',
    status: 'MONITORED',
    severity: 'MEDIUM',
    confidence: '94.5%',
    confidence_num: 94.5,
    last_camera: 'CHECK-01',
    last_time: '20:05',
    first_seen_time: '19:40',
    gender: 'Male',
    age: '40–45',
    clothing: 'Grey Shirt, Glasses',
    watchlist_status: 'Watchlist Flag #W-210',
    vehicle: {
      plate: 'DL01XY9988',
      type: 'White Cargo Truck',
      associated_time: '20:05:12',
      confidence: '92.0%'
    },
    event_count: 4,
    avatar: { bg: '#e8a13d', icon: 'user' },
    camera_journey: [
      { camera_id: 'CHECK-01', name: 'Checkpost camera 01', time: '19:40:00', action: 'Cargo Bay Arrival' },
      { camera_id: 'CHECK-01', name: 'Checkpost camera 01', time: '20:05:12', action: 'Loitering Threshold Trigger' }
    ],
    map_path: [
      { lat: 28.6208, lng: 77.2170, label: 'Cargo Bay 4', time: '20:05', camera_id: 'CHECK-01' }
    ],
    alerts: [
      { id: 'ALT-2026-9108', label: 'Vehicle Loitering DL01XY9988', severity: 'MEDIUM', time: '20:05:12' }
    ]
  },
  {
    id: 'G-031',
    status: 'MONITORED',
    severity: 'MEDIUM',
    confidence: '97.2%',
    confidence_num: 97.2,
    last_camera: 'GATE-NORTH',
    last_time: '20:15',
    first_seen_time: '20:00',
    gender: 'Female',
    age: '25–30',
    clothing: 'Red Jacket, Black Denim',
    watchlist_status: 'Flagged Visitor',
    vehicle: null,
    event_count: 3,
    avatar: { bg: '#e8a13d', icon: 'user' },
    camera_journey: [
      { camera_id: 'GATE-NORTH', name: 'North Gate Entrance', time: '20:00:00', action: 'Turnstile Scan' },
      { camera_id: 'GATE-NORTH', name: 'North Gate Entrance', time: '20:15:30', action: 'Screening Station' }
    ],
    map_path: [
      { lat: 28.6250, lng: 77.2210, label: 'North Gate Turnstile', time: '20:15', camera_id: 'GATE-NORTH' }
    ],
    alerts: [
      { id: 'ALT-2026-9107', label: 'Watchlist Match #B-102', severity: 'HIGH', time: '20:15:30' }
    ]
  },
  {
    id: 'G-045',
    status: 'CLOSED',
    severity: 'LOW',
    confidence: '98.9%',
    confidence_num: 98.9,
    last_camera: 'SUBSTATION-01',
    last_time: '19:35',
    first_seen_time: '19:00',
    gender: 'Male',
    age: '35–40',
    clothing: 'High-Vis Vest, Helmet',
    watchlist_status: 'Clear / Verified Contractor',
    vehicle: {
      plate: 'MH12CD5678',
      type: 'Utility Pickup',
      associated_time: '19:05:00',
      confidence: '98.0%'
    },
    event_count: 4,
    avatar: { bg: '#34d9b4', icon: 'user' },
    camera_journey: [
      { camera_id: 'GATE-SOUTH', name: 'South Gate Entry', time: '19:00:00', action: 'Badge Scan' },
      { camera_id: 'SUBSTATION-01', name: 'Solar Substation 01', time: '19:35:10', action: 'Work Completed' }
    ],
    map_path: [
      { lat: 28.6135, lng: 77.2080, label: 'Substation Yard', time: '19:35', camera_id: 'SUBSTATION-01' }
    ],
    alerts: [
      { id: 'ALT-2026-9110', label: 'Contractor Re-identified G-112', severity: 'LOW', time: '19:35:10' }
    ]
  },
  {
    id: 'G-052',
    status: 'ACTIVE',
    severity: 'HIGH',
    confidence: '99.1%',
    confidence_num: 99.1,
    last_camera: 'BOP-01',
    last_time: '20:28',
    first_seen_time: '20:12',
    gender: 'Male',
    age: '29–34',
    clothing: 'Dark Coat, Tactical Boots',
    watchlist_status: 'Priority Watchlist Match #W-991',
    vehicle: {
      plate: 'MH02EF4321',
      type: 'Black Van',
      associated_time: '20:25:00',
      confidence: '96.5%'
    },
    event_count: 7,
    avatar: { bg: '#e14b3c', icon: 'user' },
    camera_journey: [
      { camera_id: 'PERIMETER-02', name: 'Perimeter Sensor Cam 02', time: '20:12:00', action: 'Movement Detected' },
      { camera_id: 'BOP-01', name: 'Border outpost camera 01', time: '20:25:00', action: 'Vehicle Association MH02EF4321' },
      { camera_id: 'BOP-01', name: 'Border outpost camera 01', time: '20:28:10', action: 'Restricted Zone Perimeter Tripwire' }
    ],
    map_path: [
      { lat: 28.6120, lng: 77.2050, label: 'Perimeter 02', time: '20:12', camera_id: 'PERIMETER-02' },
      { lat: 28.6139, lng: 77.2090, label: 'BOP-01 Tripwire', time: '20:28', camera_id: 'BOP-01' }
    ],
    alerts: [
      { id: 'ALT-2026-9140', label: 'Restricted Zone Breach #W-991', severity: 'HIGH', time: '20:28:10' },
      { id: 'ALT-2026-9141', label: 'Vehicle Association MH02EF4321', severity: 'MEDIUM', time: '20:25:00' }
    ]
  }
];
