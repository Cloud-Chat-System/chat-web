import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "backend"
    }


@app.get("/db-health")
def db_health():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        result = cur.fetchone()
        cur.close()
        conn.close()

        return {
            "status": "ok",
            "database": "connected",
            "result": result[0]
        }

    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/users")
def get_users():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, email, display_name, auth_provider, is_active
            FROM users
            ORDER BY id;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "display_name": row[3],
                "auth_provider": row[4],
                "is_active": row[5]
            }
            for row in rows
        ]

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/chat-rooms")
def get_chat_rooms():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                cr.id,
                cr.room_type,
                cr.name,
                cr.created_by,
                cr.last_message_at,
                cr.is_active
            FROM chat_rooms cr
            ORDER BY cr.last_message_at DESC NULLS LAST, cr.id DESC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "room_type": row[1],
                "name": row[2],
                "created_by": row[3],
                "last_message_at": row[4],
                "is_active": row[5]
            }
            for row in rows
        ]

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/chat-rooms/{chat_room_id}/messages")
def get_messages(chat_room_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                m.id,
                m.chat_room_id,
                m.sender_id,
                u.username,
                m.content,
                m.message_type,
                m.created_at,
                m.is_deleted
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.chat_room_id = %s
            ORDER BY m.created_at ASC;
        """, (chat_room_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "chat_room_id": row[1],
                "sender_id": row[2],
                "sender_username": row[3],
                "content": row[4],
                "message_type": row[5],
                "created_at": row[6],
                "is_deleted": row[7]
            }
            for row in rows
        ]

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/notifications/{user_id}")
def get_notifications(user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                n.id,
                n.user_id,
                n.chat_room_id,
                n.message_id,
                n.notification_type,
                n.is_read,
                n.created_at
            FROM notifications n
            WHERE n.user_id = %s
            ORDER BY n.created_at DESC;
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "chat_room_id": row[2],
                "message_id": row[3],
                "notification_type": row[4],
                "is_read": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/presence")
def get_presence():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                up.user_id,
                u.username,
                up.status,
                up.last_seen_at,
                up.updated_at
            FROM user_presence up
            JOIN users u ON u.id = up.user_id
            ORDER BY up.user_id;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "user_id": row[0],
                "username": row[1],
                "status": row[2],
                "last_seen_at": row[3],
                "updated_at": row[4]
            }
            for row in rows
        ]

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }