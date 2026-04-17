// sections/08-target-users.js — 2×2 stagger grid
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initTargetUsers() {
  const section = document.getElementById('target-users')
  if (!section) return

  // Header
  gsap.from('#target-users .section-label, #target-users .section-heading, #target-users .section-sub', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', stagger: 0.1,
    scrollTrigger: { trigger: '#target-users', start: 'top 80%' }
  })

  // 2×2 stagger
  const cards = gsap.utils.toArray('.user-card')
  gsap.to(cards, {
    opacity: 1, y: 0,
    duration: 0.7,
    ease: 'power3.out',
    stagger: { each: 0.08, from: 'start' },
    scrollTrigger: { trigger: '.users-grid', start: 'top 80%' }
  })
}
