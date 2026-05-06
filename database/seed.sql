-- =========================================
-- Chat App Seed Data v1
-- =========================================

-- Users
INSERT INTO users (
    id,
    username,
    email,
    password_hash,
    display_name,
    avatar_url,
    auth_provider,
    provider_user_id,
    is_active
)
VALUES
(
    1,
    'user_a',
    'user_a@example.com',
    '$2b$12$example_hash_user_a',
    'User A',
    NULL,
    'local',
    NULL,
    TRUE
),
(
    2,
    'user_b',
    'user_b@example.com',
    '$2b$12$example_hash_user_b',
    'User B',
    NULL,
    'local',
    NULL,
    TRUE
),
(
    3,
    'admin',
    'admin@example.com',
    '$2b$12$example_hash_admin',
    'Admin',
    NULL,
    'local',
    NULL,
    TRUE
)
ON CONFLICT (username) DO NOTHING;

-- Chat room: direct room between user_a and user_b
INSERT INTO chat_rooms (
    id,
    room_type,
    name,
    created_by,
    last_message_at,
    is_active
)
VALUES
(
    1,
    'direct',
    NULL,
    1,
    NOW(),
    TRUE
)
ON CONFLICT (id) DO NOTHING;

-- Chat room members
INSERT INTO chat_room_members (
    id,
    chat_room_id,
    user_id,
    role
)
VALUES
(
    1,
    1,
    1,
    'member'
),
(
    2,
    1,
    2,
    'member'
)
ON CONFLICT (chat_room_id, user_id) DO NOTHING;

-- Messages
INSERT INTO messages (
    id,
    chat_room_id,
    sender_id,
    content,
    message_type,
    is_deleted
)
VALUES
(
    1,
    1,
    1,
    'Hello, this is User A.',
    'text',
    FALSE
),
(
    2,
    1,
    2,
    'Hi, this is User B.',
    'text',
    FALSE
),
(
    3,
    1,
    1,
    'This is a seed message for testing chat history.',
    'text',
    FALSE
)
ON CONFLICT (id) DO NOTHING;

-- Update chat room last message time
UPDATE chat_rooms
SET last_message_at = (
    SELECT MAX(created_at)
    FROM messages
    WHERE chat_room_id = 1
)
WHERE id = 1;

-- Update last read message
UPDATE chat_room_members
SET last_read_message_id = 3
WHERE chat_room_id = 1
AND user_id = 1;

UPDATE chat_room_members
SET last_read_message_id = 2
WHERE chat_room_id = 1
AND user_id = 2;

-- Notifications
INSERT INTO notifications (
    id,
    user_id,
    chat_room_id,
    message_id,
    notification_type,
    is_read
)
VALUES
(
    1,
    2,
    1,
    1,
    'new_message',
    TRUE
),
(
    2,
    1,
    1,
    2,
    'new_message',
    TRUE
),
(
    3,
    2,
    1,
    3,
    'new_message',
    FALSE
)
ON CONFLICT (id) DO NOTHING;

-- User presence
INSERT INTO user_presence (
    user_id,
    status,
    last_seen_at
)
VALUES
(
    1,
    'online',
    NOW()
),
(
    2,
    'offline',
    NOW()
),
(
    3,
    'offline',
    NOW()
)
ON CONFLICT (user_id) DO NOTHING;

-- Reset sequences after manually inserting fixed IDs
SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1), true);
SELECT setval('chat_rooms_id_seq', COALESCE((SELECT MAX(id) FROM chat_rooms), 1), true);
SELECT setval('chat_room_members_id_seq', COALESCE((SELECT MAX(id) FROM chat_room_members), 1), true);
SELECT setval('messages_id_seq', COALESCE((SELECT MAX(id) FROM messages), 1), true);
SELECT setval('notifications_id_seq', COALESCE((SELECT MAX(id) FROM notifications), 1), true);