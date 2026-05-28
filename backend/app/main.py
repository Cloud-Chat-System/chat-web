"""FastAPI application entry point with WebSocket support."""

from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import decode_token
from .config import BACKEND_CONTAINER_PORT, BACKEND_HOST, CORS_ALLOWED_ORIGINS, FRONTEND_URL
from .database import Base, engine, get_db
from .models import ChatRoomMember, UserPresence
from .routers import auth_router, chatroom_router, user_router
from .ws_manager import ws_manager

HTTP_REQUESTS_TOTAL = Counter(
    "chat_web_http_requests_total",
    "Total HTTP requests handled by the backend.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "chat_web_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
WEBSOCKET_CONNECTIONS_ACTIVE = Gauge(
    "chat_web_websocket_connections_active",
    "Active WebSocket connections.",
)
WEBSOCKET_CONNECTIONS_TOTAL = Counter(
    "chat_web_websocket_connections_total",
    "Total accepted WebSocket connections.",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="TSMC Messenger API",
    description="TSMC Messenger backend API",
    version="1.0.0",
)

allowed_origins = list(CORS_ALLOWED_ORIGINS)
if FRONTEND_URL and FRONTEND_URL not in allowed_origins:
    allowed_origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chatroom_router.router)
app.include_router(user_router.router)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def record_http_metrics(request, call_next):
    """Expose a small, stable set of request metrics for Grafana dashboards."""
    start = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - start
    path = request.url.path

    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        path=path,
        status=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path).observe(duration)
    return response


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "TSMC Messenger API"}


def _check_database_health() -> tuple[bool, str]:
    """Verify that the database is reachable."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception:
        return False, "unavailable"


@app.get("/api/health")
def api_health_check():
    """Readiness check endpoint with database status."""
    db_ok, db_status = _check_database_health()
    payload = {
        "service": "TSMC Messenger API",
        "status": "ok" if db_ok else "degraded",
        "database": db_status,
    }
    if not db_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time messaging.
    Client must send a JWT token as the first message after connecting.
    """
    user_id = None
    connection_tracked = False
    db: Session = next(get_db())
    try:
        await websocket.accept()
        WEBSOCKET_CONNECTIONS_TOTAL.inc()
        WEBSOCKET_CONNECTIONS_ACTIVE.inc()
        connection_tracked = True

        auth_data = await websocket.receive_json()
        token = auth_data.get("token", "")

        try:
            payload = decode_token(token)
            user_id = int(payload.get("sub", 0))
        except Exception:
            await websocket.send_json({"type": "error", "message": "Unauthorized"})
            await websocket.close()
            return

        if user_id not in ws_manager.active_connections:
            ws_manager.active_connections[user_id] = set()
        ws_manager.active_connections[user_id].add(websocket)

        presence = db.query(UserPresence).filter(UserPresence.user_id == user_id).first()
        if presence:
            presence.status = "online"
            db.commit()

        contact_ids = _get_contact_ids(user_id, db)
        await ws_manager.broadcast_presence(user_id, "online", contact_ids)
        await websocket.send_json({"type": "connected", "user_id": user_id})

        while True:
            data = await websocket.receive_json()
            if data.get("type", "") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if user_id:
            ws_manager.disconnect(websocket, user_id)

            if not ws_manager.is_online(user_id):
                try:
                    presence = db.query(UserPresence).filter(UserPresence.user_id == user_id).first()
                    if presence:
                        presence.status = "offline"
                        db.commit()

                    contact_ids = _get_contact_ids(user_id, db)
                    await ws_manager.broadcast_presence(user_id, "offline", contact_ids)
                except Exception:
                    pass

        db.close()
        if connection_tracked:
            WEBSOCKET_CONNECTIONS_ACTIVE.dec()


def _get_contact_ids(user_id: int, db: Session) -> list:
    """Get all user IDs that share a chat room with the given user."""
    room_ids = [
        member.room_id
        for member in db.query(ChatRoomMember).filter(ChatRoomMember.user_id == user_id).all()
    ]
    if not room_ids:
        return []

    contact_ids = set()
    for member in db.query(ChatRoomMember).filter(ChatRoomMember.room_id.in_(room_ids)).all():
        if member.user_id != user_id:
            contact_ids.add(member.user_id)

    return list(contact_ids)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=BACKEND_HOST, port=BACKEND_CONTAINER_PORT, reload=True)
