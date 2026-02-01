/**
 * Network graph component using vis.js with SolidJS.
 */

import { Component, onMount, onCleanup, createEffect } from "solid-js";
import { monitorStore } from "~/stores/monitorStore";
import { AGENTS, type AgentName } from "~/lib/types";

// Import vis-network dynamically to avoid SSR issues
let Network: typeof import("vis-network").Network;
let DataSet: typeof import("vis-data").DataSet;

const Graph: Component = () => {
  let containerRef: HTMLDivElement | undefined;
  let network: InstanceType<typeof Network> | null = null;
  let nodesDataSet: InstanceType<typeof DataSet> | null = null;
  let previousActiveAgent: string | null = null;

  onMount(async () => {
    // Dynamic import for client-side only
    const visNetwork = await import("vis-network");
    const visData = await import("vis-data");
    Network = visNetwork.Network;
    DataSet = visData.DataSet;

    initNetwork();
  });

  onCleanup(() => {
    if (network) {
      network.destroy();
      network = null;
    }
  });

  // React to active agent changes
  createEffect(() => {
    const activeAgent = monitorStore.state.active_agent;
    if (network && nodesDataSet) {
      updateNetworkHighlight(activeAgent);
    }
  });

  function initNetwork() {
    if (!containerRef || !Network || !DataSet) return;

    // Create nodes for all agents
    nodesDataSet = new DataSet(
      Object.entries(AGENTS).map(([id, agent]) => ({
        id,
        label: `${agent.icon}\n${agent.label}`,
        color: {
          background: agent.color,
          border: agent.color,
          highlight: { background: agent.color, border: "#fff" },
        },
        font: { color: "#fff", size: 14 },
        shape: "circle",
        size: 30,
        borderWidth: 2,
        shadow: { enabled: true, color: "rgba(0,0,0,0.5)", size: 10 },
      }))
    );

    // Create edges based on typical workflow
    const edges = new DataSet([
      { from: "master", to: "architect", arrows: "to" },
      { from: "architect", to: "coder", arrows: "to" },
      { from: "coder", to: "tester", arrows: "to" },
      { from: "tester", to: "cicd", arrows: "to" },
      { from: "architect", to: "pm", arrows: "to", dashes: true },
      { from: "analyst", to: "architect", arrows: "to", dashes: true },
    ]);

    const options = {
      nodes: {
        borderWidth: 2,
      },
      edges: {
        color: { color: "#64748b", highlight: "#94a3b8" },
        width: 2,
        smooth: { type: "curvedCW", roundness: 0.2 },
      },
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 150,
          springConstant: 0.08,
        },
        stabilization: { iterations: 50 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
      },
    };

    network = new Network(
      containerRef,
      { nodes: nodesDataSet, edges },
      options
    );

    // Disable physics after stabilization to prevent CPU usage
    network.on("stabilizationIterationsDone", () => {
      network?.setOptions({ physics: { enabled: false } });
    });

    // Handle window resize
    const handleResize = debounce(() => {
      network?.fit();
    }, 250);

    window.addEventListener("resize", handleResize);

    onCleanup(() => {
      window.removeEventListener("resize", handleResize);
    });
  }

  function updateNetworkHighlight(activeAgent: string | null) {
    if (!nodesDataSet) return;

    // Only update nodes that changed
    if (previousActiveAgent === activeAgent) return;

    const updates: Array<{ id: string; borderWidth: number; shadow: { enabled: boolean; color: string; size: number } }> = [];

    // Reset previous active agent
    if (previousActiveAgent && AGENTS[previousActiveAgent as AgentName]) {
      updates.push({
        id: previousActiveAgent,
        borderWidth: 2,
        shadow: { enabled: true, color: "rgba(0,0,0,0.5)", size: 10 },
      });
    }

    // Highlight new active agent
    if (activeAgent && AGENTS[activeAgent as AgentName]) {
      updates.push({
        id: activeAgent,
        borderWidth: 4,
        shadow: { enabled: true, color: "#4ade80", size: 20 },
      });
    }

    if (updates.length > 0) {
      nodesDataSet.update(updates);
    }

    previousActiveAgent = activeAgent;
  }

  return (
    <div id="graph-container">
      <div id="network" ref={containerRef} />
    </div>
  );
};

// Debounce helper
function debounce<T extends (...args: Parameters<T>) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export default Graph;
