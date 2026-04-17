// sections/02-problem.js — Stagger stat cards + DrawSVG border reveals
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initProblem() {
  const section = document.getElementById('problem')
  if (!section) return

  // Animate header
  gsap.from('#problem .section-label', {
    opacity: 0, y: 20, duration: 0.6, ease: 'power3.out',
    scrollTrigger: { trigger: '#problem', start: 'top 80%' }
  })
  gsap.from('#problem .section-heading', {
    opacity: 0, y: 30, duration: 0.8, ease: 'power3.out', delay: 0.1,
    scrollTrigger: { trigger: '#problem', start: 'top 80%' }
  })
  gsap.from('#problem .problem-lead', {
    opacity: 0, y: 20, duration: 0.7, ease: 'power3.out', delay: 0.2,
    scrollTrigger: { trigger: '#problem', start: 'top 80%' }
  })

  // Stagger stat cards in with DrawSVG border reveals
  const cards = gsap.utils.toArray('.stat-card')
  cards.forEach((card, i) => {
    const rect = card.querySelector('rect')

    const tl = gsap.timeline({
      scrollTrigger: { trigger: card, start: 'top 85%' }
    })

    // Fade/slide card
    tl.from(card, {
      opacity: 0, y: 30, duration: 0.7, ease: 'power3.out',
      delay: i * 0.08
    })

    // DrawSVG border reveal
    if (rect) {
      tl.to(rect, {
        strokeDashoffset: 0,
        duration: 1.0,
        ease: 'power2.inOut',
      }, '-=0.4')
    }
  })
}
