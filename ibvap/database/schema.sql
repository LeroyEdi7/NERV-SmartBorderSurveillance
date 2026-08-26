-- =========================================================
-- IBVAP - Intelligent Border Video Analytics Platform
-- PostgreSQL MVP Schema
-- =========================================================

-- =========================================================
-- 1. CAMERAS
-- =========================================================

CREATE TABLE cameras (
    camera_id VARCHAR(30) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(150),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    stream_url TEXT,

    status VARCHAR(20) DEFAULT 'offline'
        CHECK (status IN ('online', 'offline', 'error')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 2. ENTITIES
-- Global identities for people and vehicles
-- =========================================================

CREATE TABLE entities (
    entity_id VARCHAR(30) PRIMARY KEY,

    entity_type VARCHAR(30) NOT NULL
        CHECK (entity_type IN ('person', 'vehicle', 'object')),

    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(30) DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'unknown')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 3. VEHICLES
-- =========================================================

CREATE TABLE vehicles (
    vehicle_id VARCHAR(30) PRIMARY KEY,

    entity_id VARCHAR(30),

    plate_number VARCHAR(30),

    vehicle_type VARCHAR(50),

    color VARCHAR(30),

    first_seen TIMESTAMP,
    last_seen TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_vehicle_entity
        FOREIGN KEY (entity_id)
        REFERENCES entities(entity_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 4. WATCHLIST
-- Demo/local watchlist
-- =========================================================

CREATE TABLE watchlist (
    person_id VARCHAR(50) PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    embedding TEXT,

    status VARCHAR(30) DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 5. DETECTIONS
-- Raw AI detections from individual frames
-- =========================================================

CREATE TABLE detections (
    detection_id BIGSERIAL PRIMARY KEY,

    camera_id VARCHAR(30) NOT NULL,

    entity_id VARCHAR(30),

    object_type VARCHAR(50) NOT NULL,

    confidence REAL
        CHECK (confidence >= 0 AND confidence <= 1),

    bbox_x1 REAL,
    bbox_y1 REAL,
    bbox_x2 REAL,
    bbox_y2 REAL,

    track_id INTEGER,

    frame_id BIGINT,

    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_detection_camera
        FOREIGN KEY (camera_id)
        REFERENCES cameras(camera_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_detection_entity
        FOREIGN KEY (entity_id)
        REFERENCES entities(entity_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 6. ZONES
-- Virtual fences / restricted areas
-- =========================================================

CREATE TABLE zones (
    zone_id VARCHAR(30) PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    zone_type VARCHAR(30) NOT NULL
        CHECK (
            zone_type IN (
                'restricted',
                'warning',
                'safe',
                'custom'
            )
        ),

    camera_id VARCHAR(30),

    polygon JSONB NOT NULL,

    severity VARCHAR(20) DEFAULT 'HIGH'
        CHECK (
            severity IN (
                'LOW',
                'MEDIUM',
                'HIGH'
            )
        ),

    enabled BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_zone_camera
        FOREIGN KEY (camera_id)
        REFERENCES cameras(camera_id)
        ON DELETE CASCADE
);


-- =========================================================
-- 7. EVENTS
-- Important interpreted events
-- =========================================================

CREATE TABLE events (
    event_id VARCHAR(50) PRIMARY KEY,

    event_type VARCHAR(50) NOT NULL,

    camera_id VARCHAR(30),

    entity_id VARCHAR(30),

    severity VARCHAR(20) NOT NULL DEFAULT 'LOW'
        CHECK (
            severity IN (
                'LOW',
                'MEDIUM',
                'HIGH'
            )
        ),

    confidence REAL
        CHECK (
            confidence IS NULL
            OR (confidence >= 0 AND confidence <= 1)
        ),

    zone_id VARCHAR(30),

    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(30) DEFAULT 'NEW'
        CHECK (
            status IN (
                'NEW',
                'ACKNOWLEDGED',
                'RESOLVED',
                'DISMISSED'
            )
        ),

    snapshot_path TEXT,

    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_event_camera
        FOREIGN KEY (camera_id)
        REFERENCES cameras(camera_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_event_entity
        FOREIGN KEY (entity_id)
        REFERENCES entities(entity_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_event_zone
        FOREIGN KEY (zone_id)
        REFERENCES zones(zone_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 8. CROSS-CAMERA TRACKING
-- Records movement of an entity between cameras
-- =========================================================

CREATE TABLE cross_camera_tracks (
    track_id BIGSERIAL PRIMARY KEY,

    entity_id VARCHAR(30) NOT NULL,

    previous_camera_id VARCHAR(30),

    current_camera_id VARCHAR(30),

    previous_timestamp TIMESTAMP,

    current_seen_at TIMESTAMP,

    match_type VARCHAR(30),

    confidence REAL
        CHECK (
            confidence IS NULL
            OR (confidence >= 0 AND confidence <= 1)
        ),

    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_cross_entity
        FOREIGN KEY (entity_id)
        REFERENCES entities(entity_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_previous_camera
        FOREIGN KEY (previous_camera_id)
        REFERENCES cameras(camera_id)
        ON DELETE SET NULL,

    CONSTRAINT fk_current_camera
        FOREIGN KEY (current_camera_id)
        REFERENCES cameras(camera_id)
        ON DELETE SET NULL
);

-- =========================================================
-- 9. PERSON-VEHICLE ASSOCIATIONS
-- Links a person to a vehicle
-- =========================================================

CREATE TABLE person_vehicle_associations (
    association_id BIGSERIAL PRIMARY KEY,

    person_entity_id VARCHAR(30) NOT NULL,

    vehicle_entity_id VARCHAR(30) NOT NULL,

    camera_id VARCHAR(30),

    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    end_time TIMESTAMP,

    confidence REAL
        CHECK (
            confidence IS NULL
            OR (confidence >= 0 AND confidence <= 1)
        ),

    status VARCHAR(30) DEFAULT 'active'
        CHECK (
            status IN (
                'active',
                'ended'
            )
        ),

    metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT fk_person_entity
        FOREIGN KEY (person_entity_id)
        REFERENCES entities(entity_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_vehicle_entity
        FOREIGN KEY (vehicle_entity_id)
        REFERENCES entities(entity_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_association_camera
        FOREIGN KEY (camera_id)
        REFERENCES cameras(camera_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 10. ALERTS
-- Alerts shown to the operator
-- =========================================================

CREATE TABLE alerts (
    alert_id BIGSERIAL PRIMARY KEY,

    event_id VARCHAR(50) NOT NULL,

    title VARCHAR(200) NOT NULL,

    message TEXT,

    severity VARCHAR(20) NOT NULL
        CHECK (
            severity IN (
                'LOW',
                'MEDIUM',
                'HIGH'
            )
        ),

    status VARCHAR(30) DEFAULT 'ACTIVE'
        CHECK (
            status IN (
                'ACTIVE',
                'ACKNOWLEDGED',
                'RESOLVED'
            )
        ),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    acknowledged_at TIMESTAMP,

    resolved_at TIMESTAMP,

    CONSTRAINT fk_alert_event
        FOREIGN KEY (event_id)
        REFERENCES events(event_id)
        ON DELETE CASCADE
);


-- =========================================================
-- INDEXES
-- =========================================================

CREATE INDEX idx_detections_camera
ON detections(camera_id);

CREATE INDEX idx_detections_entity
ON detections(entity_id);

CREATE INDEX idx_detections_timestamp
ON detections(timestamp);

CREATE INDEX idx_events_camera
ON events(camera_id);

CREATE INDEX idx_events_entity
ON events(entity_id);

CREATE INDEX idx_events_type
ON events(event_type);

CREATE INDEX idx_events_timestamp
ON events(timestamp);

CREATE INDEX idx_events_severity
ON events(severity);

CREATE INDEX idx_alerts_status
ON alerts(status);

CREATE INDEX idx_cross_camera_entity
ON cross_camera_tracks(entity_id);

CREATE INDEX idx_vehicle_plate
ON vehicles(plate_number);


-- =========================================================
-- SAMPLE CAMERAS
-- =========================================================

INSERT INTO cameras (
    camera_id,
    name,
    location,
    latitude,
    longitude,
    stream_url,
    status
)
VALUES
(
    'BOP-01',
    'Border Outpost Camera 01',
    'Border Sector A',
    19.0760,
    72.8777,
    'rtsp://192.168.1.101:8554/live',
    'offline'
),
(
    'CHECK-01',
    'Checkpost Camera 01',
    'Checkpost Alpha',
    19.0800,
    72.8820,
    'rtsp://192.168.1.102:8554/live',
    'offline'
);


-- =========================================================
-- SAMPLE ZONE
-- =========================================================

INSERT INTO zones (
    zone_id,
    name,
    zone_type,
    camera_id,
    polygon,
    severity
)
VALUES
(
    'ZONE-01',
    'Restricted Area',
    'restricted',
    'BOP-01',
    '[
        [120,100],
        [600,100],
        [600,400],
        [120,400]
    ]'::jsonb,
    'HIGH'
);