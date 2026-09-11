import { ref, onMounted, onUnmounted } from 'vue'

export interface TypewriterOptions {
  speedMs?: number
  pauseBetweenLinesMs?: number
  loop?: boolean
  showCaret?: boolean
}

export function useTypewriter(lines: string[], options: TypewriterOptions = {}) {
  const {
    speedMs = 24, // 18-28ms per character
    pauseBetweenLinesMs = 1800,
    loop = true,
    showCaret = true,
  } = options

  const displayedText = ref('')
  const currentLineIndex = ref(0)
  const isPaused = ref(false)
  const caretVisible = ref(true)

  let charIndex = 0
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  let caretIntervalId: ReturnType<typeof setInterval> | null = null

  const prefersReducedMotion =
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false

  function typeNextChar() {
    if (prefersReducedMotion) {
      displayedText.value = lines[currentLineIndex.value] || ''
      return
    }

    if (isPaused.value) {
      timeoutId = setTimeout(typeNextChar, 100)
      return
    }

    const currentLine = lines[currentLineIndex.value] || ''

    if (charIndex < currentLine.length) {
      displayedText.value = currentLine.slice(0, charIndex + 1)
      charIndex++
      // slight natural variation between 18ms and 28ms
      const jitter = speedMs + (Math.random() * 8 - 4)
      timeoutId = setTimeout(typeNextChar, Math.max(16, jitter))
    } else {
      // Line complete, pause then advance
      if (currentLineIndex.value < lines.length - 1 || loop) {
        timeoutId = setTimeout(() => {
          if (!isPaused.value) {
            charIndex = 0
            currentLineIndex.value = (currentLineIndex.value + 1) % lines.length
            displayedText.value = ''
          }
          typeNextChar()
        }, pauseBetweenLinesMs)
      }
    }
  }

  function pause() {
    isPaused.value = true
  }

  function resume() {
    isPaused.value = false
  }

  onMounted(() => {
    if (prefersReducedMotion) {
      displayedText.value = lines[0] || ''
      return
    }

    typeNextChar()

    if (showCaret) {
      caretIntervalId = setInterval(() => {
        caretVisible.value = !caretVisible.value
      }, 530)
    }
  })

  onUnmounted(() => {
    if (timeoutId) clearTimeout(timeoutId)
    if (caretIntervalId) clearInterval(caretIntervalId)
  })

  return {
    displayedText,
    currentLineIndex,
    isPaused,
    caretVisible,
    pause,
    resume,
  }
}
