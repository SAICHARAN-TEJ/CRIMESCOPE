import { ref, onMounted, onUnmounted, type Ref } from 'vue'

export function useStickyStage(panelRefs: Ref<(HTMLElement | null)[]>) {
  const activeStageIndex = ref(0)
  let observer: IntersectionObserver | null = null

  onMounted(() => {
    if (typeof IntersectionObserver === 'undefined') return

    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const index = Number(entry.target.getAttribute('data-stage-index'))
            if (!isNaN(index)) {
              activeStageIndex.value = index
            }
          }
        })
      },
      {
        threshold: 0.6,
        rootMargin: '-10% 0px -20% 0px',
      }
    )

    panelRefs.value.forEach((el, idx) => {
      if (el) {
        el.setAttribute('data-stage-index', String(idx))
        observer?.observe(el)
      }
    })
  })

  onUnmounted(() => {
    observer?.disconnect()
    observer = null
  })

  function selectStage(index: number) {
    activeStageIndex.value = index
    const target = panelRefs.value[index]
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  return {
    activeStageIndex,
    selectStage,
  }
}
