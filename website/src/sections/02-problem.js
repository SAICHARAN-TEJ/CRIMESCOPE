// sections/02-problem.js — Stat cards with counter animation + slide-in
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

function animateCounter(el, target, suffix, duration = 1.4) {
  const obj = { value: 0 }
  gsap.to(obj, {
    value: target,
    duration,
    ease: 'power2.out',
    onUpdate() {
      const v = typeof target === 'float' || String(target).includes('.')
        ? obj.value.toFixed(1)
        : Math.floor(obj.value)
      el.textContent = v + suffix
    },
  })
}

export function initProblem() {
  const section = document.getElementById('problem')
  if (!section) return

  // Section header stagger
  gsap.from('#problem .section-label, #problem .section-heading, #problem .problem-lead', {
    opacity: 0, y: 28, duration: 0.75, ease: 'power3.out', stagger: 0.12,
    scrollTrigger: { trigger: '#problem', start: 'top 78%' }
  })

  // Stat cards: slide in from right with left-bar reveal
  const cards = gsap.utils.toArray('.stat-card')
  cards.forEach((card, i) => {
    gsap.from(card, {
      opacity: 0, x: 32, duration: 0.7, ease: 'power3.out', delay: i * 0.1,
      scrollTrigger: { trigger: card, start: 'top 88%' }
    })
  })

  // Counter animation on stat numbers
  ScrollTrigger.create({
    trigger: '.stat-cards',
    start: 'top 82%',
    once: true,
    onEnter: () => {
      const statData = [
        { selector: '.stat-card:nth-child(1) .stat-number', value: 73, suffix: '%' },
        { selector: '.stat-card:nth-child(2) .stat-number', value: 4.2, suffix: '×' },
        { selector: '.stat-card:nth-child(3) .stat-number', value: 38, suffix: '%' },
      ]
      statData.forEach(({ selector, value, suffix }, i) => {
        const el = document.querySelector(selector)
        if (!el) return
        el.textContent = '0' + suffix
        gsap.delayedCall(i * 0.15, () => {
          const obj = { v: 0 }
          gsap.to(obj, {
            v: value,
            duration: 1.5,
            ease: 'power2.out',
            onUpdate() {
              el.textContent = (value % 1 !== 0 ? obj.v.toFixed(1) : Math.floor(obj.v)) + suffix
            },
          })
        })
      })
    }
  })
}
