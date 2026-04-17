// sections/nav.js — Nav becomes opaque/red-border on scroll
import { gsap } from 'gsap'

export function initNav() {
  const nav = document.getElementById('cs-nav')
  if (!nav) return

  ScrollTrigger.create({
    start: 'top -80',
    onEnter: () => nav.classList.add('scrolled'),
    onLeaveBack: () => nav.classList.remove('scrolled'),
  })
}
