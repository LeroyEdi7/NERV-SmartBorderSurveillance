import { useState, useMemo } from 'react';
import StatusBar   from './components/StatusBar';
import MainCCTVFeed from './components/MainCCTVFeed';
import CameraTile  from './components/CameraTile';
import TacticalMap  from './components/TacticalMap';
import AlertsFeed   from './components/AlertsFeed';

import ActiveAlertsPage from './components/ActiveAlertsPage';
import AlertDetailsModal from './components/AlertDetailsModal';
import GlobalTracksPage from './components/GlobalTracksPage';
import GlobalTrackDetailsModal from './components/GlobalTrackDetailsModal';
import { CAMERAS }  from './data/scenario';
import { useEventStream } from './hooks/useEventStream';
import './App.css';

export default function App() {
  const { events, cameraStatus } = useEventStream();
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard' | 'alerts' | 'tracks'
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState(null);

  // Manual camera focus state & toggle for auto-speaker view
  const [manualCamId, setManualCamId] = useState(null);
  const [isManualOverride, setIsManualOverride] = useState(false);

  // Determine top priority / latest anomaly camera automatically (Zoom/Meet active-speaker style)
  const autoCamId = useMemo(() => {
    if (!events || events.length === 0) return 'BOP-01';
    
    // 1. Look for highest priority active event (HIGH > MEDIUM > LOW)
    const highEvent = events.find((ev) => ev.severity === 'HIGH');
    if (highEvent?.camera_id) return highEvent.camera_id;

    const medEvent = events.find((ev) => ev.severity === 'MEDIUM');
    if (medEvent?.camera_id) return medEvent.camera_id;

    // 2. Default to newest event's camera or BOP-01
    return events[0]?.camera_id || 'BOP-01';
  }, [events]);

  // Selected camera feed for the main display
  const activeCamId = isManualOverride && manualCamId ? manualCamId : autoCamId;
  const activeCamera = CAMERAS.find((c) => c.camera_id === activeCamId) || CAMERAS[0];

  const handleSelectIndividualAlert = (ev) => {
    const formatted = {
      id: ev.event_id || 'ALT-2026-LIVE',
      event_type: ev.event_type || 'intrusion',
      type_label: ev.label || ev.event_type?.replace(/_/g, ' '),
      severity: ev.severity || 'HIGH',
      timestamp: `2026-08-27 ${ev.timestamp || '20:35'}`,
      time_relative: 'Just now',
      camera_id: ev.camera_id || 'BOP-01',
      camera_name: ev.camera_id === 'BOP-01' ? 'Border outpost camera 01' : 'Checkpost camera 01',
      global_id: ev.entity?.entity_id || 'G-017',
      description: `${ev.label || 'Security alert'} detected on sensor feed ${ev.camera_id || 'BOP-01'}`,
      status: 'NEW',
      confidence: '98.1%',
      zone: ev.zone?.zone_name || 'ZONE-01 (Restricted Perimeter)',
      location: ev.camera_id || 'Sector Alpha',
      coordinates: { lat: 28.6139, lng: 77.209 },
      entity: {
        type: ev.entity?.entity_type || 'Person',
        id: ev.entity?.entity_id || 'G-017',
        estimated_speed: '2.1 m/s',
        reid_score: '98.1%'
      },
      audit_trail: [
        { time: ev.timestamp || '20:35', note: 'Real-time alert triggered by Surveillance System' }
      ]
    };
    setSelectedAlert(formatted);
  };

  if (activeView === 'alerts') {
    return (
      <ActiveAlertsPage
        onBackToDashboard={() => setActiveView('dashboard')}
        liveEvents={events}
      />
    );
  }

  if (activeView === 'tracks') {
    return (
      <GlobalTracksPage
        onBackToDashboard={() => setActiveView('dashboard')}
      />
    );
  }

  return (
    <div className="dashboard">
      {/* ── Top Status Bar ── */}
      <StatusBar
        cameraCount={CAMERAS.length}
        activeView={activeView}
        onNavigate={(view) => setActiveView(view)}
      />

      {/* ── Main Dashboard Body ── */}
      <main className="dashboard__body">

        {/* ── LEFT COLUMN: Main Dynamic CCTV Feed + 2 Camera Tiles ── */}
        <div className="dashboard__left-col">
          {/* Main Large CCTV Feed */}
          <section className="dashboard__main-cctv-wrap">
            <MainCCTVFeed
              camera={activeCamera}
              latestEvent={cameraStatus[activeCamId]}
              isAutoSwitch={!isManualOverride}
              onToggleAutoSwitch={() => setIsManualOverride((prev) => !prev)}
            />
          </section>

          {/* Exactly 2 Camera Tiles Below */}
          <section className="dashboard__tiles-wrap">
            <div className="dashboard__tiles-grid">
              {CAMERAS.map((cam) => (
                <CameraTile
                  key={cam.camera_id}
                  camera={cam}
                  latestEvent={cameraStatus[cam.camera_id]}
                  isActive={cam.camera_id === activeCamId}
                  onClick={() => {
                    setManualCamId(cam.camera_id);
                    setIsManualOverride(true);
                  }}
                />
              ))}
            </div>
          </section>
        </div>

        {/* ── RIGHT COLUMN: Active Alerts + Repositioned Tactical Zone Map ── */}
        <div className="dashboard__right-col">
          {/* Top: Active Alerts Panel */}
          <section className="dashboard__alerts-wrap">
            <AlertsFeed
              events={events}
              onViewAll={() => setActiveView('alerts')}
              onSelectAlert={handleSelectIndividualAlert}
            />
          </section>

          {/* Bottom: Repositioned Tactical Zone Map (Exactly the same) */}
          <section className="dashboard__map-wrap">
            <TacticalMap cameraStatus={cameraStatus} />
          </section>
        </div>
      </main>



      {/* Individual Alert Details Modal */}
      {selectedAlert && (
        <AlertDetailsModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onAcknowledge={(id) => {
            setSelectedAlert((prev) => prev ? { ...prev, status: 'ACKNOWLEDGED' } : null);
          }}
          onResolve={(id) => {
            setSelectedAlert((prev) => prev ? { ...prev, status: 'RESOLVED' } : null);
          }}
        />
      )}

      {/* Individual Global Track Details Modal */}
      {selectedTrack && (
        <GlobalTrackDetailsModal
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
        />
      )}
    </div>
  );
}
