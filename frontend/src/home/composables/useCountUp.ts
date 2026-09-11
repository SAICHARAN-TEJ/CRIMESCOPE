import { ref, onMounted, onUnmounted, type Ref } from 'vue'

function easeOutEditorial(t: number): number {
  // Approximation of cubic-bezier(0.22, 1, 0.36, 1)
  const c1 = 1 - t
  return 1 - Math.pow(c1, 3.5)
}

export function useCountUp(
  target: number,
  durationMs = 900,
  triggerElRef?: Ref<HTMLElement | null>
) {
  const displayValue = ref(0)
  let animationFrameId: number | null = null
  let observer: IntersectionObserver | null = null
  let hasStarted = false

  function startCount() {
    if (hasStarted) return
    hasStarted = true

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      displayValue.value = target
      return
    }

    const startTime = performance.now()

    function step(currentTime: number) {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / durationMs, 1)
      const easedProgress = easeOutEditorial(progress)

      displayValue.value = Math.round(easedProgress * target)

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(step)
      } else {
        displayValue.value = target
      }
    }

    animationFrameId = requestAnimationFrame(step)
  }

  onMounted(() => {
    if (triggerElRef?.value && typeof IntersectionObserver !== 'undefined') {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            startCount()
            observer?.disconnect()
            observer = null
          }
        },
        { threshold: 0.15 }
      )
      observer.observe(triggerElRef.value)
    } else {
      startCount()
    }
  })

  onUnmounted(() => {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
    observer?.disconnect()
    observer = null
  })

  return {
    displayValue,
    startCount,
  }
}
