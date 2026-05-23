import os


def pytest_addoption(parser):
    group = parser.getgroup("pressure")
    group.addoption(
        "--pressure-scenario",
        choices=["light", "mid", "heavy", "custom"],
        default=os.getenv("PRESSURE_SCENARIO", "light"),
        help="Pressure scenario preset to run.",
    )
    group.addoption(
        "--pressure-base-url",
        default=os.getenv("PRESSURE_BASE_URL", "http://127.0.0.1:8000"),
        help="Backend base URL used by pressure tests.",
    )
    group.addoption("--pressure-users", type=int, default=int(os.getenv("PRESSURE_USERS", "50")))
    group.addoption(
        "--pressure-online-users",
        type=int,
        default=int(os.getenv("PRESSURE_ONLINE_USERS", "10")),
    )
    group.addoption("--pressure-rooms", type=int, default=int(os.getenv("PRESSURE_ROOMS", "50")))
    group.addoption(
        "--pressure-room-type",
        choices=["direct", "group"],
        default=os.getenv("PRESSURE_ROOM_TYPE", "direct"),
    )
    group.addoption(
        "--pressure-group-size",
        type=int,
        default=int(os.getenv("PRESSURE_GROUP_SIZE", "5")),
    )
    group.addoption(
        "--pressure-messages-per-room",
        type=int,
        default=int(os.getenv("PRESSURE_MESSAGES_PER_ROOM", "5")),
    )
    group.addoption(
        "--pressure-history-fetches",
        type=int,
        default=int(os.getenv("PRESSURE_HISTORY_FETCHES", "50")),
    )
    group.addoption(
        "--pressure-concurrency",
        type=int,
        default=int(os.getenv("PRESSURE_CONCURRENCY", "25")),
    )
    group.addoption(
        "--pressure-max-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_P95_MS", "0")),
        help="Custom send_message p95 threshold in ms. 0 uses preset defaults or disables custom threshold.",
    )
    group.addoption(
        "--pressure-max-register-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_REGISTER_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-login-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_LOGIN_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-ws-connect-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_WS_CONNECT_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-create-room-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_CREATE_ROOM_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-send-message-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_SEND_MESSAGE_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-fetch-messages-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_FETCH_MESSAGES_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-verify-persist-p95-ms",
        type=float,
        default=float(os.getenv("PRESSURE_MAX_VERIFY_PERSIST_P95_MS", "0")),
    )
    group.addoption(
        "--pressure-max-errors",
        type=int,
        default=int(os.getenv("PRESSURE_MAX_ERRORS", "0")),
    )
    group.addoption(
        "--pressure-fail-on-errors",
        action="store_true",
        default=os.getenv("PRESSURE_FAIL_ON_ERRORS", "").lower() == "true",
        help="Fail if pressure runner records any errors.",
    )
