import { useState } from 'react';
import StatusBar   from './components/StatusBar';
import CameraPanel  from './components/CameraPanel';
import TacticalMap  from './components/TacticalMap';
import AlertsFeed   from './components/AlertsFeed';
import GlobalTrack  from './components/GlobalTrack';
import EventTimeline from './components/EventTimeline';
import StatsBar     from './components/StatsBar';
import ActiveAlertsPage from './components/ActiveAlertsPage';
import AlertDetailsModal from './components/AlertDetailsModal';
import { CAMERAS }  from './data/scenario';
import { useEventStream } from './hooks/useEventStream';
import './App.css';

import GlobalTracksPage from './components/GlobalTracksPage';
import GlobalTrackDetailsModal from './components/GlobalTrackDetailsModal';

export default function App() {
  const { events, cameraStatus } = useEventStream();
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard' | 'alerts' | 'tracks'
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState(null);

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
      {/* ── Top status bar ── */}
      <StatusBar
        cameraCount={CAMERAS.length}
        activeView={activeView}
        onNavigate={(view) => setActiveView(view)}
      />

      {/* ── Main content area ── */}
      <main className="dashboard__body">

        {/* ── ROW 1: Live cameras (left) + Active alerts (right) ── */}
        <div className="dashboard__row1">

          {/* Cameras section */}
          <section className="dashboard__cameras-wrap">
            <div className="dashboard__section-label">LIVE CAMERAS</div>
            <div className="dashboard__cameras-grid">
              {CAMERAS.map((cam) => (
                <CameraPanel
                  key={cam.camera_id}
                  camera={cam}
                  latestEvent={cameraStatus[cam.camera_id]}
                />
              ))}
            </div>
          </section>

          {/* Active alerts feed */}
          <section className="dashboard__alerts-wrap">
            <AlertsFeed
              events={events}
              onViewAll={() => setActiveView('alerts')}
              onSelectAlert={handleSelectIndividualAlert}
            />
          </section>
        </div>

        {/* ── ROW 2: Tactical map + Global track + Event timeline ── */}
        <div className="dashboard__row2">

          <section className="dashboard__map-wrap">
            <TacticalMap cameraStatus={cameraStatus} />
          </section>

          <section className="dashboard__gtrack-wrap">
            <GlobalTrack
              events={events}
              onViewTracks={() => setActiveView('tracks')}
              onSelectTrack={(track) => setSelectedTrack(track)}
            />
          </section>

          <section className="dashboard__etl-wrap">
            <EventTimeline events={events} />
          </section>
        </div>
      </main>

      {/* ── Bottom statistics bar ── */}
      <StatsBar />

      {/* Individual Alert Details Modal on Dashboard */}
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

      {/* Individual Global Track Details Modal on Dashboard */}
      {selectedTrack && (
        <GlobalTrackDetailsModal
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
        />
      )}
    </div>
  );
}
