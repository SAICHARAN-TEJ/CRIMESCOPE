// sections/01-hero.js
// SplitText char-by-char on headline + 1,000-agent canvas particle field via GSAP ticker
import { gsap } from 'gsap'

/* ── Canvas particle field ── */
function initParticleField() {
  const canvas = document.getElementById('hero-canvas')
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  function resize() {
    canvas.width  = canvas.parentElement.offsetWidth
    canvas.height = canvas.parentElement.offsetHeight
  }
  resize()
  window.addEventListener('resize', resize)

  const NUM = 1000
  const particles = Array.from({ length: NUM }, () => ({
    x:    Math.random() * canvas.width,
    y:    Math.random() * canvas.height,
    vx:   (Math.random() - 0.5) * 0.6,
    vy:   (Math.random() - 0.5) * 0.6,
    r:    Math.random() * 1.5 + 0.4,
    alpha: Math.random() * 0.5 + 0.1,
    // red or blue
    col:  Math.random() < 0.6 ? '192,57,43' : '26,107,138',
  }))

  // Mouse influence
  let mx = canvas.width / 2, my = canvas.height / 2
  window.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY })

  // GSAP ticker (stays in sync with GSAP's RAF)
  gsap.ticker.add(() => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const W = canvas.width, H = canvas.height

    particles.forEach(p => {
      // Gentle mouse attraction
      const dx = mx - p.x, dy = my - p.y
      const dist = Math.hypot(dx, dy)
      if (dist < 200) {
        p.vx += (dx / dist) * 0.015
        p.vy += (dy / dist) * 0.015
      }

      // clamp speed
      const speed = Math.hypot(p.vx, p.vy)
      if (speed > 1.2) { p.vx = (p.vx / speed) * 1.2; p.vy = (p.vy / speed) * 1.2 }

      p.x += p.vx; p.y += p.vy
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${p.col},${p.alpha})`
      ctx.fill()
    })

    // Draw edges between nearby particles
    for (let i = 0; i < particles.length; i += 5) {
      for (let j = i + 5; j < particles.length; j += 5) {
        const dx = particles[i].x - particles[j].x
        const dy = particles[i].y - particles[j].y
        const d  = Math.hypot(dx, dy)
        if (d < 60) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(192,57,43,${(1 - d / 60) * 0.06})`
          ctx.lineWidth = 0.4
          ctx.moveTo(particles[i].x, particles[i].y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.stroke()
        }
      }
    }
  })
}

/* ── Hero entrance ── */
export function initHero() {
  initParticleField()

  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

  // Eyebrow
  tl.to('.hero-eyebrow', { opacity: 1, y: 0, duration: 0.6 }, 0.3)

  // SplitText on H1
  const h1 = document.querySelector('.hero-h1')
  if (h1 && window.SplitText) {
    const split = new SplitText(h1, { type: 'chars' })
    tl.from(split.chars, {
      opacity: 0,
      y: 60,
      rotationX: -30,
      duration: 0.8,
      stagger: 0.025,
      ease: 'power3.out',
    }, 0.5)
  } else if (h1) {
    // Fallback without SplitText (GSAP free plan)
    tl.from(h1, { opacity: 0, y: 40, duration: 0.9 }, 0.5)
  }

  // Sub-headline
  tl.to('.hero-sub', { opacity: 1, y: 0, duration: 0.7 }, '-=0.3')

  // CTAs
  tl.to('.hero-actions', { opacity: 1, duration: 0.5 }, '-=0.4')
  tl.from('.hero-actions .btn', { scale: 0.88, opacity: 0, stagger: 0.08, duration: 0.5, ease: 'back.out(1.7)' }, '-=0.4')

  // Badge + scroll hint
  tl.to('.hero-badge', { opacity: 1, duration: 0.5 }, '-=0.2')
  tl.to('.hero-scroll-hint', { opacity: 1, duration: 0.5 }, '-=0.3')
}
