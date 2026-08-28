import { useState, useMemo } from 'react';
import { Search, AlertTriangle, User, Car, Zap } from 'lucide-react';
import './GlobalTracksPage.css';
import { INITIAL_TRACKS } from '../data/mockTracks';
import GlobalTrackDetailsModal from './GlobalTrackDetailsModal';
import TacticalSnapshot from './TacticalSnapshot';

export default function GlobalTracksPage({ onBackToDashboard }) {
  const [tracks, setTracks] = useState(INITIAL_TRACKS);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [vehicleFilter, setVehicleFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('NEWEST');

  const [selectedTrack, setSelectedTrack] = useState(null);

  const filteredTracks = useMemo(() => {
    return tracks
      .filter((tr) => {
        // Search filter
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchId = tr.id.toLowerCase().includes(q);
          const matchCam = (tr.last_camera || '').toLowerCase().includes(q);
          const matchPlate = tr.vehicle?.plate ? tr.vehicle.plate.toLowerCase().includes(q) : false;
          const matchClothing = (tr.clothing || '').toLowerCase().includes(q);
          if (!matchId && !matchCam && !matchPlate && !matchClothing) return false;
        }

        // Status / Risk filter
        if (statusFilter !== 'ALL') {
          if (statusFilter === 'ACTIVE' && tr.status !== 'ACTIVE') return false;
          if (statusFilter === 'MONITORED' && tr.status !== 'MONITORED') return false;
          if (statusFilter === 'CLOSED' && tr.status !== 'CLOSED') return false;
        }

        // Vehicle filter
        if (vehicleFilter !== 'ALL') {
          if (vehicleFilter === 'VEHICLE' && !tr.vehicle) return false;
          if (vehicleFilter === 'PERSON_ONLY' && tr.vehicle) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortOrder === 'NEWEST') {
          return b.last_time.localeCompare(a.last_time);
        }
        if (sortOrder === 'CONFIDENCE') {
          return b.confidence_num - a.confidence_num;
        }
        if (sortOrder === 'EVENTS') {
          return b.event_count - a.event_count;
        }
        return 0;
      });
  }, [tracks, searchQuery, statusFilter, vehicleFilter, sortOrder]);

  const hasActiveFilters = searchQuery !== '' || statusFilter !== 'ALL' || vehicleFilter !== 'ALL';

  const resetFilters = () => {
    setSearchQuery('');
    setStatusFilter('ALL');
    setVehicleFilter('ALL');
  };

  const activeCount = tracks.filter((t) => t.status === 'ACTIVE').length;

  return (
    <div className="tracks-page">
      {/* Top Header */}
      <header className="tracks-page__header">
        <div className="tracks-page__title-cluster">
          <button className="alerts-page__back-btn" onClick={onBackToDashboard}>
            ← Back to Live Dashboard
          </button>
          <h1 className="tracks-page__title">
            Global Tracks
            <span className="tracks-page__count-badge">{filteredTracks.length} Target Tracks</span>
          </h1>
        </div>

        <div className="alerts-page__header-right">
          <div className="alerts-page__stat-pill">
            <span className="status-bar__dot status-bar__dot--live" />
            System Online
          </div>
          <div className="alerts-page__stat-pill">
            Active Targets: <span className="alerts-page__stat-val" style={{ color: 'var(--signal-red)' }}>{activeCount}</span>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="tracks-page__body">
        {/* Filters Toolbar */}
        <section className="tracks-page__filters" aria-label="Global tracks filters">
          <div className="alerts-page__filters-left">
            {/* Search Input */}
            <div className="alerts-page__search-wrap">
              <span className="alerts-page__search-icon">
                <Search size={14} />
              </span>
              <input
                type="text"
                className="alerts-page__search-input"
                placeholder="Search target ID (G-017), plate, camera..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Status / Risk Filter */}
            <div className="alerts-page__filter-group">
              <span className="alerts-page__filter-label">Status:</span>
              {['ALL', 'ACTIVE', 'MONITORED', 'CLOSED'].map((st) => (
                <button
                  key={st}
                  className={`alerts-page__filter-btn ${statusFilter === st ? 'alerts-page__filter-btn--active' : ''}`}
                  onClick={() => setStatusFilter(st)}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Vehicle Association Filter */}
            <div className="alerts-page__filter-group">
              <span className="alerts-page__filter-label">Vehicle:</span>
              <select
                className="alerts-page__select"
                value={vehicleFilter}
                onChange={(e) => setVehicleFilter(e.target.value)}
              >
                <option value="ALL">All Targets</option>
                <option value="VEHICLE">Vehicle Associated</option>
                <option value="PERSON_ONLY">Person Only</option>
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
                <option value="NEWEST">Newest Activity</option>
                <option value="CONFIDENCE">Highest Confidence</option>
                <option value="EVENTS">Event Count</option>
              </select>
            </div>

            {hasActiveFilters && (
              <button className="alerts-page__reset-btn" onClick={resetFilters}>
                Clear Filters
              </button>
            )}
          </div>
        </section>

        {/* Responsive Track Card Grid */}
        <section className="tracks-page__grid">
          {filteredTracks.length === 0 ? (
            <div className="alerts-page__empty" style={{ gridColumn: '1 / -1' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={14} /> No target tracks found matching the search criteria.
              </span>
              {hasActiveFilters && (
                <button className="alerts-page__filter-btn" onClick={resetFilters}>
                  Reset Filters
                </button>
              )}
            </div>
          ) : (
            filteredTracks.map((tr) => {
              const severityColor = tr.severity === 'HIGH' ? '#e14b3c' : tr.severity === 'MEDIUM' ? '#e8a13d' : '#34d9b4';

              return (
                <div
                  key={tr.id}
                  className="track-card"
                  style={{ '--track-accent': severityColor }}
                  onClick={() => setSelectedTrack(tr)}
                >
                  {/* Card Top */}
                  <div className="track-card__top">
                    <div className="track-card__avatar-cluster">
                      <div className="track-card__avatar" style={{ borderColor: severityColor }}>
                        <User size={14} />
                      </div>
                      <div>
                        <div className="track-card__id">{tr.id}</div>
                        <span className={`badge-status badge-status--${tr.status.toLowerCase()}`}>
                          {tr.status}
                        </span>
                      </div>
                    </div>

                    <span
                      className="badge-severity"
                      style={{
                        color: severityColor,
                        borderColor: severityColor,
                        background: `${severityColor}18`
                      }}
                    >
                      {tr.severity}
                    </span>
                  </div>

                  {/* Camera Snapshot Frame Thumbnail */}
                  <div style={{ margin: '2px 0' }}>
                    <TacticalSnapshot
                      type={tr.vehicle ? 'vehicle' : 'person'}
                      cameraId={tr.last_camera}
                      timestamp={tr.last_time}
                      targetId={tr.id}
                      accentColor={severityColor}
                      aspectRatio="16/9"
                      height="110px"
                    />
                  </div>

                  {/* Confidence Bar */}
                  <div className="track-card__confidence-strip">
                    <div className="track-card__conf-label">
                      <span>RE-ID CONFIDENCE</span>
                      <span className="track-card__conf-val">{tr.confidence}</span>
                    </div>
                    <div className="track-card__conf-bar">
                      <div className="track-card__conf-fill" style={{ width: `${tr.confidence_num}%` }} />
                    </div>
                  </div>

                  {/* Info Rows */}
                  <div className="track-card__info-rows">
                    <div className="track-card__info-row">
                      <span className="track-card__key">Last Camera:</span>
                      <span className="track-card__val">{tr.last_camera} ({tr.last_time})</span>
                    </div>
                    <div className="track-card__info-row">
                      <span className="track-card__key">Vehicle:</span>
                      <span className="track-card__val track-card__val--vehicle">
                        {tr.vehicle ? (
                          <span><Car size={11} style={{ display: 'inline', marginRight: '3px' }} /> {tr.vehicle.plate}</span>
                        ) : 'None'}
                      </span>
                    </div>
                    <div className="track-card__info-row">
                      <span className="track-card__key">Watchlist:</span>
                      <span className="track-card__val" style={{ color: 'var(--signal-amber)', fontSize: '10px' }}>
                        {tr.watchlist_status}
                      </span>
                    </div>
                  </div>

                  {/* Card Footer / Action */}
                  <div className="track-card__footer">
                    <span className="track-card__event-badge">
                      <Zap size={11} style={{ display: 'inline', marginRight: '3px' }} /> {tr.event_count} Logged Events
                    </span>
                    <button className="alert-card__btn" onClick={(e) => {
                      e.stopPropagation();
                      setSelectedTrack(tr);
                    }}>
                      View Track →
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </section>
      </main>

      {/* Global Track Details Modal */}
      {selectedTrack && (
        <GlobalTrackDetailsModal
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
        />
      )}
    </div>
  );
}
