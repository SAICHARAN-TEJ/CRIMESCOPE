/**
 * casesStore — Persists all investigation sessions in localStorage.
 * Each submitted job is saved as a "Case" with metadata, evidence files,
 * graph snapshot, and final status.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface CaseFile {
  id: string           // job_id from backend
  caseRef: string      // short human ref e.g. CR-2025-0001
  createdAt: string    // ISO timestamp
  updatedAt: string
  status: 'queued' | 'processing' | 'completed' | 'partial' | 'failed'
  evidenceFiles: { name: string; size: number; type: string }[]
  nodeCount: number
  edgeCount: number
  processingTimeMs: number
  agentResults: Record<string, { status: string; entityCount: number; processingTimeMs: number }>
  summary?: string     // AI-generated summary from pipeline
}

const STORAGE_KEY = 'crimescope_cases_v1'
let caseCounter = 1

function loadFromStorage(): CaseFile[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as CaseFile[]
    // bump counter so new refs don't collide
    if (parsed.length > 0) {
      const maxNum = parsed
        .map(c => parseInt(c.caseRef.split('-').pop() || '0', 10))
        .reduce((a, b) => Math.max(a, b), 0)
      caseCounter = maxNum + 1
    }
    return parsed
  } catch { return [] }
}

function saveToStorage(cases: CaseFile[]) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cases)) } catch {}
}

function nextRef(): string {
  const year = new Date().getFullYear()
  return `CR-${year}-${String(caseCounter++).padStart(4, '0')}`
}

export const useCasesStore = defineStore('cases', () => {
  const cases = ref<CaseFile[]>(loadFromStorage())

  const sortedCases = computed(() =>
    [...cases.value].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
  )

  /** Called from UploadPanel when a job starts */
  function openCase(jobId: string, files: { name: string; size: number; type: string }[]): CaseFile {
    const c: CaseFile = {
      id: jobId,
      caseRef: nextRef(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'queued',
      evidenceFiles: files,
      nodeCount: 0,
      edgeCount: 0,
      processingTimeMs: 0,
      agentResults: {},
    }
    cases.value.unshift(c)
    saveToStorage(cases.value)
    return c
  }

  /** Called on every WS pipeline_complete event */
  function finalizeCase(
    jobId: string,
    update: Partial<Pick<CaseFile, 'status' | 'nodeCount' | 'edgeCount' | 'processingTimeMs' | 'agentResults' | 'summary'>>
  ) {
    const idx = cases.value.findIndex(c => c.id === jobId)
    if (idx === -1) return
    cases.value[idx] = { ...cases.value[idx], ...update, updatedAt: new Date().toISOString() }
    saveToStorage(cases.value)
  }

  /** Hydrate status during processing */
  function updateCaseStatus(jobId: string, status: CaseFile['status']) {
    const idx = cases.value.findIndex(c => c.id === jobId)
    if (idx !== -1) {
      cases.value[idx].status = status
      cases.value[idx].updatedAt = new Date().toISOString()
      saveToStorage(cases.value)
    }
  }

  function deleteCase(id: string) {
    cases.value = cases.value.filter(c => c.id !== id)
    saveToStorage(cases.value)
  }

  function clearAll() {
    cases.value = []
    localStorage.removeItem(STORAGE_KEY)
    caseCounter = 1
  }

  function getCase(id: string) {
    return cases.value.find(c => c.id === id)
  }

  return { cases, sortedCases, openCase, finalizeCase, updateCaseStatus, deleteCase, clearAll, getCase }
})
