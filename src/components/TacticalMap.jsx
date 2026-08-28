import { useEffect, useRef, useState } from 'react';
import './TacticalMap.css';

// ─── Layout constants (SVG viewport: 480 × 320) ──────────────────────────────
const W = 480;
const H = 320;

// Camera anchor positions on the floor plan
const CAMERAS = [
  { id: 'BOP-01',   x: 80,  y: 185, label: 'BOP-01'   },
  { id: 'CHECK-01', x: 380, y: 165, label: 'CHECK-01'  },
];

// Restricted zone polygon (SVG coords)
const ZONE_POLY = [
  { x: 160, y: 100 },
  { x: 280, y: 90  },
  { x: 295, y: 190 },
  { x: 200, y: 210 },
  { x: 145, y: 180 },
];

// G-017 patrol waypoints (loops)
const WAYPOINTS = [
  { x: 55,  y: 240 },   // outside – approaching BOP
  { x: 90,  y: 200 },   // near BOP-01
  { x: 155, y: 170 },   // entering zone edge
  { x: 210, y: 145 },   // deep inside zone ← red
  { x: 265, y: 120 },   // still inside zone
  { x: 310, y: 165 },   // exiting zone
  { x: 370, y: 160 },   // near CHECK-01
  { x: 420, y: 185 },   // past CHECK-01
  { x: 370, y: 220 },   // loop back
  { x: 250, y: 255 },   // outside below
  { x: 110, y: 265 },   // returning
  { x: 55,  y: 240 },   // back to start
];

// Dashed vehicle path (approx arc between cameras, below the zone)
const VEHICLE_PATH = `M 80 195 C 150 270 330 270 380 175`;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function polyStr(pts) {
  return pts.map(p => `${p.x},${p.y}`).join(' ');
}

/** Ray-casting point-in-polygon test */
function pointInPoly(px, py, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i].x, yi = poly[i].y;
    const xj = poly[j].x, yj = poly[j].y;
    if ((yi > py) !== (yj > py) &&
        px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

/** Linear interpolate between two waypoints */
function lerp(a, b, t) {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}

// ─── Grid lines for the floor plan background ────────────────────────────────
function GridLines() {
  const lines = [];
  const step = 40;
  for (let x = 0; x <= W; x += step) {
    lines.push(<line key={`v${x}`} x1={x} y1={0} x2={x} y2={H} />);
  }
  for (let y = 0; y <= H; y += step) {
    lines.push(<line key={`h${y}`} x1={0} y1={y} x2={W} y2={y} />);
  }
  return <g className="tmap__grid">{lines}</g>;
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function TacticalMap({ cameraStatus }) {
  const [markerPos, setMarkerPos] = useState(WAYPOINTS[0]);
  const [insideZone, setInsideZone]  = useState(false);
  const progressRef = useRef(0);   // 0..WAYPOINTS.length-1 (fractional)
  const rafRef      = useRef(null);

  useEffect(() => {
    const SPEED = 0.004; // waypoints per frame (~60fps)
    let last = performance.now();

    function tick(now) {
      const dt = Math.min(now - last, 50); // cap at 50ms
      last = now;
      progressRef.current = (progressRef.current + SPEED * (dt / 16.67)) % (WAYPOINTS.length - 1);

      const idx = Math.floor(progressRef.current);
      const t   = progressRef.current - idx;
      const pos = lerp(WAYPOINTS[idx], WAYPOINTS[idx + 1] ?? WAYPOINTS[0], t);

      setMarkerPos(pos);
      setInsideZone(pointInPoly(pos.x, pos.y, ZONE_POLY));
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  const markerColor = insideZone ? '#e14b3c' : '#34d9b4';
  const pulseClass  = insideZone ? 'tmap__pulse tmap__pulse--danger' : 'tmap__pulse';

  return (
    <div className="tmap">
      {/* ── Header ── */}
      <div className="tmap__head">
        <span className="tmap__title">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
            <rect x="0.5" y="0.5" width="11" height="11" rx="1" stroke="currentColor" strokeOpacity="0.6"/>
            <rect x="3" y="3" width="6" height="6" rx="0.5" fill="currentColor" fillOpacity="0.35"/>
          </svg>
          TACTICAL ZONE MAP
        </span>
        <span className="tmap__status">
          <span className="tmap__live-dot" />
          LIVE
        </span>
      </div>

      {/* ── SVG Floor Plan ── */}
      <div className="tmap__frame">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          xmlns="http://www.w3.org/2000/svg"
          className="tmap__svg"
          role="img"
          aria-label="Tactical floor plan"
        >
          <defs>
            {/* Glow filters */}
            <filter id="tmap-glow-teal" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur"/>
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="tmap-glow-red" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="blur"/>
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="tmap-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor="#34d9b4" floodOpacity="0.5"/>
            </filter>
            {/* Zone fill gradient */}
            <radialGradient id="zone-fill" cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor="#e14b3c" stopOpacity="0.18"/>
              <stop offset="100%" stopColor="#e14b3c" stopOpacity="0.04"/>
            </radialGradient>
            {/* Marker pulse animation */}
            <style>{`
              @keyframes tmap-pulse-teal {
                0%,100% { r: 9;  opacity: .7; }
                50%      { r: 14; opacity: 0; }
              }
              @keyframes tmap-pulse-red {
                0%,100% { r: 10; opacity: .8; }
                50%      { r: 16; opacity: 0; }
              }
              .pulse-ring-teal { animation: tmap-pulse-teal 1.8s ease-out infinite; }
              .pulse-ring-red  { animation: tmap-pulse-red  1.1s ease-out infinite; }
              @keyframes tmap-cam-blink {
                0%,90%,100% { opacity: 1; }
                95%         { opacity: 0.2; }
              }
              .cam-live { animation: tmap-cam-blink 3s ease-in-out infinite; }
            `}</style>
          </defs>

          {/* ── Background grid ── */}
          <rect width={W} height={H} fill="#0a0d0f"/>
          <GridLines />

          {/* ── Perimeter / floor boundary ── */}
          <rect
            x="16" y="12" width={W - 32} height={H - 24}
            rx="3" ry="3"
            fill="none"
            stroke="#223038"
            strokeWidth="1.5"
          />

          {/* ── Structural elements (rooms / partitions) ── */}
          {/* Left room */}
          <rect x="16" y="12" width="110" height="85" fill="none" stroke="#1d2d35" strokeWidth="1"/>
          {/* Right room */}
          <rect x="354" y="12" width={W-32-338} height="90" fill="none" stroke="#1d2d35" strokeWidth="1"/>
          {/* Bottom corridor */}
          <rect x="16" y="240" width={W - 32} height={H-252} fill="none" stroke="#1d2d35" strokeWidth="1"/>

          {/* ── Vehicle / dashed path ── */}
          <path
            d={VEHICLE_PATH}
            fill="none"
            stroke="#4e9fe8"
            strokeWidth="1.2"
            strokeDasharray="5 5"
            strokeLinecap="round"
            opacity="0.55"
          />

          {/* ── Restricted zone ── */}
          <polygon
            points={polyStr(ZONE_POLY)}
            fill="url(#zone-fill)"
            stroke="#e14b3c"
            strokeWidth="1.5"
            strokeDasharray="6 3"
            strokeLinejoin="round"
          />
          {/* Zone label */}
          <text
            x="213" y="158"
            textAnchor="middle"
            fontSize="9"
            fontFamily="'IBM Plex Mono', monospace"
            fontWeight="600"
            fill="#e14b3c"
            opacity="0.85"
            letterSpacing="0.06em"
          >RESTRICTED ZONE</text>

          {/* ── Camera markers ── */}
          {CAMERAS.map((cam) => {
            const status = cameraStatus?.[cam.id];
            const isHigh = status?.severity === 'HIGH';
            const camColor = isHigh ? '#e14b3c' : '#34d9b4';
            return (
              <g key={cam.id}>
                {/* Glow halo */}
                <circle
                  cx={cam.x} cy={cam.y} r="14"
                  fill={camColor}
                  fillOpacity="0.07"
                />
                {/* Camera icon hexagon background */}
                <circle
                  cx={cam.x} cy={cam.y} r="9"
                  fill="#10161a"
                  stroke={camColor}
                  strokeWidth="1.5"
                  filter={isHigh ? 'url(#tmap-glow-red)' : 'url(#tmap-shadow)'}
                />
                {/* Camera icon */}
                <text
                  x={cam.x} y={cam.y + 3.5}
                  textAnchor="middle"
                  fontSize="9"
                  fill={camColor}
                  className="cam-live"
                >⊙</text>
                {/* Live dot */}
                <circle
                  cx={cam.x + 8} cy={cam.y - 8} r="2.5"
                  fill={camColor}
                  className="cam-live"
                />
                {/* Label pill */}
                <rect
                  x={cam.x - 26} y={cam.y + 13}
                  width="52" height="14"
                  rx="2"
                  fill="#161f24"
                  stroke="#223038"
                  strokeWidth="0.8"
                />
                <text
                  x={cam.x} y={cam.y + 23}
                  textAnchor="middle"
                  fontSize="8"
                  fontFamily="'IBM Plex Mono', monospace"
                  fontWeight="500"
                  fill={camColor}
                  letterSpacing="0.04em"
                >{cam.label}</text>
              </g>
            );
          })}

          {/* ── G-017 moving marker ── */}
          <g>
            {/* Pulse ring */}
            <circle
              cx={markerPos.x} cy={markerPos.y}
              r="9"
              fill="none"
              stroke={markerColor}
              strokeWidth="1"
              opacity="0"
              className={insideZone ? 'pulse-ring-red' : 'pulse-ring-teal'}
            />
            {/* Core dot */}
            <circle
              cx={markerPos.x} cy={markerPos.y}
              r="5"
              fill={markerColor}
              stroke="#0a0d0f"
              strokeWidth="1.5"
              filter={insideZone ? 'url(#tmap-glow-red)' : 'url(#tmap-glow-teal)'}
            />
            {/* Label */}
            <rect
              x={markerPos.x + 8} y={markerPos.y - 10}
              width="36" height="14"
              rx="2"
              fill="#161f24"
              stroke={markerColor}
              strokeWidth="0.8"
              opacity="0.92"
            />
            <text
              x={markerPos.x + 26} y={markerPos.y}
              textAnchor="middle"
              fontSize="8.5"
              fontFamily="'IBM Plex Mono', monospace"
              fontWeight="600"
              fill={markerColor}
            >G-017</text>
          </g>

          {/* ── Corner crosshairs (tactical decoration) ── */}
          {[
            [20, 16], [W - 20, 16], [20, H - 16], [W - 20, H - 16]
          ].map(([cx, cy], i) => (
            <g key={i} stroke="#34d9b4" strokeWidth="0.8" opacity="0.25">
              <line x1={cx - 5} y1={cy} x2={cx + 5} y2={cy}/>
              <line x1={cx} y1={cy - 5} x2={cx} y2={cy + 5}/>
            </g>
          ))}
        </svg>
      </div>

      {/* ── Legend ── */}
      <div className="tmap__legend">
        <span className="tmap__legend-item">
          <span className="tmap__legend-dash" style={{ background: '#4e9fe8' }}/>
          Vehicle Path
        </span>
        <span className="tmap__legend-item">
          <span className="tmap__legend-dot" style={{ background: '#34d9b4' }}/>
          Cameras
        </span>
        <span className="tmap__legend-item">
          <span className="tmap__legend-dot" style={{ background: '#e14b3c' }}/>
          Restricted Zone
        </span>
        <span className="tmap__legend-item tmap__legend-g017" style={{ color: insideZone ? '#e14b3c' : '#34d9b4' }}>
          <span className="tmap__legend-dot" style={{ background: insideZone ? '#e14b3c' : '#34d9b4' }}/>
          G-017{insideZone ? ' [IN RESTRICTED ZONE]' : ''}
        </span>
      </div>
    </div>
  );
}
