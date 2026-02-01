/**
 * Main dashboard layout component.
 */

import { Component, onMount, onCleanup } from "solid-js";
import { initializeMonitor } from "~/stores/monitorStore";
import ConnectionStatus from "./ConnectionStatus";
import Widgets from "./Widgets";
import Timeline from "./Timeline";
import Logs from "./Logs";
import Graph from "./Graph";

const Dashboard: Component = () => {
  onMount(() => {
    const cleanup = initializeMonitor();
    onCleanup(cleanup);
  });

  return (
    <>
      <header>
        <h1>CICD Monitor</h1>
        <ConnectionStatus />
      </header>

      <main>
        <div class="left-panel">
          <Graph />
        </div>

        <div class="right-panel">
          <Widgets />
          <Timeline />
        </div>
      </main>

      <Logs />
    </>
  );
};

export default Dashboard;
