import { onMounted, onUnmounted, ref, type Ref } from 'vue'

export function useReveal(containerRef?: Ref<HTMLElement | null>) {
  const observer = ref<IntersectionObserver | null>(null)

  onMounted(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      // Immediately reveal all elements
      const targets = containerRef?.value
        ? containerRef.value.querySelectorAll('.reveal-init')
        : document.querySelectorAll('.reveal-init')
      targets.forEach((el) => el.classList.add('reveal-visible'))
      return
    }

    observer.value = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target as HTMLElement
            const delay = el.dataset.revealDelay ? parseInt(el.dataset.revealDelay, 10) : 0
            if (delay > 0) {
              setTimeout(() => {
                el.classList.add('reveal-visible')
              }, delay)
            } else {
              el.classList.add('reveal-visible')
            }
            observer.value?.unobserve(el)
          }
        })
      },
      {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px',
      }
    )

    const targets = containerRef?.value
      ? containerRef.value.querySelectorAll('.reveal-init')
      : document.querySelectorAll('.reveal-init')

    targets.forEach((el, i) => {
      if (!el.getAttribute('data-reveal-delay')) {
        el.setAttribute('data-reveal-delay', String(i * 90))
      }
      observer.value?.observe(el)
    })
  })

  onUnmounted(() => {
    observer.value?.disconnect()
    observer.value = null
  })

  return {
    observer,
  }
}
