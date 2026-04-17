// sections/04-three-modes.js — Stagger feature cards + GSAP hover states
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initThreeModes() {
  const section = document.getElementById('three-modes')
  if (!section) return

  // Header
  gsap.from('#three-modes .section-label', {
    opacity: 0, y: 20, duration: 0.6, ease: 'power3.out',
    scrollTrigger: { trigger: '#three-modes', start: 'top 80%' }
  })
  gsap.from('#three-modes .section-heading', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', delay: 0.1,
    scrollTrigger: { trigger: '#three-modes', start: 'top 80%' }
  })

  // Stagger cards
  const cards = gsap.utils.toArray('.mode-card')
  gsap.to(cards, {
    opacity: 1, y: 0,
    duration: 0.7,
    ease: 'power3.out',
    stagger: 0.08,
    scrollTrigger: { trigger: '.modes-grid', start: 'top 80%' }
  })

  // GSAP hover states (scale + slight lift)
  cards.forEach(card => {
    const enterTl = gsap.timeline({ paused: true })
    enterTl.to(card, { y: -6, duration: 0.35, ease: 'power2.inOut' })

    card.addEventListener('mouseenter', () => enterTl.play())
    card.addEventListener('mouseleave', () => enterTl.reverse())
  })
}
