import asyncio

import pytest

from .chat_pressure import make_args, run


pytestmark = pytest.mark.pressure


PRESETS = {
    "light": {
        "users": 50,
        "online_users": 10,
        "rooms": 50,
        "messages_per_room": 5,
        "history_fetches": 50,
        "concurrency": 25,
        "max_register_p95_ms": 1500,
        "max_login_p95_ms": 1500,
        "max_ws_connect_p95_ms": 1000,
        "max_create_room_p95_ms": 1000,
        "max_send_message_p95_ms": 1000,
        "max_fetch_messages_p95_ms": 1000,
        "max_verify_persist_p95_ms": 1000,
        "max_errors": 0,
        "fail_on_errors": True,
    },
    "mid": {
        "users": 300,
        "online_users": 100,
        "rooms": 300,
        "messages_per_room": 10,
        "history_fetches": 500,
        "concurrency": 50,
        "max_register_p95_ms": 2500,
        "max_login_p95_ms": 2500,
        "max_ws_connect_p95_ms": 1500,
        "max_create_room_p95_ms": 1500,
        "max_send_message_p95_ms": 1500,
        "max_fetch_messages_p95_ms": 1500,
        "max_verify_persist_p95_ms": 1500,
        "max_errors": 0,
        "fail_on_errors": True,
    },
    "heavy": {
        "users": 2000,
        "online_users": 500,
        "rooms": 2000,
        "messages_per_room": 20,
        "history_fetches": 5000,
        "concurrency": 100,
        "max_register_p95_ms": 5000,
        "max_login_p95_ms": 5000,
        "max_ws_connect_p95_ms": 3000,
        "max_create_room_p95_ms": 3000,
        "max_send_message_p95_ms": 3000,
        "max_fetch_messages_p95_ms": 3000,
        "max_verify_persist_p95_ms": 3000,
        "max_errors": 0,
        "fail_on_errors": False,
    },
}


def build_pressure_args(pytestconfig):
    scenario = pytestconfig.getoption("--pressure-scenario")
    if scenario == "custom":
        values = {
            "users": pytestconfig.getoption("--pressure-users"),
            "online_users": pytestconfig.getoption("--pressure-online-users"),
            "rooms": pytestconfig.getoption("--pressure-rooms"),
            "messages_per_room": pytestconfig.getoption("--pressure-messages-per-room"),
            "history_fetches": pytestconfig.getoption("--pressure-history-fetches"),
            "concurrency": pytestconfig.getoption("--pressure-concurrency"),
            "max_p95_ms": pytestconfig.getoption("--pressure-max-p95-ms"),
            "max_register_p95_ms": pytestconfig.getoption("--pressure-max-register-p95-ms"),
            "max_login_p95_ms": pytestconfig.getoption("--pressure-max-login-p95-ms"),
            "max_ws_connect_p95_ms": pytestconfig.getoption("--pressure-max-ws-connect-p95-ms"),
            "max_create_room_p95_ms": pytestconfig.getoption("--pressure-max-create-room-p95-ms"),
            "max_send_message_p95_ms": pytestconfig.getoption("--pressure-max-send-message-p95-ms"),
            "max_fetch_messages_p95_ms": pytestconfig.getoption("--pressure-max-fetch-messages-p95-ms"),
            "max_verify_persist_p95_ms": pytestconfig.getoption("--pressure-max-verify-persist-p95-ms"),
            "max_errors": pytestconfig.getoption("--pressure-max-errors"),
            "fail_on_errors": pytestconfig.getoption("--pressure-fail-on-errors"),
        }
    else:
        values = dict(PRESETS[scenario])
        custom_p95 = pytestconfig.getoption("--pressure-max-p95-ms")
        if custom_p95:
            values["max_send_message_p95_ms"] = custom_p95
        for option_name, value_name in [
            ("--pressure-max-register-p95-ms", "max_register_p95_ms"),
            ("--pressure-max-login-p95-ms", "max_login_p95_ms"),
            ("--pressure-max-ws-connect-p95-ms", "max_ws_connect_p95_ms"),
            ("--pressure-max-create-room-p95-ms", "max_create_room_p95_ms"),
            ("--pressure-max-send-message-p95-ms", "max_send_message_p95_ms"),
            ("--pressure-max-fetch-messages-p95-ms", "max_fetch_messages_p95_ms"),
            ("--pressure-max-verify-persist-p95-ms", "max_verify_persist_p95_ms"),
        ]:
            custom_value = pytestconfig.getoption(option_name)
            if custom_value:
                values[value_name] = custom_value
        custom_max_errors = pytestconfig.getoption("--pressure-max-errors")
        if custom_max_errors:
            values["max_errors"] = custom_max_errors
        if pytestconfig.getoption("--pressure-fail-on-errors"):
            values["fail_on_errors"] = True

    values.update(
        {
            "base_url": pytestconfig.getoption("--pressure-base-url"),
            "room_type": pytestconfig.getoption("--pressure-room-type"),
            "group_size": pytestconfig.getoption("--pressure-group-size"),
        }
    )
    return make_args(**values)


def test_pressure_scenario(pytestconfig):
    exit_code = asyncio.run(run(build_pressure_args(pytestconfig)))
    assert exit_code == 0
