/* ══════════════════════════════════════════════════════════════════════
   CrimeScope Marketing — GSAP + Canvas Particles (Red/Brown palette)
   ══════════════════════════════════════════════════════════════════════ */

gsap.registerPlugin(ScrollTrigger)

// ── Hero entrance ───────────────────────────────────────────────────
const heroTL = gsap.timeline({ defaults: { ease: 'power3.out' } })
heroTL
  .from('#hero-overline', { y: 30, opacity: 0, duration: 0.6 })
  .from('#hero-h1', { y: 50, opacity: 0, duration: 0.8 }, '-=0.3')
  .from('#hero-p', { y: 30, opacity: 0, duration: 0.6 }, '-=0.4')
  .from('#hero-btns', { y: 20, opacity: 0, duration: 0.5 }, '-=0.3')
  .from('#hero-viz', { scale: 0.9, opacity: 0, duration: 1 }, '-=0.6')
  .from('#hero-stats .stat', { y: 30, opacity: 0, stagger: 0.08, duration: 0.5 }, '-=0.5')

// ── Section reveal ──────────────────────────────────────────────────
gsap.utils.toArray('.section').forEach(sec => {
  const heading = sec.querySelector('h2')
  const cards = sec.querySelectorAll('.glass, .step, .rp-finding')

  if (heading) {
    gsap.from(heading, {
      y: 60, opacity: 0, duration: 0.8,
      scrollTrigger: { trigger: heading, start: 'top 80%', toggleActions: 'play none none reverse' },
    })
  }

  if (cards.length) {
    gsap.from(cards, {
      y: 40, opacity: 0, stagger: 0.08, duration: 0.6,
      scrollTrigger: { trigger: cards[0], start: 'top 85%', toggleActions: 'play none none reverse' },
    })
  }
})

// ── CTA ─────────────────────────────────────────────────────────────
gsap.from('.cta-h2', {
  y: 60, opacity: 0, duration: 0.8,
  scrollTrigger: { trigger: '.cta', start: 'top 70%' },
})
gsap.from('.cta-btns', {
  y: 30, opacity: 0, duration: 0.6,
  scrollTrigger: { trigger: '.cta', start: 'top 60%' },
})

// ── Nav shrink on scroll ────────────────────────────────────────────
ScrollTrigger.create({
  start: 'top -80',
  onToggle: self => {
    document.getElementById('nav').style.height = self.isActive ? '48px' : '56px'
  },
})

// ══════════════════════════════════════════════════════════════════════
// Particle canvas — hero & swarm sections (red/brown/gray palette)
// ══════════════════════════════════════════════════════════════════════

function initParticles(canvasId, count, palette) {
  const canvas = document.getElementById(canvasId)
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let w = 0, h = 0

  const resize = () => {
    w = canvas.offsetWidth
    h = canvas.offsetHeight
    canvas.width = w * devicePixelRatio
    canvas.height = h * devicePixelRatio
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
  }
  resize()
  window.addEventListener('resize', resize)

  const particles = Array.from({ length: count }, () => ({
    x: Math.random() * (w || 500),
    y: Math.random() * (h || 400),
    vx: (Math.random() - 0.5) * 0.4,
    vy: (Math.random() - 0.5) * 0.4,
    r: 1 + Math.random() * 2,
    color: palette[Math.floor(Math.random() * palette.length)],
  }))

  function draw() {
    ctx.clearRect(0, 0, w, h)

    // Draw connections
    ctx.lineWidth = 0.3
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x
        const dy = particles[i].y - particles[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 80) {
          ctx.strokeStyle = `rgba(204,51,51,${0.12 * (1 - dist / 80)})`
          ctx.beginPath()
          ctx.moveTo(particles[i].x, particles[i].y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.stroke()
        }
      }
    }

    // Draw particles
    for (const p of particles) {
      p.x += p.vx
      p.y += p.vy
      if (p.x < 0 || p.x > w) p.vx *= -1
      if (p.y < 0 || p.y > h) p.vy *= -1

      ctx.fillStyle = p.color
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fill()
    }

    requestAnimationFrame(draw)
  }
  draw()
}

const PALETTE_HERO = [
  'rgba(204,51,51,0.7)',   // red
  'rgba(139,94,60,0.6)',   // brown
  'rgba(107,101,96,0.5)',  // gray
  'rgba(204,136,51,0.5)',  // amber
]
const PALETTE_SWARM = [
  'rgba(204,51,51,0.5)',
  'rgba(139,94,60,0.4)',
  'rgba(85,119,170,0.4)',
  'rgba(122,158,126,0.3)',
]

initParticles('hero-canvas', 120, PALETTE_HERO)
initParticles('swarm-canvas', 200, PALETTE_SWARM)
