// sections/06-archetypes.js — GSAP horizontal scroll carousel
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initArchetypes() {
  const track = document.querySelector('.archetype-track')
  const wrap  = document.querySelector('.archetype-track-wrap')
  if (!track || !wrap) return

  // Header
  gsap.from('#archetypes .section-label, #archetypes .section-heading, #archetypes .section-sub', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', stagger: 0.1,
    scrollTrigger: { trigger: '#archetypes', start: 'top 80%' }
  })

  // Stagger cards in
  const cards = gsap.utils.toArray('.archetype-card')
  gsap.to(cards, {
    opacity: 1,
    duration: 0.6, ease: 'power3.out', stagger: 0.08,
    scrollTrigger: { trigger: '.archetype-track', start: 'top 85%' }
  })

  // GSAP horizontal scroll (drag)
  let isDragging = false, startX = 0, scrollLeft = 0

  wrap.addEventListener('mousedown', (e) => {
    isDragging = true
    startX = e.pageX - wrap.offsetLeft
    scrollLeft = wrap.scrollLeft
    wrap.style.userSelect = 'none'
  })
  wrap.addEventListener('mouseleave', () => isDragging = false)
  wrap.addEventListener('mouseup', () => { isDragging = false; wrap.style.userSelect = '' })
  wrap.addEventListener('mousemove', (e) => {
    if (!isDragging) return
    const x    = e.pageX - wrap.offsetLeft
    const walk = (x - startX) * 1.5
    wrap.scrollLeft = scrollLeft - walk
  })

  // Touch support
  let touchStart = 0
  wrap.addEventListener('touchstart', (e) => { touchStart = e.touches[0].pageX; scrollLeft = wrap.scrollLeft })
  wrap.addEventListener('touchmove', (e) => {
    const dx = e.touches[0].pageX - touchStart
    wrap.scrollLeft = scrollLeft - dx * 1.2
  })

  // Auto-animate on enter
  ScrollTrigger.create({
    trigger: '#archetypes',
    start: 'top 80%',
    once: true,
    onEnter: () => {
      gsap.to(wrap, {
        scrollLeft: wrap.scrollWidth * 0.3,
        duration: 4,
        ease: 'power2.inOut',
      })
    }
  })
}
