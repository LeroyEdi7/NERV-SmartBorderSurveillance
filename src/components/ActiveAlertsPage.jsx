import { useState, useMemo } from 'react';
import { Search, AlertTriangle, Check, ShieldCheck, Footprints, UserX, Car, Link } from 'lucide-react';
import './ActiveAlertsPage.css';
import { INITIAL_ALERTS, SEVERITY_COLORS, EVENT_META } from '../data/mockAlerts';
import AlertDetailsModal from './AlertDetailsModal';

function RenderAlertIcon({ eventType }) {
  switch (eventType) {
    case 'intrusion': return <AlertTriangle size={12} />;
    case 'watchlist_match': return <UserX size={12} />;
    case 'vehicle_person_association': return <Car size={12} />;
    case 'cross_camera_match': return <Link size={12} />;
    case 'person_reidentified': return <Footprints size={12} />;
    default: return <AlertTriangle size={12} />;
  }
}

export default function ActiveAlertsPage({ onBackToDashboard, liveEvents = [] }) {
  // State for alerts (merge live streaming events + comprehensive initial alerts)
  const [alerts, setAlerts] = useState(() => {
    // Map live events from streaming hook if present
    const formattedLive = liveEvents.map((ev, i) => ({
      id: ev.event_id || `LIVE-${i}`,
      event_type: ev.event_type,
      type_label: ev.label || ev.event_type.replace(/_/g, ' '),
      severity: ev.severity || 'HIGH',
      timestamp: `2026-08-27 ${ev.timestamp || '20:35'}`,
      time_relative: 'Just now',
      camera_id: ev.camera_id || 'BOP-01',
      camera_name: ev.camera_id === 'BOP-01' ? 'Border outpost camera 01' : 'Checkpost camera 01',
      global_id: ev.entity?.entity_id || 'G-017',
      description: `${ev.label} detected on sensor feed ${ev.camera_id}`,
      status: 'NEW',
      confidence: '97.5%',
      zone: ev.zone?.zone_name || 'ZONE-01 Perimeter',
      location: ev.camera_id,
      coordinates: { lat: 28.6139, lng: 77.209 },
      entity: {
        type: ev.entity?.entity_type || 'Person',
        id: ev.entity?.entity_id || 'G-017',
        estimated_speed: '1.8 m/s',
        reid_score: '97.5%'
      },
      audit_trail: [
        { time: ev.timestamp || '20:35', note: 'Real-time alert streamed from AI Detection Engine' }
      ]
    }));

    // Deduplicate by ID
    const combined = [...formattedLive, ...INITIAL_ALERTS];
    const seen = new Set();
    return combined.filter(a => {
      if (seen.has(a.id)) return false;
      seen.add(a.id);
      return true;
    });
  });

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [cameraFilter, setCameraFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('NEWEST');

  // Selected Alert for Details Modal
  const [selectedAlert, setSelectedAlert] = useState(null);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(6);
  const [visibleCount, setVisibleCount] = useState(6);

  // Handle Action: Acknowledge Alert
  const handleAcknowledge = (id) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? {
              ...a,
              status: 'ACKNOWLEDGED',
              audit_trail: [
                ...(a.audit_trail || []),
                {
                  time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
                  note: 'Acknowledged by Operator Admin'
                }
              ]
            }
          : a
      )
    );
    if (selectedAlert && selectedAlert.id === id) {
      setSelectedAlert((prev) => prev ? { ...prev, status: 'ACKNOWLEDGED' } : null);
    }
  };

  // Handle Action: Resolve Alert
  const handleResolve = (id) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? {
              ...a,
              status: 'RESOLVED',
              audit_trail: [
                ...(a.audit_trail || []),
                {
                  time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
                  note: 'Resolved and closed by Operator Admin'
                }
              ]
            }
          : a
      )
    );
    if (selectedAlert && selectedAlert.id === id) {
      setSelectedAlert((prev) => prev ? { ...prev, status: 'RESOLVED' } : null);
    }
  };

  // Filter & Sort Logic
  const filteredAlerts = useMemo(() => {
    return alerts
      .filter((item) => {
        // Search filter
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchId = item.id.toLowerCase().includes(q);
          const matchType = (item.type_label || '').toLowerCase().includes(q);
          const matchDesc = (item.description || '').toLowerCase().includes(q);
          const matchCam = (item.camera_id || '').toLowerCase().includes(q);
          const matchGId = (item.global_id || '').toLowerCase().includes(q);
          if (!matchId && !matchType && !matchDesc && !matchCam && !matchGId) {
            return false;
          }
        }
        // Severity filter
        if (severityFilter !== 'ALL' && item.severity !== severityFilter) {
          return false;
        }
        // Camera filter
        if (cameraFilter !== 'ALL' && item.camera_id !== cameraFilter) {
          return false;
        }
        // Status filter
        if (statusFilter !== 'ALL') {
          if (statusFilter === 'NEW' && item.status !== 'NEW') return false;
          if (statusFilter === 'ACKNOWLEDGED' && item.status !== 'ACKNOWLEDGED') return false;
          if (statusFilter === 'RESOLVED' && item.status !== 'RESOLVED') return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortOrder === 'NEWEST') {
          return b.id.localeCompare(a.id);
        }
        if (sortOrder === 'OLDEST') {
          return a.id.localeCompare(b.id);
        }
        if (sortOrder === 'SEVERITY') {
          const rank = { HIGH: 3, MEDIUM: 2, LOW: 1 };
          return (rank[b.severity] || 0) - (rank[a.severity] || 0);
        }
        return 0;
      });
  }, [alerts, searchQuery, severityFilter, cameraFilter, statusFilter, sortOrder]);

  // Reset page when filters change
  const totalItems = filteredAlerts.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  const paginatedAlerts = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAlerts.slice(start, start + visibleCount);
  }, [filteredAlerts, currentPage, pageSize, visibleCount]);

  const hasActiveFilters =
    searchQuery !== '' ||
    severityFilter !== 'ALL' ||
    cameraFilter !== 'ALL' ||
    statusFilter !== 'ALL';

  const resetFilters = () => {
    setSearchQuery('');
    setSeverityFilter('ALL');
    setCameraFilter('ALL');
    setStatusFilter('ALL');
    setCurrentPage(1);
    setVisibleCount(pageSize);
  };

  // Stats calculation
  const newCount = alerts.filter(a => a.status === 'NEW').length;
  const highCount = alerts.filter(a => a.severity === 'HIGH').length;

  return (
    <div className="alerts-page">
      {/* Top Header */}
      <header className="alerts-page__header">
        <div className="alerts-page__title-cluster">
          <button className="alerts-page__back-btn" onClick={onBackToDashboard}>
            ← Back to Live Dashboard
          </button>

          <h1 className="alerts-page__title">
            Active Alerts
            <span className="alerts-page__count-badge">{totalItems} Alerts</span>
          </h1>
        </div>

        <div className="alerts-page__header-right">
          <div className="alerts-page__stat-pill">
            <span className="status-bar__dot status-bar__dot--live" />
            System Online
          </div>

          <div className="alerts-page__stat-pill">
            New: <span className="alerts-page__stat-val" style={{ color: 'var(--signal-red)' }}>{newCount}</span>
          </div>

          <div className="alerts-page__stat-pill">
            High Severity: <span className="alerts-page__stat-val" style={{ color: 'var(--signal-red)' }}>{highCount}</span>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="alerts-page__body">
        {/* Tactical Filters Strip */}
        <section className="alerts-page__filters" aria-label="Alert filters">
          <div className="alerts-page__filters-left">
            {/* Search Input */}
            <div className="alerts-page__search-wrap">
              <span className="alerts-page__search-icon">
                <Search size={14} />
              </span>
              <input
                type="text"
                className="alerts-page__search-input"
                placeholder="Search alert type, Global ID (G-017), description..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>

            {/* Severity Filter */}
            <div className="alerts-page__filter-group">
              <span className="alerts-page__filter-label">Severity:</span>
              {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                <button
                  key={sev}
                  className={`alerts-page__filter-btn ${severityFilter === sev ? 'alerts-page__filter-btn--active' : ''}`}
                  onClick={() => {
                    setSeverityFilter(sev);
                    setCurrentPage(1);
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>

            {/* Camera Filter */}
            <div className="alerts-page__filter-group">
              <span className="alerts-page__filter-label">Camera:</span>
              <select
                className="alerts-page__select"
                value={cameraFilter}
                onChange={(e) => {
                  setCameraFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="ALL">All Cameras</option>
                <option value="BOP-01">BOP-01 (Border Outpost 1)</option>
                <option value="CHECK-01">CHECK-01 (Checkpost 1)</option>
                <option value="PERIMETER-03">PERIMETER-03 (Sensor 3)</option>
                <option value="GATE-NORTH">GATE-NORTH (North Gate)</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="alerts-page__filter-group">
              <span className="alerts-page__filter-label">Status:</span>
              <select
                className="alerts-page__select"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="NEW">New / Unacknowledged</option>
                <option value="ACKNOWLEDGED">Acknowledged</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>

            {/* Sort Selector */}
            <div className="alerts-page__filter-group">
              <span className="alerts-page__filter-label">Sort:</span>
              <select
                className="alerts-page__select"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
              >
                <option value="NEWEST">Newest First</option>
                <option value="OLDEST">Oldest First</option>
                <option value="SEVERITY">Severity (High to Low)</option>
              </select>
            </div>

            {/* Reset button */}
            {hasActiveFilters && (
              <button className="alerts-page__reset-btn" onClick={resetFilters}>
                Clear Filters
              </button>
            )}
          </div>
        </section>

        {/* Alerts List Grid */}
        <section className="alerts-page__list-wrap">
          {paginatedAlerts.length === 0 ? (
            <div className="alerts-page__empty">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={14} /> No alerts match the selected filter criteria.
              </span>
              {hasActiveFilters && (
                <button className="alerts-page__filter-btn" onClick={resetFilters}>
                  Reset All Filters
                </button>
              )}
            </div>
          ) : (
            paginatedAlerts.map((item) => {
              const meta = EVENT_META[item.event_type] ?? { bg: '#52666d', color: '#8fa3aa' };
              const severityColor = SEVERITY_COLORS[item.severity] ?? '#8fa3aa';

              return (
                <div
                  key={item.id}
                  className="alert-card"
                  style={{ '--card-accent': severityColor }}
                  onClick={() => setSelectedAlert(item)}
                >
                  {/* Thumbnail Preview */}
                  <div className="alert-card__thumb">
                    <svg className="alert-card__thumb-svg" viewBox="0 0 120 76" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <rect width="120" height="76" fill="#0b1013" />
                      {/* Grid background */}
                      <path d="M0 25 L120 25 M0 50 L120 50 M40 0 L40 76 M80 0 L80 76" stroke="#162229" strokeWidth="0.8" />
                      {/* Target crosshair box */}
                      <rect x="35" y="16" width="50" height="44" fill="none" stroke={severityColor} strokeWidth="1.5" strokeDasharray="4 2" />
                      <circle cx="60" cy="30" r="7" fill="#1b2831" stroke={severityColor} strokeWidth="1" />
                      <path d="M48 55 C48 40, 72 40, 72 55 Z" fill="#1b2831" stroke={severityColor} strokeWidth="1" />
                    </svg>
                    <span className="alert-card__cam-tag">{item.camera_id}</span>
                  </div>

                  {/* Main Details */}
                  <div className="alert-card__main">
                    <div className="alert-card__top">
                      <span
                        className="badge-severity"
                        style={{
                          color: severityColor,
                          borderColor: severityColor,
                          background: `${severityColor}18`
                        }}
                      >
                        {item.severity}
                      </span>

                      <span className="alert-card__type-label">
                        <span><RenderAlertIcon eventType={item.event_type} /></span>
                        <span>{item.type_label}</span>
                      </span>

                      <span className={`badge-status badge-status--${(item.status || 'NEW').toLowerCase()}`}>
                        {item.status}
                      </span>
                    </div>

                    <div className="alert-card__desc">
                      {item.description}
                    </div>

                    <div className="alert-card__meta-strip">
                      <span className="alert-card__meta-item">
                        <span>Cam:</span>
                        <span className="alert-card__meta-val">{item.camera_id}</span>
                      </span>
                      <span>•</span>
                      <span className="alert-card__meta-item">
                        <span>Global ID:</span>
                        <span className="alert-card__meta-val alert-card__meta-val--accent">{item.global_id || 'N/A'}</span>
                      </span>
                      <span>•</span>
                      <span className="alert-card__meta-item">
                        <span>Time:</span>
                        <span className="alert-card__meta-val">{item.timestamp}</span>
                      </span>
                      <span>•</span>
                      <span className="alert-card__meta-item">
                        <span>Confidence:</span>
                        <span className="alert-card__meta-val">{item.confidence || '96%'}</span>
                      </span>
                    </div>
                  </div>

                  {/* Actions Buttons */}
                  <div className="alert-card__actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      className="alert-card__btn"
                      onClick={() => setSelectedAlert(item)}
                    >
                      View Details
                    </button>

                    {item.status !== 'ACKNOWLEDGED' && item.status !== 'RESOLVED' && (
                      <button
                        className="alert-card__btn alert-card__btn--ack"
                        onClick={() => handleAcknowledge(item.id)}
                      >
                        <Check size={11} style={{ display: 'inline', marginRight: '3px' }} /> Acknowledge
                      </button>
                    )}

                    {item.status !== 'RESOLVED' && (
                      <button
                        className="alert-card__btn alert-card__btn--resolve"
                        onClick={() => handleResolve(item.id)}
                      >
                        <ShieldCheck size={11} style={{ display: 'inline', marginRight: '3px' }} /> Resolve
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </section>

        {/* Pagination & Load More Footer */}
        <footer className="alerts-page__pagination-bar">
          <div className="alerts-page__page-info">
            Showing {paginatedAlerts.length > 0 ? (currentPage - 1) * pageSize + 1 : 0}–
            {Math.min(currentPage * pageSize, totalItems)} of {totalItems} Alerts
          </div>

          {/* Page Controls */}
          <div className="alerts-page__page-controls">
            <button
              className="alerts-page__page-btn"
              disabled={currentPage === 1}
              onClick={() => {
                setCurrentPage((prev) => Math.max(1, prev - 1));
                setVisibleCount(pageSize);
              }}
            >
              ◄ Previous
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                className={`alerts-page__page-btn ${currentPage === p ? 'alerts-page__page-btn--active' : ''}`}
                onClick={() => {
                  setCurrentPage(p);
                  setVisibleCount(pageSize);
                }}
              >
                {p}
              </button>
            ))}

            <button
              className="alerts-page__page-btn"
              disabled={currentPage >= totalPages}
              onClick={() => {
                setCurrentPage((prev) => Math.min(totalPages, prev + 1));
                setVisibleCount(pageSize);
              }}
            >
              Next ►
            </button>
          </div>

          {/* Load More Option */}
          {visibleCount < filteredAlerts.length && (
            <button
              className="alerts-page__load-more-btn"
              onClick={() => setVisibleCount((prev) => prev + pageSize)}
            >
              + Load More Alerts ({filteredAlerts.length - visibleCount} Remaining)
            </button>
          )}
        </footer>
      </main>

      {/* Alert Details Modal */}
      {selectedAlert && (
        <AlertDetailsModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
          onAcknowledge={handleAcknowledge}
          onResolve={handleResolve}
        />
      )}
    </div>
  );
}
