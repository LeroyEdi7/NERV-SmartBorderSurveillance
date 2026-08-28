import './CameraTile.css';
import { SEVERITY_COLOR } from '../data/scenario';

const CAM_NAMES = {
  'BOP-01':   'BOP-01 (Border Out Post)',
  'CHECK-01': 'CHECK-01 (Check Post)',
};

export default function CameraTile({ camera, latestEvent, isActive, onClick, streamUrl }) {
  const cameraID = camera?.camera_id || 'BOP-01';
  const displayName = CAM_NAMES[cameraID] || cameraID;
  const severity = latestEvent?.severity || null;
  const accentColor = severity ? (SEVERITY_COLOR[severity] || 'var(--signal-teal)') : 'var(--signal-teal)';

  return (
    <div
      className={`camera-tile ${isActive ? 'camera-tile--active' : ''} ${severity ? `camera-tile--${severity.toLowerCase()}` : ''}`}
      onClick={onClick}
      style={{ '--accent': accentColor }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.(); }}
    >
      {/* ── Tile Header ── */}
      <div className="camera-tile__head">
        <div className="camera-tile__title-wrap">
          <span className="camera-tile__id">{cameraID}</span>
          <span className="camera-tile__name">{displayName}</span>
        </div>

        <div className="camera-tile__badges">
          {isActive && <span className="camera-tile__active-badge">MAIN FEED</span>}
          <span className="camera-tile__live-badge">
            <span className="camera-tile__live-dot" />
            LIVE
          </span>
        </div>
      </div>

      {/* ── Feed Preview ── */}
      <div className="camera-tile__feed">
        {streamUrl ? (
          <img src={streamUrl} alt={`Thumbnail feed for ${cameraID}`} className="camera-tile__thumb-img" />
        ) : (
          <div className="camera-tile__placeholder">
            {/* Simulated Bounding Box Preview */}
            <div
              className="camera-tile__mini-bbox"
              style={{
                top: cameraID === 'BOP-01' ? '25%' : '35%',
                left: cameraID === 'BOP-01' ? '20%' : '55%',
                width: '28%',
                height: '50%',
              }}
            >
              <span className="camera-tile__mini-label">{latestEvent?.entity?.entity_id || 'G-017'}</span>
            </div>

            {/* Tactical Grid Pattern */}
            <div className="camera-tile__grid-pattern" />

            {/* Switch Prompt Overlay on Hover */}
            <div className="camera-tile__hover-overlay">
              <span>{isActive ? 'CURRENT MAIN FEED' : 'CLICK TO VIEW ON MAIN'}</span>
            </div>
          </div>
        )}
        <div className="camera-tile__scanline" />
      </div>

      {/* ── Tile Footer ── */}
      <div className="camera-tile__foot">
        <span className="camera-tile__status-text">
          {latestEvent ? (
            <span className="camera-tile__event-label" style={{ color: accentColor, display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span className="camera-tile__live-dot" style={{ background: accentColor, width: '6px', height: '6px' }} />
              {latestEvent.label}
            </span>
          ) : (
            <span className="camera-tile__clear-label" style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
              <span className="camera-tile__live-dot" style={{ background: 'var(--signal-teal)', width: '6px', height: '6px' }} />
              NORMAL - CLEAR
            </span>
          )}
        </span>
        <span className="camera-tile__cam-fps">1080p • 30 FPS</span>
      </div>
    </div>
  );
}
