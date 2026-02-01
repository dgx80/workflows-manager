/**
 * Event timeline component with auto-scroll.
 */

import { Component, For, createEffect, onMount } from "solid-js";
import { monitorStore } from "~/stores/monitorStore";
import { AGENTS, type AgentName, type Event } from "~/lib/types";

interface TimelineItemProps {
  event: Event;
}

const TimelineItem: Component<TimelineItemProps> = (props) => {
  const agentInfo = () => {
    const agentName = props.event.agent as AgentName;
    return AGENTS[agentName] || { icon: "❓", label: props.event.agent };
  };

  const timeStr = () => {
    const time = new Date(props.event.timestamp);
    return time.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  return (
    <div class="timeline-item">
      <span class="timeline-time">{timeStr()}</span>
      <span class={`timeline-agent agent-${props.event.agent}`}>
        {agentInfo().icon} {agentInfo().label}
      </span>
      <span classList={{ "timeline-action": true, [props.event.action]: true }}>
        {props.event.action}
      </span>
      {props.event.workflow && (
        <span class="timeline-workflow">→ {props.event.workflow}</span>
      )}
    </div>
  );
};

const Timeline: Component = () => {
  let containerRef: HTMLDivElement | undefined;

  // Auto-scroll to bottom when new events arrive
  createEffect(() => {
    const events = monitorStore.events;
    if (events.length > 0 && containerRef) {
      // Use setTimeout to ensure DOM has updated
      setTimeout(() => {
        containerRef!.scrollTop = containerRef!.scrollHeight;
      }, 0);
    }
  });

  // Show last 50 events
  const displayEvents = () => monitorStore.events.slice(-50);

  return (
    <div class="timeline-container">
      <div class="section-header">Event Timeline</div>
      <div id="timeline" ref={containerRef}>
        <For each={displayEvents()}>
          {(event) => <TimelineItem event={event} />}
        </For>
      </div>
    </div>
  );
};

export default Timeline;
