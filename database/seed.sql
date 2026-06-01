WITH seed_users (
    id,
    username,
    email,
    display_name
) AS (
    VALUES
        (1, 'admin', 'admin@tsmc.com', '系統管理員'),
        (2, 'alice', 'alice@tsmc.com', 'Alice'),
        (3, 'bob', 'bob@tsmc.com', 'Bob')
)
INSERT INTO users (
    id,
    username,
    email,
    display_name,
    auth_provider,
    is_active
)
SELECT
    id,
    username,
    email,
    display_name,
    'local',
    TRUE
FROM seed_users
ON CONFLICT (username) DO NOTHING;

UPDATE users
SET
    password_hash = NULL,
    token_version = token_version + 1,
    updated_at = NOW()
WHERE (username, email) IN (
    ('admin', 'admin@tsmc.com'),
    ('alice', 'alice@tsmc.com'),
    ('bob', 'bob@tsmc.com')
)
AND password_hash IS NOT NULL;

WITH seed_presence (id, user_id) AS (
    VALUES
        (1, 1),
        (2, 2),
        (3, 3)
)
INSERT INTO user_presence (id, user_id, status)
SELECT id, user_id, 'offline'
FROM seed_presence
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO chat_rooms (
    id,
    name,
    room_type,
    created_by,
    last_message_at
)
VALUES
    (1, NULL, 'direct', 1, NOW()),
    (2, '製程整合小組', 'group', 1, NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO chat_room_members (
    id,
    room_id,
    user_id,
    is_admin,
    last_read_at
)
VALUES
    (1, 1, 1, FALSE, NOW()),
    (2, 1, 2, FALSE, NOW()),
    (3, 2, 1, TRUE, NOW()),
    (4, 2, 2, FALSE, NOW()),
    (5, 2, 3, FALSE, NOW())
ON CONFLICT (room_id, user_id) DO NOTHING;

INSERT INTO messages (
    id,
    room_id,
    sender_id,
    content,
    message_type,
    created_at
)
VALUES
    (1, 1, 1, 'Hi Alice，這是 direct chat 測試訊息。', 'text', NOW() - INTERVAL '30 minutes'),
    (2, 1, 2, '收到，我這邊也可以看到歷史訊息。', 'text', NOW() - INTERVAL '28 minutes'),
    (3, 2, 1, '大家下午三點同步測試結果。', 'text', NOW() - INTERVAL '15 minutes'),
    (4, 2, 3, 'OK，我會帶最新資料。', 'text', NOW() - INTERVAL '12 minutes')
ON CONFLICT (id) DO NOTHING;

UPDATE chat_rooms
SET last_message_at = (
    SELECT MAX(created_at)
    FROM messages
    WHERE messages.room_id = chat_rooms.id
)
WHERE EXISTS (
    SELECT 1
    FROM messages
    WHERE messages.room_id = chat_rooms.id
);

SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1), true);
SELECT setval('user_presence_id_seq', COALESCE((SELECT MAX(id) FROM user_presence), 1), true);
SELECT setval('chat_rooms_id_seq', COALESCE((SELECT MAX(id) FROM chat_rooms), 1), true);
SELECT setval('chat_room_members_id_seq', COALESCE((SELECT MAX(id) FROM chat_room_members), 1), true);
SELECT setval('messages_id_seq', COALESCE((SELECT MAX(id) FROM messages), 1), true);
