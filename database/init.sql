-- =========================================
-- Chat App PostgreSQL Schema v1
-- =========================================

-- 1. users
CREATE TABLE IF NOT EXISTS users (
    id                  BIGSERIAL PRIMARY KEY,
    username            VARCHAR(50) UNIQUE NOT NULL,
    email               VARCHAR(255) UNIQUE,
    password_hash       TEXT,
    display_name        VARCHAR(100),
    avatar_url          TEXT,
    auth_provider       VARCHAR(30) DEFAULT 'local',
    provider_user_id    VARCHAR(255),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2. chat_rooms
CREATE TABLE IF NOT EXISTS chat_rooms (
    id                  BIGSERIAL PRIMARY KEY,
    room_type           VARCHAR(20) NOT NULL,
    name                VARCHAR(100),
    created_by          BIGINT REFERENCES users(id),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    last_message_at     TIMESTAMP,
    is_active           BOOLEAN DEFAULT TRUE
);

-- 3. chat_room_members
CREATE TABLE IF NOT EXISTS chat_room_members (
    id                      BIGSERIAL PRIMARY KEY,
    chat_room_id            BIGINT NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    user_id                 BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role                    VARCHAR(20) DEFAULT 'member',
    joined_at               TIMESTAMP NOT NULL DEFAULT NOW(),
    last_read_message_id    BIGINT,
    UNIQUE(chat_room_id, user_id)
);

-- 4. messages
CREATE TABLE IF NOT EXISTS messages (
    id                  BIGSERIAL PRIMARY KEY,
    chat_room_id        BIGINT NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
    sender_id           BIGINT NOT NULL REFERENCES users(id),
    content             TEXT NOT NULL,
    message_type        VARCHAR(20) DEFAULT 'text',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    is_deleted          BOOLEAN DEFAULT FALSE
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_chat_room_members_last_read_message'
    ) THEN
        ALTER TABLE chat_room_members
        ADD CONSTRAINT fk_chat_room_members_last_read_message
        FOREIGN KEY (last_read_message_id)
        REFERENCES messages(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- 5. notifications
CREATE TABLE IF NOT EXISTS notifications (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_room_id        BIGINT REFERENCES chat_rooms(id) ON DELETE CASCADE,
    message_id          BIGINT REFERENCES messages(id) ON DELETE CASCADE,
    notification_type   VARCHAR(30) NOT NULL,
    is_read             BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 6. user_presence
CREATE TABLE IF NOT EXISTS user_presence (
    user_id             BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'offline',
    last_seen_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =========================================
-- Indexes
-- =========================================

CREATE INDEX IF NOT EXISTS idx_messages_room_created_at
ON messages(chat_room_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_room_members_user_id
ON chat_room_members(user_id);

CREATE INDEX IF NOT EXISTS idx_chat_room_members_room_id
ON chat_room_members(chat_room_id);

CREATE INDEX IF NOT EXISTS idx_chat_rooms_last_message_at
ON chat_rooms(last_message_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_user_is_read
ON notifications(user_id, is_read);

CREATE INDEX IF NOT EXISTS idx_user_presence_status
ON user_presence(status);