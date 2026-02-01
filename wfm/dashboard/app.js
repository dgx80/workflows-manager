// CICD Monitor Dashboard

const AGENTS = {
    architect: { icon: '🏗️', label: 'Architect', color: '#f59e0b' },
    coder: { icon: '💻', label: 'Coder', color: '#3b82f6' },
    tester: { icon: '🧪', label: 'Tester', color: '#10b981' },
    analyst: { icon: '🔍', label: 'Analyst', color: '#8b5cf6' },
    pm: { icon: '📋', label: 'PM', color: '#ec4899' },
    cicd: { icon: '🔄', label: 'CI/CD', color: '#6366f1' },
    master: { icon: '👑', label: 'Master', color: '#f43f5e' },
    builder: { icon: '🔨', label: 'Builder', color: '#14b8a6' },
};

// State
let ws = null;
let network = null;
let events = [];
let activeAgent = null;
let startedAt = null;
let durationInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNetwork();
    connectWebSocket();
    startDurationUpdater();
});

// WebSocket connection
function connectWebSocket() {
    const wsPort = 8765;
    ws = new WebSocket(`ws://localhost:${wsPort}/ws`);

    ws.onopen = () => {
        updateConnectionStatus(true);
        console.log('Connected to monitor server');
    };

    ws.onclose = () => {
        updateConnectionStatus(false);
        console.log('Disconnected from monitor server');
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleMessage(data);
        } catch (e) {
            console.error('Failed to parse message:', e);
        }
    };
}

function handleMessage(data) {
    if (data.type === 'init') {
        // Initial state and events
        events = data.events || [];
        updateState(data.state);
        renderTimeline();
        renderLogs();
        updateNetwork();
    } else if (data.type === 'event') {
        // New event
        events.push(data.event);
        processEvent(data.event);
        addTimelineItem(data.event);
        addLogEntry(data.event);
        updateNetwork();
    }
}

function processEvent(event) {
    if (event.action === 'start') {
        activeAgent = event.agent;
        startedAt = new Date(event.timestamp);
        updateAgentWidget(event.agent, event.workflow);
    } else if (event.action === 'end') {
        if (activeAgent === event.agent) {
            activeAgent = null;
            startedAt = null;
            updateAgentWidget(null, null);
        }
    }
    updateEventCount();
}

function updateState(state) {
    if (state) {
        activeAgent = state.active_agent;
        startedAt = state.started_at ? new Date(state.started_at) : null;
        updateAgentWidget(state.active_agent, state.active_workflow);
    }
    updateEventCount();
}

// UI Updates
function updateConnectionStatus(connected) {
    const el = document.getElementById('connection-status');
    el.textContent = connected ? 'Connected' : 'Disconnected';
    el.className = 'status ' + (connected ? 'connected' : 'disconnected');
}

function updateAgentWidget(agent, workflow) {
    const widget = document.getElementById('agent-widget');
    const iconEl = document.getElementById('agent-icon');
    const nameEl = document.getElementById('agent-name');
    const workflowEl = document.getElementById('workflow-name');

    if (agent && AGENTS[agent]) {
        widget.classList.add('active');
        iconEl.textContent = AGENTS[agent].icon;
        nameEl.textContent = AGENTS[agent].label;
        nameEl.className = `agent-name agent-${agent}`;
    } else {
        widget.classList.remove('active');
        iconEl.textContent = '-';
        nameEl.textContent = 'None';
        nameEl.className = 'agent-name';
    }

    workflowEl.textContent = workflow || '-';
}

function updateEventCount() {
    document.getElementById('event-count').textContent = events.length;
}

function startDurationUpdater() {
    durationInterval = setInterval(() => {
        const el = document.getElementById('duration');
        if (startedAt) {
            const diff = Date.now() - startedAt.getTime();
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);

            if (hours > 0) {
                el.textContent = `${hours}h ${minutes % 60}m`;
            } else if (minutes > 0) {
                el.textContent = `${minutes}m ${seconds % 60}s`;
            } else {
                el.textContent = `${seconds}s`;
            }
        } else {
            el.textContent = '-';
        }
    }, 1000);
}

// Timeline
function renderTimeline() {
    const container = document.getElementById('timeline');
    container.innerHTML = '';
    events.slice(-50).forEach(event => addTimelineItem(event, false));
}

function addTimelineItem(event, scroll = true) {
    const container = document.getElementById('timeline');
    const item = document.createElement('div');
    item.className = 'timeline-item';

    const time = new Date(event.timestamp);
    const timeStr = time.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const agentInfo = AGENTS[event.agent] || { icon: '❓', label: event.agent };

    item.innerHTML = `
        <span class="timeline-time">${timeStr}</span>
        <span class="timeline-agent agent-${event.agent}">${agentInfo.icon} ${agentInfo.label}</span>
        <span class="timeline-action ${event.action}">${event.action}</span>
        ${event.workflow ? `<span class="timeline-workflow">→ ${event.workflow}</span>` : ''}
    `;

    container.appendChild(item);

    if (scroll) {
        item.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
}

// Logs
function renderLogs() {
    const container = document.getElementById('logs');
    container.innerHTML = '';
    events.slice(-100).forEach(event => addLogEntry(event, false));
}

function addLogEntry(event, scroll = true) {
    const container = document.getElementById('logs');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = JSON.stringify(event);
    container.appendChild(entry);

    if (scroll) {
        entry.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
}

// Network Graph
function initNetwork() {
    const container = document.getElementById('network');

    // Create nodes for all agents
    const nodes = new vis.DataSet(
        Object.entries(AGENTS).map(([id, agent], index) => ({
            id,
            label: `${agent.icon}\n${agent.label}`,
            color: {
                background: agent.color,
                border: agent.color,
                highlight: { background: agent.color, border: '#fff' },
            },
            font: { color: '#fff', size: 14 },
            shape: 'circle',
            size: 30,
        }))
    );

    // Create edges based on typical workflow
    const edges = new vis.DataSet([
        { from: 'master', to: 'architect', arrows: 'to' },
        { from: 'architect', to: 'coder', arrows: 'to' },
        { from: 'coder', to: 'tester', arrows: 'to' },
        { from: 'tester', to: 'cicd', arrows: 'to' },
        { from: 'architect', to: 'pm', arrows: 'to', dashes: true },
        { from: 'analyst', to: 'architect', arrows: 'to', dashes: true },
    ]);

    const options = {
        nodes: {
            borderWidth: 2,
            shadow: true,
        },
        edges: {
            color: { color: '#64748b', highlight: '#94a3b8' },
            width: 2,
            smooth: { type: 'curvedCW', roundness: 0.2 },
        },
        physics: {
            enabled: true,
            solver: 'forceAtlas2Based',
            forceAtlas2Based: {
                gravitationalConstant: -50,
                centralGravity: 0.01,
                springLength: 150,
                springConstant: 0.08,
            },
            stabilization: { iterations: 100 },
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
        },
    };

    network = new vis.Network(container, { nodes, edges }, options);
}

function updateNetwork() {
    if (!network) return;

    // Highlight active agent
    const nodes = network.body.data.nodes;
    nodes.forEach(node => {
        const agent = AGENTS[node.id];
        if (node.id === activeAgent) {
            nodes.update({
                id: node.id,
                borderWidth: 4,
                shadow: { enabled: true, color: '#4ade80', size: 20 },
            });
        } else {
            nodes.update({
                id: node.id,
                borderWidth: 2,
                shadow: { enabled: true, color: 'rgba(0,0,0,0.5)', size: 10 },
            });
        }
    });
}
