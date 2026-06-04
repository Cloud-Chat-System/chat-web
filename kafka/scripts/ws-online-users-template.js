/**
 * Draft template for simulating a large number of online users.
 * Replace the placeholder logic with the team's chosen load tool flow.
 */

export const config = {
  targetOnlineUsers: Number(process.env.KAFKA_TARGET_ONLINE_USERS || 100000),
  websocketUrl: process.env.WS_URL || "",
  rampUpSeconds: 600,
  holdSeconds: 900,
}

export function describeScenario() {
  return {
    name: "online-user-soak-template",
    ...config,
    note: "This is a template only. Set WS_URL and pick k6, Locust, Gatling, or a custom runner before real execution.",
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log(JSON.stringify(describeScenario(), null, 2))
}
