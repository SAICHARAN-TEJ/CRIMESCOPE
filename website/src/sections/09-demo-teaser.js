// sections/09-demo-teaser.js — Redaction bar slide-off reveals
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initDemoTeaser() {
  const section = document.getElementById('demo-teaser')
  if (!section) return

  // Header
  gsap.from('#demo-teaser .section-label, #demo-teaser .section-heading, #demo-teaser .section-sub', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', stagger: 0.1,
    scrollTrigger: { trigger: '#demo-teaser', start: 'top 80%' }
  })

  // Demo case box slides in
  gsap.from('.demo-case', {
    opacity: 0, y: 40, duration: 0.8, ease: 'power3.out',
    scrollTrigger: { trigger: '.demo-case', start: 'top 85%' }
  })

  // Redaction bars slide off (scaleX: 1→0 from left)
  const bars = section.querySelectorAll('.redact-bar')
  ScrollTrigger.create({
    trigger: '.demo-case',
    start: 'top 80%',
    once: true,
    onEnter: () => {
      gsap.to(bars, {
        scaleX: 0,
        transformOrigin: 'left center',
        duration: 0.8,
        ease: 'power3.out',
        stagger: 0.08,
      })
    }
  })

  // Hypothesis rows fade in after redaction
  ScrollTrigger.create({
    trigger: '.demo-hypothesis',
    start: 'top 85%',
    once: true,
    onEnter: () => {
      gsap.to('.demo-hypothesis', { opacity: 1, duration: 0.5, ease: 'power2.out' })
      gsap.to('.hyp-row', {
        opacity: 1, y: 0,
        duration: 0.6, ease: 'power3.out', stagger: 0.08,
        delay: 0.3,
      })
    }
  })
}
