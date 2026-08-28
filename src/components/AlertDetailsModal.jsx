import { useState } from 'react';
import { AlertTriangle, UserX, Car, Link, Footprints, Check, ShieldCheck, X } from 'lucide-react';
import './AlertDetailsModal.css';
import { SEVERITY_COLORS, EVENT_META } from '../data/mockAlerts';

function RenderModalTypeIcon({ eventType }) {
  switch (eventType) {
    case 'intrusion': return <AlertTriangle size={16} />;
    case 'watchlist_match': return <UserX size={16} />;
    case 'vehicle_person_association': return <Car size={16} />;
    case 'cross_camera_match': return <Link size={16} />;
    case 'person_reidentified': return <Footprints size={16} />;
    default: return <AlertTriangle size={16} />;
  }
}

export default function AlertDetailsModal({ alert, onClose, onAcknowledge, onResolve }) {
  const [noteText, setNoteText] = useState('');
  const [localNotes, setLocalNotes] = useState([]);

  if (!alert) return null;

  const meta = EVENT_META[alert.event_type] ?? { bg: '#52666d', color: '#8fa3aa' };
  const severityColor = SEVERITY_COLORS[alert.severity] ?? '#8fa3aa';

  const handleAddNote = (e) => {
    e.preventDefault();
    if (!noteText.trim()) return;
    const newNote = {
      time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      note: `Operator Note: ${noteText.trim()}`
    };
    setLocalNotes([...localNotes, newNote]);
    setNoteText('');
  };

  const combinedAuditTrail = [...(alert.audit_trail || []), ...localNotes];

  return (
    <div className="alert-modal-backdrop" onClick={onClose}>
      <div className="alert-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        {/* Header */}
        <div className="alert-modal__header">
          <div className="alert-modal__header-left">
            <div className="alert-modal__type-icon" style={{ background: meta.bg }}>
              <RenderModalTypeIcon eventType={alert.event_type} />
            </div>
            <div>
              <h2 className="alert-modal__title">{alert.type_label || alert.label}</h2>
              <div className="alert-modal__id">ALERT ID: {alert.id} • {alert.timestamp}</div>
            </div>
            <div className="alert-modal__badges">
              <span
                className="badge-severity"
                style={{
                  color: severityColor,
                  borderColor: severityColor,
                  background: `${severityColor}18`
                }}
              >
                {alert.severity} SEVERITY
              </span>
              <span className={`badge-status badge-status--${(alert.status || 'NEW').toLowerCase()}`}>
                {alert.status}
              </span>
            </div>
          </div>

          <button
            className="alert-modal__close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div className="alert-modal__body">
          {/* Left: Evidence Video/Snapshot Frame */}
          <div className="alert-modal__evidence-section">
            <div className="alert-modal__section-title">
              <span>EVIDENCE FRAME CAPTURE</span>
              <span style={{ color: 'var(--signal-teal)' }}>CAM: {alert.camera_id}</span>
            </div>

            <div className="alert-modal__frame">
              <div className="alert-modal__cam-overlay">
                <span className="status-bar__dot status-bar__dot--live" />
                REC • {alert.camera_name || alert.camera_id}
              </div>

              <div className="alert-modal__confidence-overlay">
                AI CONFIDENCE: {alert.confidence || '96.2%'}
              </div>

              {/* Tactical Surveillance Bounding Box Graphic */}
              <svg className="alert-modal__frame-svg" viewBox="0 0 400 250" fill="none" xmlns="http://www.w3.org/2000/svg">
                {/* Background grid */}
                <rect width="400" height="250" fill="#0c1216" />
                <path d="M 0 50 L 400 50 M 0 100 L 400 100 M 0 150 L 400 150 M 0 200 L 400 200" stroke="#16222a" strokeWidth="1" />
                <path d="M 100 0 L 100 250 M 200 0 L 200 250 M 300 0 L 300 250" stroke="#16222a" strokeWidth="1" />

                {/* Tactical zone polygon overlay */}
                <polygon points="120,40 340,60 360,200 100,180" fill="rgba(225, 75, 60, 0.08)" stroke="rgba(225, 75, 60, 0.3)" strokeDasharray="4 3" strokeWidth="1.5" />

                {/* Subject Silhouette */}
                <circle cx="210" cy="100" r="18" fill="#1d2c36" stroke={severityColor} strokeWidth="2" />
                <path d="M 175 185 C 175 140, 245 140, 245 185 Z" fill="#1d2c36" stroke={severityColor} strokeWidth="2" />

                {/* Target Bounding Box */}
                <rect x="165" y="70" width="90" height="125" fill="none" stroke={severityColor} strokeWidth="2" strokeDasharray="8 4" />

                {/* Target Corner Crosshairs */}
                <path d="M 165 85 L 165 70 L 180 70" stroke={severityColor} strokeWidth="3" />
                <path d="M 240 70 L 255 70 L 255 85" stroke={severityColor} strokeWidth="3" />
                <path d="M 165 180 L 165 195 L 180 195" stroke={severityColor} strokeWidth="3" />
                <path d="M 240 195 L 255 195 L 255 180" stroke={severityColor} strokeWidth="3" />

                {/* Target ID overlay label */}
                <rect x="165" y="48" width="90" height="18" fill={severityColor} />
                <text x="210" y="61" fill="#ffffff" fontSize="10" fontWeight="bold" fontFamily="IBM Plex Mono" textAnchor="middle">
                  {alert.global_id || 'G-017'}
                </text>

                {/* Target coordinates graphic */}
                <text x="170" y="210" fill="var(--text-mid)" fontSize="9" fontFamily="IBM Plex Mono">
                  LAT: {alert.coordinates?.lat || '28.6148'}
                </text>
                <text x="170" y="222" fill="var(--text-mid)" fontSize="9" fontFamily="IBM Plex Mono">
                  LNG: {alert.coordinates?.lng || '77.2078'}
                </text>
              </svg>
            </div>

            <div className="alert-modal__desc-box">
              <strong>Tactical Summary:</strong> {alert.description}
            </div>
          </div>

          {/* Right: Intelligence Specs & Audit Trail */}
          <div className="alert-modal__info-section">
            <div className="alert-modal__section-title">INTELLIGENCE METRICS</div>
            
            <div className="alert-modal__spec-grid">
              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Global Target ID</div>
                <div className="alert-modal__spec-val alert-modal__spec-val--accent">
                  {alert.global_id || 'N/A'}
                </div>
              </div>

              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Detection Zone</div>
                <div className="alert-modal__spec-val">
                  {alert.zone || 'ZONE-01'}
                </div>
              </div>

              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Location / Sector</div>
                <div className="alert-modal__spec-val">
                  {alert.location || 'North Perimeter'}
                </div>
              </div>

              <div className="alert-modal__spec-card">
                <div className="alert-modal__spec-label">Target Type</div>
                <div className="alert-modal__spec-val">
                  {alert.entity?.type || 'Person / Subject'}
                </div>
              </div>

              {alert.entity?.apparel && (
                <div className="alert-modal__spec-card">
                  <div className="alert-modal__spec-label">Visual Profile</div>
                  <div className="alert-modal__spec-val" style={{ fontSize: '11px' }}>
                    {alert.entity.apparel}
                  </div>
                </div>
              )}

              {alert.entity?.estimated_speed && (
                <div className="alert-modal__spec-card">
                  <div className="alert-modal__spec-label">Est. Velocity</div>
                  <div className="alert-modal__spec-val">
                    {alert.entity.estimated_speed}
                  </div>
                </div>
              )}
            </div>

            {/* Audit Trail Timeline */}
            <div className="alert-modal__section-title">EVENT AUDIT TRAIL</div>
            <div className="alert-modal__audit-list">
              {combinedAuditTrail.map((item, idx) => (
                <div key={idx} className="alert-modal__audit-item">
                  <span className="alert-modal__audit-time">[{item.time}]</span>
                  <span className="alert-modal__audit-text">{item.note}</span>
                </div>
              ))}
            </div>

            {/* Operator Note Form */}
            <form onSubmit={handleAddNote} style={{ marginTop: 'auto' }}>
              <div className="alert-modal__section-title" style={{ marginBottom: '6px' }}>
                ADD OPERATOR NOTE
              </div>
              <textarea
                className="alert-modal__note-input"
                placeholder="Type tactical log note and press Enter to save..."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    handleAddNote(e);
                  }
                }}
              />
            </form>
          </div>
        </div>

        {/* Footer / Actions */}
        <div className="alert-modal__footer">
          <div className="alert-modal__footer-status">
            <span>Status: <strong style={{ color: 'var(--text-hi)' }}>{alert.status}</strong></span>
          </div>

          <div className="alert-modal__actions">
            {alert.status !== 'ACKNOWLEDGED' && alert.status !== 'RESOLVED' && (
              <button
                className="btn-tactical btn-tactical--ack"
                onClick={() => onAcknowledge(alert.id)}
              >
                <Check size={12} style={{ display: 'inline', marginRight: '4px' }} /> Acknowledge Alert
              </button>
            )}

            {alert.status !== 'RESOLVED' && (
              <button
                className="btn-tactical btn-tactical--resolve"
                onClick={() => onResolve(alert.id)}
              >
                <ShieldCheck size={12} style={{ display: 'inline', marginRight: '4px' }} /> Resolve Alert
              </button>
            )}

            <button
              className="btn-tactical"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
