import { useState } from 'react';
import { Search, Camera, X } from 'lucide-react';
import './TacticalSnapshot.css';

export default function TacticalSnapshot({
  type = 'person',
  cameraId = 'BOP-01',
  timestamp = '20:36',
  targetId = 'G-017',
  accentColor = '#e14b3c',
  aspectRatio = '16/10',
  width = '100%',
  height = 'auto',
  style = {}
}) {
  const [showLightbox, setShowLightbox] = useState(false);

  const renderGraphicContent = () => {
    if (type === 'vehicle') {
      return (
        <g>
          {/* Vehicle Silhouette & Bounding Box */}
          <rect x="80" y="70" width="240" height="110" fill="none" stroke={accentColor} strokeWidth="2" strokeDasharray="6 3" />
          <path d="M 100 140 L 140 100 L 260 100 L 300 140 Z" fill="#1b2a33" stroke={accentColor} strokeWidth="1.5" />
          <rect x="90" y="130" width="220" height="40" rx="4" fill="#152026" stroke={accentColor} strokeWidth="1.5" />
          <circle cx="130" cy="170" r="14" fill="#0c1215" stroke={accentColor} strokeWidth="2" />
          <circle cx="270" cy="170" r="14" fill="#0c1215" stroke={accentColor} strokeWidth="2" />

          {/* License plate graphic */}
          <rect x="175" y="148" width="50" height="14" fill="#10181d" stroke="var(--signal-blue)" strokeWidth="1" />
          <text x="200" y="159" fill="var(--signal-blue)" fontSize="8" fontWeight="bold" fontFamily="IBM Plex Mono" textAnchor="middle">
            VEHICLE
          </text>
        </g>
      );
    }

    if (type === 'cargo') {
      return (
        <g>
          {/* Cargo Container/Truck Bounding Box */}
          <rect x="70" y="50" width="260" height="140" fill="none" stroke={accentColor} strokeWidth="2" strokeDasharray="6 3" />
          <rect x="80" y="60" width="200" height="110" fill="#1b272f" stroke={accentColor} strokeWidth="1.5" />
          <rect x="280" y="90" width="40" height="80" fill="#152026" stroke={accentColor} strokeWidth="1.5" />
          <circle cx="120" cy="175" r="14" fill="#0c1215" stroke={accentColor} strokeWidth="2" />
          <circle cx="240" cy="175" r="14" fill="#0c1215" stroke={accentColor} strokeWidth="2" />
        </g>
      );
    }

    // Default: Person / Intrusion / Watchlist Subject Silhouette
    return (
      <g>
        {/* Subject Silhouette */}
        <circle cx="200" cy="95" r="22" fill="#1a2831" stroke={accentColor} strokeWidth="2" />
        <path d="M 155 190 C 155 135, 245 135, 245 190 Z" fill="#1a2831" stroke={accentColor} strokeWidth="2" />

        {/* Target Bounding Box */}
        <rect x="145" y="60" width="110" height="135" fill="none" stroke={accentColor} strokeWidth="2" strokeDasharray="6 3" />

        {/* Corner Crosshair Markers */}
        <path d="M 145 75 L 145 60 L 160 60" stroke={accentColor} strokeWidth="2.5" />
        <path d="M 240 60 L 255 60 L 255 75" stroke={accentColor} strokeWidth="2.5" />
        <path d="M 145 180 L 145 195 L 160 195" stroke={accentColor} strokeWidth="2.5" />
        <path d="M 240 195 L 255 195 L 255 180" stroke={accentColor} strokeWidth="2.5" />

        {/* Target Badge */}
        <rect x="145" y="42" width="110" height="18" fill={accentColor} />
        <text x="200" y="55" fill="#ffffff" fontSize="10" fontWeight="bold" fontFamily="IBM Plex Mono" textAnchor="middle">
          {targetId}
        </text>
      </g>
    );
  };

  const renderSvgCanvas = (isExpanded = false) => (
    <svg className="tactical-snapshot__svg" viewBox="0 0 400 230" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Background Frame Grid */}
      <rect width="400" height="230" fill="#090e11" />
      <path d="M 0 57 L 400 57 M 0 115 L 400 115 M 0 172 L 400 172" stroke="#141e24" strokeWidth="1" />
      <path d="M 100 0 L 100 230 M 200 0 L 200 230 M 300 0 L 300 230" stroke="#141e24" strokeWidth="1" />

      {/* Camera HUD Overlays */}
      <rect x="10" y="10" width="8" height="8" fill="#e14b3c" />
      <text x="24" y="18" fill="#e14b3c" fontSize="10" fontWeight="bold" fontFamily="IBM Plex Mono">REC</text>
      <text x="390" y="18" fill="var(--signal-teal)" fontSize="10" fontFamily="IBM Plex Mono" textAnchor="end">{cameraId}</text>
      <text x="390" y="220" fill="var(--text-mid)" fontSize="9" fontFamily="IBM Plex Mono" textAnchor="end">{timestamp}</text>

      {/* Detection Graphic */}
      {renderGraphicContent()}

      {/* Frame Center Crosshair */}
      <circle cx="200" cy="115" r="3" fill="none" stroke="rgba(52, 217, 180, 0.3)" />
      <path d="M 190 115 L 210 115 M 200 105 L 200 125" stroke="rgba(52, 217, 180, 0.3)" strokeWidth="1" />
    </svg>
  );

  return (
    <>
      <div
        className="tactical-snapshot"
        style={{ width, height, aspectRatio, ...style }}
        onClick={(e) => {
          e.stopPropagation();
          setShowLightbox(true);
        }}
        title="Click to expand camera snapshot"
      >
        {renderSvgCanvas()}
        <span className="tactical-snapshot__zoom-hint">
          <Search size={9} style={{ display: 'inline', marginRight: '3px' }} /> Zoom
        </span>
        <span className="tactical-snapshot__tag">{cameraId}</span>
      </div>

      {/* Expanded Lightbox Modal */}
      {showLightbox && (
        <div className="snapshot-lightbox-backdrop" onClick={() => setShowLightbox(false)}>
          <div className="snapshot-lightbox" onClick={(e) => e.stopPropagation()}>
            <div className="snapshot-lightbox__head">
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Camera size={13} /> CAMERA FRAME SNAPSHOT CAPTURE • <span style={{ color: 'var(--signal-teal)' }}>{cameraId}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: 'var(--text-dim)' }}>[{timestamp}]</span>
                <button
                  className="snapshot-lightbox__close"
                  onClick={() => setShowLightbox(false)}
                  aria-label="Close image preview"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
            <div className="snapshot-lightbox__body">
              {renderSvgCanvas(true)}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
