import { ref, onMounted, onUnmounted } from 'vue'

export function useMagnetic(elementRef, options = {}) {
  const { strength = 0.3, radius = 120 } = options
  const isHovered = ref(false)
  let animFrame = null

  function onMouseMove(e) {
    if (!elementRef.value) return
    const rect = elementRef.value.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const dx = e.clientX - centerX
    const dy = e.clientY - centerY
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist < radius) {
      isHovered.value = true
      cancelAnimationFrame(animFrame)
      animFrame = requestAnimationFrame(() => {
        const pull = 1 - dist / radius
        elementRef.value.style.transform = `translate(${dx * strength * pull}px, ${dy * strength * pull}px)`
      })
    } else if (isHovered.value) {
      reset()
    }
  }

  function reset() {
    isHovered.value = false
    if (elementRef.value) {
      elementRef.value.style.transition = 'transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)'
      elementRef.value.style.transform = 'translate(0, 0)'
      setTimeout(() => {
        if (elementRef.value) elementRef.value.style.transition = ''
      }, 500)
    }
  }

  onMounted(() => {
    window.addEventListener('mousemove', onMouseMove)
  })

  onUnmounted(() => {
    window.removeEventListener('mousemove', onMouseMove)
    cancelAnimationFrame(animFrame)
  })

  return { isHovered }
}
