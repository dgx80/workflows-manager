/**
 * SolidJS reactive store for CICD Monitor state.
 */

import { createSignal, createEffect, onCleanup } from "solid-js";
import { createStore, produce } from "solid-js/store";
import type { Event, MonitorState, WebSocketMessage } from "~/lib/types";
import { monitorWS } from "~/lib/websocket";

interface MonitorStore {
  events: Event[];
  state: MonitorState;
  connected: boolean;
}

const initialState: MonitorStore = {
  events: [],
  state: {
    active_agent: null,
    active_workflow: null,
    started_at: null,
    event_count: 0,
  },
  connected: false,
};

// Create the store
const [store, setStore] = createStore<MonitorStore>(initialState);

// Connection status signal (for reactivity in components)
const [connected, setConnected] = createSignal(false);

// Duration timer
const [duration, setDuration] = createSignal<string>("-");

function handleMessage(message: WebSocketMessage) {
  if (message.type === "init") {
    setStore(
      produce((s) => {
        s.events = message.events || [];
        if (message.state) {
          s.state = message.state;
        }
      })
    );
  } else if (message.type === "event" && message.event) {
    setStore(
      produce((s) => {
        s.events.push(message.event!);
        // Keep only last 1000 events
        if (s.events.length > 1000) {
          s.events = s.events.slice(-1000);
        }
        // Update state based on event
        updateStateFromEvent(s.state, message.event!);
      })
    );
  }
}

function updateStateFromEvent(state: MonitorState, event: Event) {
  if (event.action === "start") {
    state.active_agent = event.agent;
    state.active_workflow = event.workflow;
    state.started_at = event.timestamp;
  } else if (event.action === "end") {
    if (state.active_agent === event.agent) {
      state.active_agent = null;
      state.active_workflow = null;
      state.started_at = null;
    }
  }
  state.event_count = store.events.length + 1;
}

function handleConnection(isConnected: boolean) {
  setConnected(isConnected);
  setStore("connected", isConnected);
}

// Duration updater
let durationInterval: ReturnType<typeof setInterval> | null = null;

function startDurationUpdater() {
  if (durationInterval) return;

  durationInterval = setInterval(() => {
    const startedAt = store.state.started_at;
    if (startedAt) {
      const diff = Date.now() - new Date(startedAt).getTime();
      const seconds = Math.floor(diff / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);

      if (hours > 0) {
        setDuration(`${hours}h ${minutes % 60}m`);
      } else if (minutes > 0) {
        setDuration(`${minutes}m ${seconds % 60}s`);
      } else {
        setDuration(`${seconds}s`);
      }
    } else {
      setDuration("-");
    }
  }, 1000);
}

function stopDurationUpdater() {
  if (durationInterval) {
    clearInterval(durationInterval);
    durationInterval = null;
  }
}

// Initialize WebSocket connection and handlers
export function initializeMonitor() {
  const unsubMessage = monitorWS.onMessage(handleMessage);
  const unsubConnection = monitorWS.onConnection(handleConnection);

  monitorWS.connect();
  startDurationUpdater();

  // Cleanup function
  return () => {
    unsubMessage();
    unsubConnection();
    monitorWS.disconnect();
    stopDurationUpdater();
  };
}

// Reset store
export function resetMonitor() {
  setStore(initialState);
  setDuration("-");
}

// Exports
export { store as monitorStore, connected, duration };
