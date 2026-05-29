CREATE TABLE IF NOT EXISTS users (
    id                  SERIAL PRIMARY KEY,
    username            VARCHAR(50) UNIQUE NOT NULL,
    email               VARCHAR(255) UNIQUE,
    password_hash       TEXT,
    display_name        VARCHAR(100),
    avatar_url          TEXT,
    auth_provider       VARCHAR(30) DEFAULT 'local',
    provider_user_id    VARCHAR(255),
    token_version       INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_rooms (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100),
    room_type           VARCHAR(10) NOT NULL DEFAULT 'direct',
    created_by          INTEGER REFERENCES users(id),
    last_message_at     TIMESTAMP DEFAULT NOW(),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_room_members (
    id                  SERIAL PRIMARY KEY,
    room_id             INTEGER NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_admin            BOOLEAN DEFAULT FALSE,
    last_read_at        TIMESTAMP DEFAULT NOW(),
    joined_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_room_user UNIQUE(room_id, user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id                  SERIAL PRIMARY KEY,
    room_id             INTEGER NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    sender_id           INTEGER NOT NULL REFERENCES users(id),
    content             TEXT NOT NULL,
    message_type        VARCHAR(10) DEFAULT 'text',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type                VARCHAR(30) NOT NULL,
    content             TEXT,
    is_read             BOOLEAN DEFAULT FALSE,
    reference_id        INTEGER,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_presence (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status              VARCHAR(10) DEFAULT 'offline',
    last_seen_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_rooms_last_message_at
ON chat_rooms(last_message_at);

CREATE INDEX IF NOT EXISTS idx_chat_room_members_user_id
ON chat_room_members(user_id);

CREATE INDEX IF NOT EXISTS idx_chat_room_members_room_id
ON chat_room_members(room_id);

CREATE INDEX IF NOT EXISTS idx_messages_room_created_at
ON messages(room_id, created_at);

CREATE INDEX IF NOT EXISTS idx_notifications_user_is_read
ON notifications(user_id, is_read);

CREATE INDEX IF NOT EXISTS idx_user_presence_status
ON user_presence(status);
