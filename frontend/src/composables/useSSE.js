import { ref, onUnmounted } from 'vue'

export function useSSE(url) {
  const data = ref(null)
  const error = ref(null)
  const connected = ref(false)
  let source = null
  const listeners = {}

  function connect() {
    if (source) close()

    try {
      source = new EventSource(url)

      source.onopen = () => {
        connected.value = true
        error.value = null
      }

      source.onerror = (e) => {
        connected.value = false
        error.value = 'SSE connection error'
      }

      source.onmessage = (event) => {
        try {
          data.value = JSON.parse(event.data)
        } catch {
          data.value = event.data
        }
      }
    } catch (e) {
      error.value = e.message
    }
  }

  function on(eventName, callback) {
    if (!source) return
    const handler = (event) => {
      try {
        callback(JSON.parse(event.data))
      } catch {
        callback(event.data)
      }
    }
    listeners[eventName] = handler
    source.addEventListener(eventName, handler)
  }

  function close() {
    if (source) {
      Object.entries(listeners).forEach(([name, handler]) => {
        source.removeEventListener(name, handler)
      })
      source.close()
      source = null
    }
    connected.value = false
  }

  onUnmounted(close)

  return { data, error, connected, connect, on, close }
}
