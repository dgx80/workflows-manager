/**
 * Raw JSON logs component for debugging.
 */

import { Component, For, createEffect } from "solid-js";
import { monitorStore } from "~/stores/monitorStore";
import type { Event } from "~/lib/types";

const Logs: Component = () => {
  let containerRef: HTMLDivElement | undefined;

  // Auto-scroll to bottom when new events arrive
  createEffect(() => {
    const events = monitorStore.events;
    if (events.length > 0 && containerRef) {
      setTimeout(() => {
        containerRef!.scrollTop = containerRef!.scrollHeight;
      }, 0);
    }
  });

  // Show last 100 events
  const displayEvents = () => monitorStore.events.slice(-100);

  return (
    <footer>
      <div class="section-header">Raw Logs</div>
      <div id="logs" ref={containerRef}>
        <For each={displayEvents()}>
          {(event) => (
            <div class="log-entry">{JSON.stringify(event)}</div>
          )}
        </For>
      </div>
    </footer>
  );
};

export default Logs;
