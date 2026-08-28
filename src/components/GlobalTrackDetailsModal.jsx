import { User, Car, X } from 'lucide-react';
import TacticalSnapshot from './TacticalSnapshot';
import './GlobalTrackDetailsModal.css';

export default function GlobalTrackDetailsModal({ track, onClose }) {
  if (!track) return null;

  const severityColor = track.severity === 'HIGH' ? '#e14b3c' : track.severity === 'MEDIUM' ? '#e8a13d' : '#34d9b4';

  return (
    <div className="track-modal-backdrop" onClick={onClose}>
      <div className="track-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        {/* Header */}
        <div className="track-modal__header">
          <div className="track-modal__header-left">
            <div className="track-modal__avatar-wrap" style={{ borderColor: severityColor }}>
              <User size={16} />
            </div>
            <div>
              <h2 className="track-modal__title">
                Global Target Track: {track.id}
                <span
                  className="badge-severity"
                  style={{
                    color: severityColor,
                    borderColor: severityColor,
                    background: `${severityColor}18`
                  }}
                >
                  {track.severity} SEVERITY
                </span>
              </h2>
              <div className="track-modal__sub">
                First Seen: {track.first_seen_time} • Last Active: {track.last_time} ({track.last_camera})
              </div>
            </div>
          </div>

          <div className="track-modal__badges">
            <span className={`badge-status badge-status--${track.status.toLowerCase()}`}>
              {track.status}
            </span>
            <button className="track-modal__close-btn" onClick={onClose} aria-label="Close modal">
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="track-modal__body">
          {/* Left Column: Map Path & Camera Journey */}
          <div className="track-modal__section">
            {/* Tactical Vector Route Map */}
            <div className="track-modal__section-title">
              <span>TACTICAL TRAJECTORY ROUTE MAP</span>
              <span style={{ color: 'var(--signal-teal)' }}>{track.map_path.length} WAYPOINTS</span>
            </div>

            <div className="track-modal__map-frame">
              <svg className="track-modal__map-svg" viewBox="0 0 440 240" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="440" height="240" fill="#0b1115" />
                {/* Tactical grid background */}
                <path d="M 0 60 L 440 60 M 0 120 L 440 120 M 0 180 L 440 180" stroke="#16232b" strokeWidth="1" />
                <path d="M 110 0 L 110 240 M 220 0 L 220 240 M 330 0 L 330 240" stroke="#16232b" strokeWidth="1" />

                {/* Restricted Zone Polygon */}
                <polygon points="40,30 220,50 260,190 30,170" fill="rgba(225, 75, 60, 0.06)" stroke="rgba(225, 75, 60, 0.3)" strokeDasharray="3 3" />

                {/* Path connections */}
                <path
                  d="M 60 150 L 140 100 L 220 130 L 320 80 L 380 90"
                  fill="none"
                  stroke={severityColor}
                  strokeWidth="2.5"
                  strokeDasharray="6 3"
                />

                {/* Waypoint nodes */}
                <circle cx="60" cy="150" r="6" fill="#10161a" stroke={severityColor} strokeWidth="2" />
                <text x="60" y="170" fill="var(--text-hi)" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="middle">BOP-01 (20:31)</text>

                <circle cx="140" cy="100" r="6" fill="#10161a" stroke={severityColor} strokeWidth="2" />
                <text x="140" y="85" fill="var(--signal-red)" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="middle">Intrusion (20:32)</text>

                <circle cx="220" cy="130" r="6" fill="#10161a" stroke={severityColor} strokeWidth="2" />
                <text x="220" y="150" fill="var(--signal-blue)" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="middle">Vehicle MH04 (20:34)</text>

                <circle cx="320" cy="80" r="6" fill="#10161a" stroke={severityColor} strokeWidth="2" />
                <text x="320" y="65" fill="var(--signal-teal)" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="middle">CHECK-01 (20:35)</text>

                <circle cx="380" cy="90" r="8" fill={severityColor} />
                <circle cx="380" cy="90" r="14" fill="none" stroke={severityColor} strokeWidth="1.5" strokeDasharray="3 2" />
                <text x="380" y="112" fill="var(--text-hi)" fontSize="9" fontWeight="bold" fontFamily="IBM Plex Mono" textAnchor="middle">CURRENT (20:36)</text>
              </svg>
            </div>

            {/* Camera Journey Corridor */}
            <div className="track-modal__section-title">CAMERA CORRIDOR JOURNEY</div>
            <div className="track-modal__journey-list">
              {track.camera_journey.map((step, idx) => (
                <div key={idx} className="track-modal__journey-step">
                  <span className="track-modal__journey-dot" />
                  <div className="track-modal__journey-card">
                    <TacticalSnapshot
                      type={step.action.toLowerCase().includes('vehicle') ? 'vehicle' : 'person'}
                      cameraId={step.camera_id}
                      timestamp={step.time}
                      targetId={track.id}
                      accentColor={severityColor}
                      width="70px"
                      height="46px"
                      aspectRatio="16/10"
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="track-modal__journey-cam">{step.camera_id} • {step.name}</div>
                      <div className="track-modal__journey-action">{step.action}</div>
                    </div>
                    <div className="track-modal__journey-time">[{step.time}]</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column: Vehicle Specs, Intelligence, & Alerts */}
          <div className="track-modal__section">
            {/* Target Profile Specs */}
            <div className="track-modal__section-title">TARGET INTELLIGENCE</div>
            <div className="alert-modal__spec-grid">
              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Re-ID Confidence</div>
                <div className="alert-modal__spec-val alert-modal__spec-val--accent">
                  {track.confidence}
                </div>
              </div>

              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Gender / Age</div>
                <div className="alert-modal__spec-val">
                  {track.gender}, {track.age}
                </div>
              </div>

              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Visual Profile</div>
                <div className="alert-modal__spec-val" style={{ fontSize: '11px' }}>
                  {track.clothing}
                </div>
              </div>

              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Watchlist Hit</div>
                <div className="alert-modal__spec-val" style={{ color: 'var(--signal-amber)', fontSize: '11px' }}>
                  {track.watchlist_status}
                </div>
              </div>
            </div>

            {/* Vehicle Association Box */}
            <div className="track-modal__section-title">VEHICLE ASSOCIATION</div>
            {track.vehicle ? (
              <div className="track-modal__vehicle-box">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span className="track-modal__vehicle-icon">
                    <Car size={14} />
                  </span>
                  <div>
                    <div className="track-modal__vehicle-plate">{track.vehicle.plate}</div>
                    <div className="track-modal__vehicle-type">{track.vehicle.type}</div>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--signal-teal)' }}>
                    {track.vehicle.confidence} Match
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)' }}>
                    {track.vehicle.associated_time}
                  </div>
                </div>
              </div>
            ) : (
              <div className="alert-modal__spec-card" style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '16px' }}>
                No vehicle associated with target track.
              </div>
            )}

            {/* Associated Alerts */}
            <div className="track-modal__section-title">ASSOCIATED SECURITY ALERTS ({track.alerts.length})</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {track.alerts.map((alt) => (
                <div
                  key={alt.id}
                  className="track-modal__alert-item"
                  style={{ '--alert-accent': alt.severity === 'HIGH' ? '#e14b3c' : '#e8a13d' }}
                >
                  <div>
                    <span className="track-modal__alert-title">{alt.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-dim)', marginLeft: '8px' }}>
                      ({alt.id})
                    </span>
                  </div>
                  <span className="track-modal__alert-time">[{alt.time}]</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="track-modal__footer">
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-mid)' }}>
            Track ID: <strong style={{ color: 'var(--text-hi)' }}>{track.id}</strong> • Logged Events: {track.event_count}
          </div>
          <button className="btn-tactical" onClick={onClose}>
            Close Track Details
          </button>
        </div>
      </div>
    </div>
  );
}
