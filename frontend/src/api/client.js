import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    const msg = error.response?.data?.detail || error.message || 'Network error'
    console.error('[API]', msg)
    return Promise.reject(error)
  }
)

export default api
