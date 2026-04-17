// sections/01-hero.js
// Enhanced particle field + hero entrance with chip animations
import { gsap } from 'gsap'

/* ── Canvas particle field — amber/steel swarm ── */
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

  const NUM = 900
  const particles = Array.from({ length: NUM }, () => {
    const type = Math.random()
    return {
      x:     Math.random() * canvas.width,
      y:     Math.random() * canvas.height,
      vx:    (Math.random() - 0.5) * 0.7,
      vy:    (Math.random() - 0.5) * 0.7,
      r:     Math.random() * 1.6 + 0.3,
      alpha: Math.random() * 0.55 + 0.08,
      // 60% amber agents, 30% steel agents, 10% white evidence nodes
      col:   type < 0.60 ? '245,166,35' : type < 0.90 ? '46,170,240' : '220,230,245',
    }
  })

  let mx = canvas.width / 2, my = canvas.height / 2
  window.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY })

  gsap.ticker.add(() => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const W = canvas.width, H = canvas.height

    particles.forEach(p => {
      const dx = mx - p.x, dy = my - p.y
      const dist = Math.hypot(dx, dy)
      // Subtle mouse attraction
      if (dist < 180 && dist > 20) {
        p.vx += (dx / dist) * 0.012
        p.vy += (dy / dist) * 0.012
      }
      // Repel from mouse centre (tight zone)
      if (dist < 40) {
        p.vx -= (dx / dist) * 0.06
        p.vy -= (dy / dist) * 0.06
      }

      const speed = Math.hypot(p.vx, p.vy)
      if (speed > 1.4) { p.vx = (p.vx / speed) * 1.4; p.vy = (p.vy / speed) * 1.4 }

      p.x += p.vx; p.y += p.vy
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${p.col},${p.alpha})`
      ctx.fill()
    })

    // Connecting edges — amber tint only
    for (let i = 0; i < particles.length; i += 4) {
      for (let j = i + 4; j < particles.length; j += 4) {
        const dx = particles[i].x - particles[j].x
        const dy = particles[i].y - particles[j].y
        const d  = Math.hypot(dx, dy)
        if (d < 55) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(245,166,35,${(1 - d / 55) * 0.07})`
          ctx.lineWidth = 0.5
          ctx.moveTo(particles[i].x, particles[i].y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.stroke()
        }
      }
    }
  })
}

/* ── Hero entrance animation ── */
export function initHero() {
  initParticleField()

  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

  // Eyebrow label
  tl.to('.hero-eyebrow', { opacity: 1, y: 0, duration: 0.6 }, 0.3)

  // H1 — SplitText if available (GSAP Club), otherwise fallback
  const h1 = document.querySelector('.hero-h1')
  if (h1 && window.SplitText) {
    const split = new SplitText(h1, { type: 'chars' })
    tl.from(split.chars, {
      opacity: 0, y: 60, rotationX: -30,
      duration: 0.8, stagger: 0.022, ease: 'power3.out',
    }, 0.5)
  } else if (h1) {
    tl.from(h1, { opacity: 0, y: 40, duration: 0.9 }, 0.5)
  }

  // Sub-headline
  tl.to('.hero-sub', { opacity: 1, y: 0, duration: 0.7 }, '-=0.3')

  // CTA buttons
  tl.to('.hero-actions', { opacity: 1, duration: 0.4 }, '-=0.4')
  tl.from('.hero-actions .btn', {
    scale: 0.88, opacity: 0, stagger: 0.1, duration: 0.5,
    ease: 'back.out(1.7)',
  }, '-=0.35')

  // Status chips
  tl.to('.hero-chips', { opacity: 1, duration: 0.3 }, '-=0.2')
  tl.from('.hero-chip', {
    opacity: 0, y: 14, stagger: 0.06, duration: 0.4, ease: 'power2.out',
  }, '-=0.25')

  // Badge + scroll hint
  tl.to('.hero-badge',       { opacity: 1, duration: 0.5 }, '-=0.2')
  tl.to('.hero-scroll-hint', { opacity: 1, duration: 0.5 }, '-=0.3')
}
