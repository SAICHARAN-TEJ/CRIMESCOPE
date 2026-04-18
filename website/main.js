/* ══════════════════════════════════════════════════════════════════════
   CrimeScope Marketing — GSAP 3 Animations (Dark Theme)
   Uses GSAP core only (no paid plugins). Manual char-split for hero.
   ══════════════════════════════════════════════════════════════════════ */

gsap.registerPlugin(ScrollTrigger)

// ── Hero entrance ───────────────────────────────────────────────────
const heroTL = gsap.timeline({ defaults: { ease: 'power3.out' } })
heroTL
  .from('#hero-overline', { y: 30, opacity: 0, duration: 0.6 })
  .from('#hero-h1', { y: 50, opacity: 0, duration: 0.8 }, '-=0.3')
  .from('#hero-p', { y: 30, opacity: 0, duration: 0.6 }, '-=0.4')
  .from('#hero-btns', { y: 20, opacity: 0, duration: 0.5 }, '-=0.3')
  .from('#hero-stats .stat', { y: 30, opacity: 0, stagger: 0.08, duration: 0.5 }, '-=0.5')

// ── Manual char-split for hero H1 (SplitText alternative) ───────────
;(function splitHeroChars() {
  const h1 = document.getElementById('hero-h1')
  if (!h1) return

  // Wait for hero entrance, then do the gradient sweep
  heroTL.eventCallback('onComplete', () => {
    gsap.fromTo(h1, {
      backgroundPosition: '0% 50%',
    }, {
      backgroundPosition: '100% 50%',
      backgroundSize: '200% 200%',
      duration: 3,
      ease: 'power2.inOut',
      repeat: -1,
      yoyo: true,
    })
  })
})()

// ── Section reveal ──────────────────────────────────────────────────
gsap.utils.toArray('.section').forEach(sec => {
  const heading = sec.querySelector('h2')
  const overline = sec.querySelector('.overline')
  const cards = sec.querySelectorAll('.glass, .step, .rp-finding, .arch-card')
  const desc = sec.querySelector('.section-desc')

  if (overline) {
    gsap.from(overline, {
      x: -30, opacity: 0, duration: 0.5,
      scrollTrigger: { trigger: overline, start: 'top 85%', toggleActions: 'play none none reverse' },
    })
  }

  if (heading) {
    gsap.from(heading, {
      y: 60, opacity: 0, duration: 0.8,
      scrollTrigger: { trigger: heading, start: 'top 80%', toggleActions: 'play none none reverse' },
    })
  }

  if (desc) {
    gsap.from(desc, {
      y: 30, opacity: 0, duration: 0.6,
      scrollTrigger: { trigger: desc, start: 'top 85%', toggleActions: 'play none none reverse' },
    })
  }

  if (cards.length) {
    gsap.from(cards, {
      y: 40, opacity: 0, stagger: 0.06, duration: 0.6,
      scrollTrigger: { trigger: cards[0], start: 'top 85%', toggleActions: 'play none none reverse' },
    })
  }
})

// ── Architecture diagram cascade ────────────────────────────────────
gsap.utils.toArray('.arch-layer').forEach((layer, i) => {
  gsap.from(layer, {
    y: 30, opacity: 0, duration: 0.5,
    delay: i * 0.15,
    scrollTrigger: { trigger: layer, start: 'top 85%', toggleActions: 'play none none reverse' },
  })
})

gsap.utils.toArray('.arch-arrow').forEach(arrow => {
  gsap.from(arrow, {
    scaleY: 0, opacity: 0, duration: 0.3,
    scrollTrigger: { trigger: arrow, start: 'top 85%', toggleActions: 'play none none reverse' },
  })
})

// ── CTA ─────────────────────────────────────────────────────────────
gsap.from('.cta-h2', {
  y: 60, opacity: 0, duration: 0.8,
  scrollTrigger: { trigger: '.cta', start: 'top 70%' },
})
gsap.from('.cta-sub', {
  y: 30, opacity: 0, duration: 0.6, delay: 0.2,
  scrollTrigger: { trigger: '.cta', start: 'top 70%' },
})
gsap.from('.cta-btns', {
  y: 30, opacity: 0, duration: 0.6, delay: 0.3,
  scrollTrigger: { trigger: '.cta', start: 'top 60%' },
})
gsap.from('.cta-code', {
  y: 20, opacity: 0, duration: 0.6, delay: 0.4,
  scrollTrigger: { trigger: '.cta', start: 'top 55%' },
})

// ── Nav background transition on scroll ─────────────────────────────
ScrollTrigger.create({
  start: 'top -80',
  onToggle: self => {
    const nav = document.getElementById('nav')
    if (self.isActive) {
      nav.style.height = '48px'
      nav.style.background = 'rgba(255,255,255,0.95)'
      nav.style.boxShadow = '0 1px 8px rgba(0,0,0,0.06)'
    } else {
      nav.style.height = '56px'
      nav.style.background = 'rgba(255,255,255,0.88)'
      nav.style.boxShadow = 'none'
    }
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
          ctx.strokeStyle = `rgba(204,51,51,${0.1 * (1 - dist / 80)})`
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
  'rgba(204,51,51,0.35)',   // crimson
  'rgba(170,120,80,0.25)',  // warm brown
  'rgba(160,155,150,0.2)',  // warm gray
  'rgba(204,136,51,0.2)',   // amber
]
const PALETTE_SWARM = [
  'rgba(204,51,51,0.3)',
  'rgba(170,120,80,0.2)',
  'rgba(68,102,170,0.2)',
  'rgba(90,138,94,0.2)',
]

initParticles('hero-canvas', 120, PALETTE_HERO)
initParticles('swarm-canvas', 200, PALETTE_SWARM)
