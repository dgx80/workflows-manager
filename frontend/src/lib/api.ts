/**
 * REST API client for CICD Monitor.
 */

import type { Event, MonitorState } from "./types";

const API_URL = "http://localhost:8000/api";

export async function fetchEvents(limit?: number): Promise<Event[]> {
  const url = limit ? `${API_URL}/events?limit=${limit}` : `${API_URL}/events`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch events: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchState(): Promise<MonitorState> {
  const response = await fetch(`${API_URL}/state`);
  if (!response.ok) {
    throw new Error(`Failed to fetch state: ${response.statusText}`);
  }
  return response.json();
}

export async function postEvent(event: Omit<Event, "timestamp">): Promise<Event> {
  const response = await fetch(`${API_URL}/events`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(event),
  });
  if (!response.ok) {
    throw new Error(`Failed to post event: ${response.statusText}`);
  }
  return response.json();
}

export async function clearEvents(): Promise<void> {
  const response = await fetch(`${API_URL}/events`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to clear events: ${response.statusText}`);
  }
}
