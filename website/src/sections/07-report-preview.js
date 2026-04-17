// sections/07-report-preview.js — Probability bars animate 0→value on enter
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initReportPreview() {
  const section = document.getElementById('report-preview')
  if (!section) return

  // Header
  gsap.from('#report-preview .section-label, #report-preview .section-heading, #report-preview .section-sub', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', stagger: 0.1,
    scrollTrigger: { trigger: '#report-preview', start: 'top 80%' }
  })

  // Animate mock UI in
  gsap.from('.report-mock', {
    opacity: 0, x: -40, duration: 0.8, ease: 'power3.out',
    scrollTrigger: { trigger: '.report-wrap', start: 'top 80%' }
  })

  // Probability bars: fill from 0 to target value
  const bars = section.querySelectorAll('.prob-bar-fill')
  ScrollTrigger.create({
    trigger: '.prob-list',
    start: 'top 85%',
    once: true,
    onEnter: () => {
      bars.forEach((bar, i) => {
        const target = parseFloat(bar.getAttribute('data-pct') || 0)
        gsap.to(bar, {
          width: target + '%',
          duration: 1.2,
          ease: 'power3.out',
          delay: i * 0.08,
        })
      })
    }
  })

  // Stagger right-side report features
  gsap.to('.report-feature', {
    opacity: 1, x: 0,
    duration: 0.7,
    ease: 'power3.out',
    stagger: 0.08,
    scrollTrigger: { trigger: '.report-features', start: 'top 80%' }
  })
}
