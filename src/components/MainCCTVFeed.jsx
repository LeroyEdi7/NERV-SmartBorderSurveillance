import { useState, useEffect } from 'react';
import { Zap, Target, Flame, Volume2, Maximize2, Grid } from 'lucide-react';
import './MainCCTVFeed.css';
import { SEVERITY_COLOR } from '../data/scenario';

const CAM_NAMES = {
  'BOP-01':   'Border Outpost Camera 01',
  'CHECK-01': 'Checkpost Camera 01',
};

export default function MainCCTVFeed({
  camera,
  latestEvent,
  isAutoSwitch,
  onToggleAutoSwitch,
  streamUrl
}) {
  const [timestamp, setTimestamp] = useState('');
  const [thermalMode, setThermalMode] = useState(false);
  const [gridVisible, setGridVisible] = useState(true);

  // Live HUD clock update
  useEffect(() => {
    const updateTime = () => {
      const d = new Date();
      const iso = d.toISOString().replace('T', ' ').substring(0, 19);
      const ms = String(d.getMilliseconds()).padStart(3, '0');
      setTimestamp(`${iso}.${ms} UTC`);
    };
    updateTime();
    const interval = setInterval(updateTime, 100);
    return () => clearInterval(interval);
  }, []);

  const cameraID = camera?.camera_id || 'BOP-01';
  const cameraName = CAM_NAMES[cameraID] || camera?.name || cameraID;
  const severity = latestEvent?.severity || null;
  const accentColor = severity ? (SEVERITY_COLOR[severity] || 'var(--signal-teal)') : 'var(--signal-teal)';

  const entityId = latestEvent?.entity?.entity_id || 'G-017';
  const anomalyLabel = latestEvent?.label || (severity ? `${severity} Priority Signal` : 'NORMAL - CLEAR');

  return (
    <div className={`main-cctv ${thermalMode ? 'main-cctv--thermal' : ''}`} style={{ '--accent': accentColor }}>
      {/* ── Header Bar ── */}
      <div className="main-cctv__head">
        <div className="main-cctv__cam-info">
          <span className="main-cctv__cam-id">{cameraID}</span>
          <span className="main-cctv__cam-name">{cameraName}</span>
        </div>

        {/* Anomaly Badge */}
        <div className={`main-cctv__anomaly-badge ${severity ? `main-cctv__anomaly-badge--${severity.toLowerCase()}` : 'main-cctv__anomaly-badge--normal'}`}>
          <span className="main-cctv__anomaly-dot" />
          <span className="main-cctv__anomaly-text">{anomalyLabel}</span>
          {severity && <span className="main-cctv__severity-tag">{severity}</span>}
        </div>

        {/* Status + Auto-Switch Controls */}
        <div className="main-cctv__controls-head">
          <span className="main-cctv__live-badge">
            <span className="main-cctv__live-dot" />
            LIVE
          </span>
          <button
            className={`main-cctv__auto-btn ${isAutoSwitch ? 'main-cctv__auto-btn--active' : ''}`}
            onClick={onToggleAutoSwitch}
            title={isAutoSwitch ? 'Auto-switching enabled (Speaker View)' : 'Click to resume Auto-Switch'}
          >
            {isAutoSwitch ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Zap size={11} /> AUTO FOCUS
              </span>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Target size={11} /> MANUAL OVERRIDE
              </span>
            )}
          </button>
        </div>
      </div>

      {/* ── Video Viewport Area ── */}
      <div className="main-cctv__viewport">
        {streamUrl ? (
          <img src={streamUrl} alt={`Live feed from ${cameraID}`} className="main-cctv__video-stream" />
        ) : (
          <div className="main-cctv__video-sim">
            {/* Tactical Grid Background Overlay */}
            {gridVisible && (
              <svg className="main-cctv__grid-svg" viewBox="0 0 800 450" preserveAspectRatio="none">
                <defs>
                  <pattern id="hud-grid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(52, 217, 180, 0.07)" strokeWidth="1" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#hud-grid)" />
              </svg>
            )}

            {/* Target Reticle Crosshair in Center */}
            <div className="main-cctv__center-reticle">
              <div className="main-cctv__reticle-h" />
              <div className="main-cctv__reticle-v" />
              <div className="main-cctv__reticle-circle" />
            </div>

            {/* AI Bounding Box 1: Primary Target G-017 */}
            <div
              className={`main-cctv__bbox main-cctv__bbox--target ${severity === 'HIGH' ? 'main-cctv__bbox--alert' : ''}`}
              style={{
                top: cameraID === 'BOP-01' ? '20%' : '30%',
                left: cameraID === 'BOP-01' ? '18%' : '52%',
                width: '26%',
                height: '58%',
              }}
            >
              {/* Corner Bracket Accents */}
              <span className="main-cctv__corner main-cctv__corner--tl" />
              <span className="main-cctv__corner main-cctv__corner--tr" />
              <span className="main-cctv__corner main-cctv__corner--bl" />
              <span className="main-cctv__corner main-cctv__corner--br" />

              {/* Target Label */}
              <div className="main-cctv__bbox-tag">
                <span className="main-cctv__bbox-id">{entityId}</span>
                <span className="main-cctv__bbox-type">PERSON</span>
                <span className="main-cctv__bbox-score">98.1%</span>
              </div>
            </div>

            {/* AI Bounding Box 2: Associated Vehicle V-003 */}
            <div
              className="main-cctv__bbox main-cctv__bbox--vehicle"
              style={{
                top: cameraID === 'BOP-01' ? '32%' : '22%',
                left: cameraID === 'BOP-01' ? '48%' : '15%',
                width: '38%',
                height: '50%',
              }}
            >
              <span className="main-cctv__corner main-cctv__corner--tl" />
              <span className="main-cctv__corner main-cctv__corner--tr" />
              <span className="main-cctv__corner main-cctv__corner--bl" />
              <span className="main-cctv__corner main-cctv__corner--br" />

              <div className="main-cctv__bbox-tag main-cctv__bbox-tag--vehicle">
                <span className="main-cctv__bbox-id">V-003</span>
                <span className="main-cctv__bbox-type">MH04AB1234</span>
                <span className="main-cctv__bbox-score">94.5%</span>
              </div>
            </div>

            {/* Target Vector Line Connecting Person and Vehicle */}
            <svg className="main-cctv__vector-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
              <line
                x1={cameraID === 'BOP-01' ? '31' : '65'}
                y1={cameraID === 'BOP-01' ? '49' : '59'}
                x2={cameraID === 'BOP-01' ? '67' : '34'}
                y2={cameraID === 'BOP-01' ? '57' : '47'}
                stroke="rgba(52, 217, 180, 0.4)"
                strokeWidth="0.8"
                strokeDasharray="2 2"
              />
            </svg>

            {/* HUD Overlay - Top Left: Global ID Pill */}
            <div className="main-cctv__hud-top-left">
              <span className="main-cctv__hud-gid-label">GLOBAL ID:</span>
              <span className="main-cctv__hud-gid-val">{entityId}</span>
            </div>

            {/* HUD Overlay - Top Right: Telemetry & Rec Dot */}
            <div className="main-cctv__hud-top-right">
              <span className="main-cctv__rec-dot" />
              <span className="main-cctv__rec-text">REC 1080p</span>
            </div>

            {/* HUD Overlay - Bottom Left: Realtime Clock & Coordinates */}
            <div className="main-cctv__hud-bottom-left">
              <div className="main-cctv__hud-time">{timestamp}</div>
              <div className="main-cctv__hud-coords">
                {cameraID === 'BOP-01' ? 'LAT: 28.6139° N • LNG: 77.2090° E' : 'LAT: 28.6205° N • LNG: 77.2165° E'}
              </div>
            </div>
          </div>
        )}

        {/* Tactical Scanline Effect */}
        <div className="main-cctv__scanline" />
      </div>

      {/* ── Footer / Controls Bar ── */}
      <div className="main-cctv__foot">
        <div className="main-cctv__telemetry">
          <span>RES: <strong style={{ color: 'var(--text-hi)' }}>1920x1080</strong></span>
          <span className="main-cctv__sep">•</span>
          <span>FPS: <strong style={{ color: 'var(--signal-teal)' }}>30</strong></span>
          <span className="main-cctv__sep">•</span>
          <span>AI ENGINE: <strong style={{ color: 'var(--signal-teal)' }}>YOLOv8-SURV (ACTIVE)</strong></span>
          <span className="main-cctv__sep">•</span>
          <span>BANDWIDTH: <strong style={{ color: 'var(--text-mid)' }}>4.8 Mbps</strong></span>
        </div>

        <div className="main-cctv__quick-controls">
          <button
            className={`main-cctv__icon-btn ${gridVisible ? 'main-cctv__icon-btn--active' : ''}`}
            onClick={() => setGridVisible(!gridVisible)}
            title="Toggle Tactical Grid"
          >
            <Grid size={11} style={{ display: 'inline', marginRight: '4px' }} /> Grid
          </button>
          <button
            className={`main-cctv__icon-btn ${thermalMode ? 'main-cctv__icon-btn--active' : ''}`}
            onClick={() => setThermalMode(!thermalMode)}
            title="Toggle Thermal Filter"
          >
            <Flame size={11} style={{ display: 'inline', marginRight: '4px' }} /> Thermal
          </button>
          <span className="main-cctv__icon-btn" title="Audio Stream">
            <Volume2 size={12} />
          </span>
          <span className="main-cctv__icon-btn" title="Fullscreen View">
            <Maximize2 size={12} />
          </span>
        </div>
      </div>
    </div>
  );
}
