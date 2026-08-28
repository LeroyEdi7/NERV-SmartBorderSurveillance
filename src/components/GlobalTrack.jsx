import { Camera, Clock } from 'lucide-react';
import './GlobalTrack.css';
import { INITIAL_TRACKS } from '../data/mockTracks';
import TacticalSnapshot from './TacticalSnapshot';

export default function GlobalTrack({ onViewTracks, onSelectTrack }) {
  return (
    <div className="gtrack">
      {/* Header */}
      <div className="gtrack__head">
        <span className="gtrack__head-label">GLOBAL TRACKS</span>
        <button
          className="gtrack__view-all-btn"
          onClick={() => onViewTracks?.()}
        >
          View All →
        </button>
      </div>

      {/* Compact List of Multiple Tracks */}
      <div className="gtrack__list">
        {INITIAL_TRACKS.map((tr) => {
          const severityColor = tr.severity === 'HIGH' ? '#e14b3c' : tr.severity === 'MEDIUM' ? '#e8a13d' : '#34d9b4';
          const detectionLabel = tr.watchlist_status || tr.alerts?.[0]?.label || 'Subject Detected';

          return (
            <div
              key={tr.id}
              className="gtrack__item"
              style={{ '--track-accent': severityColor }}
              onClick={() => onSelectTrack?.(tr)}
            >
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <TacticalSnapshot
                  type={tr.vehicle ? 'vehicle' : 'person'}
                  cameraId={tr.last_camera}
                  timestamp={tr.last_time}
                  targetId={tr.id}
                  accentColor={severityColor}
                  width="56px"
                  height="36px"
                  aspectRatio="16/10"
                />

                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  {/* Top row: ID + Status + Confidence */}
                  <div className="gtrack__item-top">
                    <div className="gtrack__item-id-group">
                      <span className="gtrack__item-id">{tr.id}</span>
                      <span className={`badge-status badge-status--${tr.status.toLowerCase()}`}>
                        {tr.status}
                      </span>
                    </div>
                    <span className="gtrack__item-conf">{tr.confidence}</span>
                  </div>

                  {/* Middle: Detection info */}
                  <div className="gtrack__item-detection">
                    <span className="gtrack__item-det-label">{detectionLabel}</span>
                  </div>

                  {/* Bottom: Camera & Time */}
                  <div className="gtrack__item-meta">
                    <span className="gtrack__item-cam">
                      <Camera size={10} style={{ display: 'inline', marginRight: '3px' }} />
                      {tr.last_camera}
                    </span>
                    <span className="gtrack__item-sep">•</span>
                    <span className="gtrack__item-time">
                      <Clock size={10} style={{ display: 'inline', marginRight: '3px' }} />
                      {tr.last_time}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
