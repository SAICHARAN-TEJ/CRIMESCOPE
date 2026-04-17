// lib/api.ts — CRIMESCOPE Backend API client
const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5001';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path}: ${res.status} — ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Graph / Project ───────────────────────────────────────────
export async function createProject(name: string, simulationRequirement: string) {
  return request('/api/graph/project/create', {
    method: 'POST',
    body: JSON.stringify({ name, simulation_requirement: simulationRequirement }),
  });
}

export async function uploadFiles(projectId: string, files: File[]) {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  const res = await fetch(`${BACKEND}/api/graph/upload/${projectId}`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function generateOntology(projectId: string, simulationRequirement: string) {
  return request('/api/graph/ontology/generate', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, simulation_requirement: simulationRequirement }),
  });
}

export async function buildGraph(projectId: string) {
  return request('/api/graph/build', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId }),
  });
}

export async function getBuildStatus(taskId: string) {
  return request(`/api/graph/build/status?task_id=${taskId}`);
}

export async function getGraphData(projectId: string) {
  return request(`/api/graph/get/${projectId}`);
}

export async function listProjects() {
  return request('/api/graph/projects');
}

// ── Simulation ────────────────────────────────────────────────
export async function createSimulation(projectId: string, graphId: string) {
  return request('/api/simulation/create', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, graph_id: graphId }),
  });
}

export async function prepareSimulation(simulationId: string) {
  return request('/api/simulation/prepare', {
    method: 'POST',
    body: JSON.stringify({ simulation_id: simulationId }),
  });
}

export async function getSimulationStatus(simulationId: string) {
  return request(`/api/simulation/status/${simulationId}`);
}

export async function runSimulation(simulationId: string) {
  return request(`/api/simulation/run/${simulationId}`, { method: 'POST', body: '{}' });
}

export async function stopSimulation(simulationId: string) {
  return request(`/api/simulation/stop/${simulationId}`, { method: 'POST', body: '{}' });
}

export async function injectVariable(simulationId: string, variable: string, value: unknown, description = '') {
  return request(`/api/simulation/inject/${simulationId}`, {
    method: 'POST',
    body: JSON.stringify({ variable, value, description }),
  });
}

export async function getSimulationActions(simulationId: string, limit = 100, offset = 0, filter?: { agentRole?: string; severity?: string }) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset), ...filter });
  return request(`/api/simulation/actions/${simulationId}?${params}`);
}

// ── Reports ───────────────────────────────────────────────────
export async function generateReport(simulationId: string) {
  return request('/api/report/generate', {
    method: 'POST',
    body: JSON.stringify({ simulation_id: simulationId }),
  });
}

export async function getReport(simulationId: string) {
  return request(`/api/report/get/${simulationId}`);
}

export async function getReportStatus(taskId: string, simulationId?: string) {
  return request('/api/report/generate/status', {
    method: 'POST',
    body: JSON.stringify({ task_id: taskId, simulation_id: simulationId }),
  });
}

export async function chatWithReport(simulationId: string, message: string, history: Array<{ role: string; content: string }>) {
  return request('/api/report/chat', {
    method: 'POST',
    body: JSON.stringify({ simulation_id: simulationId, message, history }),
  });
}

export async function interviewAgents(reportId: string, agentIds: string[], question: string) {
  return request('/api/report/interview', {
    method: 'POST',
    body: JSON.stringify({ report_id: reportId, agent_ids: agentIds, question }),
  });
}
