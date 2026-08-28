import { MapContainer, TileLayer, Marker, Polygon, Tooltip } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './ZoneMap.css';
import { CAMERAS, ZONE, SEVERITY_COLOR } from '../data/scenario';

function markerIcon(color) {
  return L.divIcon({
    className: 'zone-map__marker-wrap',
    html: `<span class="zone-map__marker" style="--c:${color}"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export default function ZoneMap({ cameraStatus }) {
  const center = [
    (CAMERAS[0].lat + CAMERAS[1].lat) / 2,
    (CAMERAS[0].lng + CAMERAS[1].lng) / 2,
  ];

  return (
    <div className="zone-map">
      <div className="zone-map__head">
        <span>Zone map</span>
        <span className="zone-map__legend">
          <i style={{ background: 'var(--signal-red)' }} /> restricted
        </span>
      </div>
      <div className="zone-map__frame">
        <MapContainer
          center={center}
          zoom={15}
          zoomControl={false}
          attributionControl={false}
          style={{ height: '100%', width: '100%', background: '#0c1114' }}
        >
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />

          <Polygon
            positions={ZONE.polygon}
            pathOptions={{
              color: 'var(--signal-red)',
              weight: 1.5,
              dashArray: '4 4',
              fillColor: 'var(--signal-red)',
              fillOpacity: 0.08,
            }}
          >
            <Tooltip direction="top" permanent={false}>{ZONE.zone_name}</Tooltip>
          </Polygon>

          {CAMERAS.map((cam) => {
            const status = cameraStatus[cam.camera_id];
            const color = status ? SEVERITY_COLOR[status.severity] : 'var(--signal-teal)';
            return (
              <Marker
                key={cam.camera_id}
                position={[cam.lat, cam.lng]}
                icon={markerIcon(color)}
              >
                <Tooltip direction="top">{cam.camera_id}</Tooltip>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
