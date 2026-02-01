/**
 * Dashboard widgets: Active Agent, Workflow, Statistics.
 */

import { Component } from "solid-js";
import { monitorStore, duration } from "~/stores/monitorStore";
import { AGENTS, type AgentName } from "~/lib/types";

const AgentWidget: Component = () => {
  const agent = () => monitorStore.state.active_agent as AgentName | null;
  const agentInfo = () => (agent() ? AGENTS[agent()!] : null);

  return (
    <div
      id="agent-widget"
      class="widget"
      classList={{ active: !!agent() }}
    >
      <div class="widget-header">Active Agent</div>
      <div class="widget-content">
        <span class="agent-icon">{agentInfo()?.icon || "-"}</span>
        <span
          class="agent-name"
          classList={{ [`agent-${agent()}`]: !!agent() }}
        >
          {agentInfo()?.label || "None"}
        </span>
      </div>
    </div>
  );
};

const WorkflowWidget: Component = () => {
  return (
    <div class="widget">
      <div class="widget-header">Workflow</div>
      <div class="widget-content">
        {monitorStore.state.active_workflow || "-"}
      </div>
    </div>
  );
};

const DurationWidget: Component = () => {
  return (
    <div class="widget">
      <div class="widget-header">Duration</div>
      <div class="widget-content" id="duration">
        {duration()}
      </div>
    </div>
  );
};

const EventCountWidget: Component = () => {
  return (
    <div class="widget">
      <div class="widget-header">Events</div>
      <div class="widget-content" id="event-count">
        {monitorStore.events.length}
      </div>
    </div>
  );
};

const Widgets: Component = () => {
  return (
    <div class="widgets">
      <AgentWidget />
      <WorkflowWidget />
      <DurationWidget />
      <EventCountWidget />
    </div>
  );
};

export default Widgets;
export { AgentWidget, WorkflowWidget, DurationWidget, EventCountWidget };
