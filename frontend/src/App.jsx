import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

const initialRequestState = {
  loading: true,
  error: "",
  data: null,
};

const sectionStyle = {
  marginTop: "24px",
  padding: "16px",
  border: "1px solid #d6d9e0",
  borderRadius: "12px",
  background: "#ffffff",
};

async function fetchJson(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`);
  }

  return response.json();
}

function getArrayPayload(payload, label) {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (payload && typeof payload === "object" && payload.error) {
    throw new Error(`${label}: ${payload.error}`);
  }

  throw new Error(`${label}: unexpected response format`);
}

function StatusBadge({ value, okValue }) {
  const isOk = value === okValue;

  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 10px",
        borderRadius: "999px",
        fontSize: "14px",
        fontWeight: 700,
        color: isOk ? "#166534" : "#991b1b",
        background: isOk ? "#dcfce7" : "#fee2e2",
      }}
    >
      {value}
    </span>
  );
}

function RequestPanel({ title, state, successContent, emptyText = "No data" }) {
  let body = null;

  if (state.loading) {
    body = <p>Loading...</p>;
  } else if (state.error) {
    body = <p style={{ color: "#b91c1c" }}>{state.error}</p>;
  } else if (successContent) {
    body = successContent;
  } else {
    body = <p>{emptyText}</p>;
  }

  return (
    <section style={sectionStyle}>
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {body}
    </section>
  );
}

function App() {
  const [health, setHealth] = useState(initialRequestState);
  const [dbHealth, setDbHealth] = useState(initialRequestState);
  const [users, setUsers] = useState(initialRequestState);
  const [chatRooms, setChatRooms] = useState(initialRequestState);
  const [messages, setMessages] = useState(initialRequestState);
  const [presence, setPresence] = useState(initialRequestState);
  const [selectedRoomId, setSelectedRoomId] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const healthPayload = await fetchJson("/health");
        if (!cancelled) {
          setHealth({ loading: false, error: "", data: healthPayload });
        }
      } catch (error) {
        if (!cancelled) {
          setHealth({ loading: false, error: error.message, data: null });
        }
      }

      try {
        const dbPayload = await fetchJson("/db-health");
        if (!cancelled) {
          const dbError = dbPayload.status === "error" ? dbPayload.error || "Database check failed" : "";
          setDbHealth({ loading: false, error: dbError, data: dbPayload });
        }
      } catch (error) {
        if (!cancelled) {
          setDbHealth({ loading: false, error: error.message, data: null });
        }
      }

      try {
        const usersPayload = getArrayPayload(await fetchJson("/users"), "Users");
        if (!cancelled) {
          setUsers({ loading: false, error: "", data: usersPayload });
        }
      } catch (error) {
        if (!cancelled) {
          setUsers({ loading: false, error: error.message, data: [] });
        }
      }

      try {
        const roomsPayload = getArrayPayload(await fetchJson("/chat-rooms"), "Chat rooms");
        if (!cancelled) {
          setChatRooms({ loading: false, error: "", data: roomsPayload });
          setSelectedRoomId((current) => current ?? roomsPayload[0]?.id ?? null);
        }
      } catch (error) {
        if (!cancelled) {
          setChatRooms({ loading: false, error: error.message, data: [] });
        }
      }

      try {
        const presencePayload = getArrayPayload(await fetchJson("/presence"), "Presence");
        if (!cancelled) {
          setPresence({ loading: false, error: "", data: presencePayload });
        }
      } catch (error) {
        if (!cancelled) {
          setPresence({ loading: false, error: error.message, data: [] });
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!selectedRoomId) {
      setMessages({ loading: false, error: "", data: [] });
      return () => {
        cancelled = true;
      };
    }

    setMessages({ loading: true, error: "", data: [] });

    async function loadMessages() {
      try {
        const messagesPayload = getArrayPayload(
          await fetchJson(`/chat-rooms/${selectedRoomId}/messages`),
          "Messages"
        );

        if (!cancelled) {
          setMessages({ loading: false, error: "", data: messagesPayload });
        }
      } catch (error) {
        if (!cancelled) {
          setMessages({ loading: false, error: error.message, data: [] });
        }
      }
    }

    loadMessages();

    return () => {
      cancelled = true;
    };
  }, [selectedRoomId]);

  const usersList = users.data || [];
  const roomsList = chatRooms.data || [];
  const messagesList = messages.data || [];
  const presenceList = presence.data || [];
  const healthData = health.data;
  const dbHealthData = dbHealth.data;

  return (
    <div
      style={{
        minHeight: "100vh",
        padding: "32px",
        background: "#f4f7fb",
        color: "#111827",
        fontFamily: "Segoe UI, sans-serif",
      }}
    >
      <div style={{ maxWidth: "960px", margin: "0 auto" }}>
        <h1 style={{ marginBottom: "8px" }}>Chat Web Integration Check</h1>
        <p style={{ marginTop: 0, color: "#4b5563" }}>
          API Base URL: <code>{API_BASE_URL}</code>
        </p>

        <section style={sectionStyle}>
          <h2 style={{ marginTop: 0 }}>Service Status</h2>
          <p>
            Backend:{" "}
            <StatusBadge
              value={health.loading ? "loading" : health.error ? "error" : healthData?.status || "unknown"}
              okValue="ok"
            />
          </p>
          {health.error ? <p style={{ color: "#b91c1c" }}>{health.error}</p> : null}

          <p>
            Database:{" "}
            <StatusBadge
              value={
                dbHealth.loading
                  ? "loading"
                  : dbHealth.error
                    ? "error"
                    : dbHealthData?.database || dbHealthData?.status || "unknown"
              }
              okValue="connected"
            />
          </p>
          {dbHealth.error ? <p style={{ color: "#b91c1c" }}>{dbHealth.error}</p> : null}
        </section>

        <RequestPanel
          title={`Users (${usersList.length})`}
          state={users}
          successContent={
            usersList.length > 0 ? (
              <ul style={{ paddingLeft: "20px", marginBottom: 0 }}>
                {usersList.map((user) => (
                  <li key={user.id}>
                    #{user.id} {user.username} | {user.display_name} | {user.email} | provider: {user.auth_provider}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No users found.</p>
            )
          }
        />

        <RequestPanel
          title={`Chat Rooms (${roomsList.length})`}
          state={chatRooms}
          successContent={
            roomsList.length > 0 ? (
              <div>
                <label htmlFor="room-select" style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}>
                  Select a room to inspect messages
                </label>
                <select
                  id="room-select"
                  value={selectedRoomId ?? ""}
                  onChange={(event) => setSelectedRoomId(Number(event.target.value))}
                  style={{ minWidth: "240px", padding: "8px" }}
                >
                  {roomsList.map((room) => (
                    <option key={room.id} value={room.id}>
                      #{room.id} {room.name || "(unnamed room)"} [{room.room_type}]
                    </option>
                  ))}
                </select>

                <ul style={{ paddingLeft: "20px", marginTop: "16px", marginBottom: 0 }}>
                  {roomsList.map((room) => (
                    <li key={room.id}>
                      #{room.id} {room.name || "(unnamed room)"} | type: {room.room_type} | active:{" "}
                      {String(room.is_active)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p>No chat rooms found.</p>
            )
          }
        />

        <RequestPanel
          title={selectedRoomId ? `Messages in Room #${selectedRoomId}` : "Messages"}
          state={messages}
          successContent={
            messagesList.length > 0 ? (
              <ul style={{ paddingLeft: "20px", marginBottom: 0 }}>
                {messagesList.map((message) => (
                  <li key={message.id}>
                    [{message.sender_username}] {message.content}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No messages found for this room.</p>
            )
          }
        />

        <RequestPanel
          title={`Presence (${presenceList.length})`}
          state={presence}
          successContent={
            presenceList.length > 0 ? (
              <ul style={{ paddingLeft: "20px", marginBottom: 0 }}>
                {presenceList.map((item) => (
                  <li key={item.user_id}>
                    {item.username}: {item.status}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No presence data found.</p>
            )
          }
        />
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
