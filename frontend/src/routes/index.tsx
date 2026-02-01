import { clientOnly } from "@solidjs/start";

// Dashboard must be client-only because it uses WebSocket and vis.js
const Dashboard = clientOnly(() => import("~/components/Dashboard"));

export default function Home() {
  return <Dashboard />;
}
