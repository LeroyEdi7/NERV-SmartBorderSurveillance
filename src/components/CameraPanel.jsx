import { Camera, Mic, Volume2, Maximize2 } from 'lucide-react';
import './CameraPanel.css';
import { SEVERITY_COLOR } from '../data/scenario';

const CAM_NAMES = {
  'BOP-01':   'BOP-01 (Border Out Post)',
  'CHECK-01': 'CHECK-01 (Check Post)',
};

export default function CameraPanel({ camera, latestEvent, streamUrl }) {
  const severity = latestEvent?.severity ?? null;
  const accent   = severity ? SEVERITY_COLOR[severity] : 'var(--signal-teal)';

  return (
    <div className="camera-panel" style={{ '--accent': accent }}>
      {/* Header */}
      <div className="camera-panel__head">
        <span className="camera-panel__id">
          {CAM_NAMES[camera.camera_id] ?? camera.camera_id}
        </span>
        <span className="camera-panel__badge">
          <span className="camera-panel__badge-dot" />
          LIVE
          <span className="camera-panel__wifi" aria-label="signal">▲</span>
        </span>
      </div>

      {/* Feed / placeholder */}
      <div className="camera-panel__feed">
        {streamUrl ? (
          <img src={streamUrl} alt={`Live feed from ${camera.camera_id}`} />
        ) : (
          <div className="camera-panel__placeholder">
            {/* Simulated detection overlay */}
            <div className="camera-panel__overlay-box camera-panel__overlay-box--person"
                 style={{ top: '18%', left: '10%', width: '28%', height: '60%' }}>
              <span className="camera-panel__overlay-label" style={{ color: '#34d9b4' }}>
                {latestEvent?.entity?.entity_id ?? 'G-017'}
              </span>
            </div>
            <div className="camera-panel__overlay-box camera-panel__overlay-box--vehicle"
                 style={{ top: '22%', left: '38%', width: '40%', height: '55%' }}>
              <span className="camera-panel__overlay-label" style={{ color: '#a87ce8' }}>V-003</span>
            </div>

            {/* Camera icon */}
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M3 7a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"
                stroke="currentColor" strokeWidth="1.2"/>
              <path d="M16 10.5 21 8v8l-5-2.5" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
            </svg>
            <span>awaiting stream</span>
          </div>
        )}
        <div className="camera-panel__scan" />
      </div>

      {/* Footer */}
      <div className="camera-panel__foot">
        <span>Resolution: 1080p &nbsp;•&nbsp; FPS: 20 &nbsp;•&nbsp; AI: <span style={{color:'var(--signal-teal)'}}>Active</span></span>
        <div className="camera-panel__foot-icons" aria-hidden="true">
          <span><Camera size={12} /></span>
          <span><Mic size={12} /></span>
          <span><Volume2 size={12} /></span>
          <span><Maximize2 size={12} /></span>
        </div>
      </div>
    </div>
  );
}
