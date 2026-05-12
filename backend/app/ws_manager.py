"""WebSocket connection manager for real-time messaging."""

from typing import Dict, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        # user_id -> set of WebSocket connections (supports multiple tabs/devices)
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    def is_online(self, user_id: int) -> bool:
        """Check if a user has any active connections."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def get_online_user_ids(self) -> list:
        """Return list of all currently connected user IDs."""
        return list(self.active_connections.keys())

    async def send_to_user(self, user_id: int, message: dict):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            dead_connections = set()
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_connections.add(ws)
            # Clean up dead connections
            for ws in dead_connections:
                self.active_connections[user_id].discard(ws)

    async def send_to_room(self, member_ids: list, message: dict, exclude_user_id: int = None):
        """Send a message to all members of a chat room."""
        for user_id in member_ids:
            if exclude_user_id and user_id == exclude_user_id:
                continue
            await self.send_to_user(user_id, message)

    async def broadcast_presence(self, user_id: int, status: str, to_user_ids: list):
        """Broadcast a user's online/offline status to specified users."""
        message = {
            "type": "presence",
            "user_id": user_id,
            "status": status,
        }
        for uid in to_user_ids:
            if uid != user_id:
                await self.send_to_user(uid, message)


# Singleton instance
ws_manager = ConnectionManager()
