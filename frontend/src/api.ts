/**
 * CrimeScope — Backend API Client.
 * Thin wrappers over the REST endpoints with typed returns.
 */
import axios from 'axios'
import { API_BASE_URL } from '@/config'
import type {
  TokenResponse,
  PresignedURLResponse,
  JobResponse,
  UploadFile,
  ChatResponse,
  PersonaMaterializeResponse,
} from '@/types'

const http = axios.create({ baseURL: API_BASE_URL })

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

/**
 * Re-run a failed pipeline. POST /analysis/{job_id}/retry takes NO body;
 * valid only when the job status is 'failed' (backend replies 409 otherwise).
 */
export async function retryAnalysis(token: string, jobId: string): Promise<JobResponse> {
  const { data } = await http.post<JobResponse>(
    `/analysis/${jobId}/retry`,
    undefined,
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

// ── Swarm Intelligence ───────────────────────────────────────────────────

/** POST /analysis/{job_id}/personas — materialize graph-entity personas. */
export async function materializePersonas(
  token: string,
  jobId: string
): Promise<PersonaMaterializeResponse> {
  const { data } = await http.post<PersonaMaterializeResponse>(
    `/analysis/${jobId}/personas`,
    {},
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

/** POST /chat — ask the ReportAgent (or a persona) a question. */
export async function sendChat(
  token: string,
  jobId: string,
  message: string,
  opts?: { conversationId?: string; personaId?: string }
): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>(
    '/chat',
    {
      job_id: jobId,
      message,
      conversation_id: opts?.conversationId ?? undefined,
      persona_id: opts?.personaId ?? undefined,
    },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}

/** POST /scenario — inject a "what if" hypothesis for evaluation. */
export async function injectScenario(token: string, jobId: string, hypothesis: string) {
  const { data } = await http.post('/scenario',
    { job_id: jobId, hypothesis },
    { headers: { Authorization: `Bearer ${token}` } }
  )
  return data
}
