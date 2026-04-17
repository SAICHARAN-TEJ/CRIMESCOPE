// sections/03-how-it-works.js — ScrollTrigger pinned timeline + DrawSVG line
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initHowItWorks() {
  const section = document.getElementById('how-it-works')
  if (!section) return

  // Animate header
  gsap.from('#how-it-works .section-label', {
    opacity: 0, y: 20, duration: 0.6, ease: 'power3.out',
    scrollTrigger: { trigger: '#how-it-works', start: 'top 80%' }
  })
  gsap.from('#how-it-works .section-heading', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', delay: 0.1,
    scrollTrigger: { trigger: '#how-it-works', start: 'top 80%' }
  })
  gsap.from('#how-it-works .section-sub', {
    opacity: 0, y: 20, duration: 0.6, ease: 'power3.out', delay: 0.2,
    scrollTrigger: { trigger: '#how-it-works', start: 'top 80%' }
  })

  // DrawSVG connecting line
  const line = section.querySelector('.timeline-line-svg line')
  if (line) {
    gsap.to(line, {
      strokeDashoffset: 0,
      duration: 2,
      ease: 'power2.inOut',
      scrollTrigger: {
        trigger: '.timeline',
        start: 'top 75%',
        end: 'bottom 30%',
        scrub: 1,
      }
    })
  }

  // Stagger timeline items
  const items = gsap.utils.toArray('.timeline-item')
  items.forEach((item, i) => {
    gsap.to(item, {
      opacity: 1, y: 0,
      duration: 0.7,
      ease: 'power3.out',
      delay: i * 0.08,
      scrollTrigger: { trigger: item, start: 'top 85%' }
    })
  })
}
