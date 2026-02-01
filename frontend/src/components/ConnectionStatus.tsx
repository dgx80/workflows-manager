/**
 * Connection status indicator component.
 */

import { Component } from "solid-js";
import { connected } from "~/stores/monitorStore";

const ConnectionStatus: Component = () => {
  return (
    <div
      class="status"
      classList={{
        connected: connected(),
        disconnected: !connected(),
      }}
    >
      {connected() ? "Connected" : "Disconnected"}
    </div>
  );
};

export default ConnectionStatus;
