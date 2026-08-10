/**
 * CrimeScope — Backend API Client.
 * Thin wrappers over the REST endpoints with typed returns.
 */
import axios from 'axios'
import type { TokenResponse, PresignedURLResponse, JobResponse, UploadFile } from '@/types'

const http = axios.create({ baseURL: '/api/v1' })

// ── Auth ──────────────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>('/auth/token', { username, password })
  return data
}

// ── Upload ────────────────────────────────────────────────────────────────

export async function presign(
  token: string,
  filename: string,
  contentType: string
): Promise<PresignedURLResponse> {
  const { data } = await http.post<PresignedURLResponse>(
    '/upload/presign',
    { filename, content_type: contentType },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

export async function uploadFileDirect(
  presignedUrl: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<void> {
  await axios.put(presignedUrl, file, {
    headers: { 'Content-Type': file.type },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
    },
  })
}

// ── Analysis ──────────────────────────────────────────────────────────────

export async function startAnalysis(
  token: string,
  jobId: string,
  files: UploadFile[],
  question: string
): Promise<JobResponse> {
  const { data } = await http.post<JobResponse>(
    '/analysis/start',
    { job_id: jobId, files, question },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

export async function getJobStatus(token: string, jobId: string) {
  const { data } = await http.get(`/analysis/${jobId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

export async function healthCheck() {
  const { data } = await http.get('/healthz')
  return data
}

// ── Swarm Intelligence ───────────────────────────────────────────────────

export async function listPersonas(token: string) {
  const { data } = await http.get('/personas', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

export async function materializePersonas(token: string, jobId: string) {
  const { data } = await http.post(`/analysis/${jobId}/personas`, {}, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

export async function sendChat(token: string, jobId: string, message: string, personaId?: string) {
  const { data } = await http.post('/chat', 
    { job_id: jobId, message, persona_id: personaId }, 
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

export async function injectScenario(token: string, jobId: string, hypothesis: string) {
  const { data } = await http.post('/scenario',
    { job_id: jobId, hypothesis },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

export async function getScenarioResult(token: string, scenarioId: string) {
  const { data } = await http.get(`/scenario/${scenarioId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}
