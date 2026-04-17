// sections/05-swarm-viz.js — Premium swarm canvas with amber/steel clustering
// Phases: Dispersion → Exploration → Convergence → Verdict
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

const PHASES = [
  { name: 'DISPERSION',   label: 'Dispersion',   desc: '1,000 agents scatter across the evidence space' },
  { name: 'EXPLORATION',  label: 'Exploration',   desc: 'Sub-swarms probe each causal hypothesis' },
  { name: 'CONVERGENCE',  label: 'Convergence',   desc: 'Evidence-aligned paths reinforce and cluster' },
  { name: 'VERDICT',      label: 'Verdict',       desc: 'Primary hypothesis emerges with probability score' },
]

// Agent archetypes mapped to colours
const ARCHETYPE_COLS = [
  '245,166,35',   // amber  — forensic / evidence
  '46,170,240',   // steel  — behavioral / timeline
  '46,204,113',   // green  — alibi verifiers
  '155,89,182',   // violet — suspect personas
]

let canvas, ctx, agents = [], animFrame, currentPhase = 0

function makeAgents(count, canvasEl) {
  return Array.from({ length: count }, (_, i) => ({
    x:       Math.random() * canvasEl.width,
    y:       Math.random() * canvasEl.height,
    vx:      (Math.random() - 0.5) * 2.2,
    vy:      (Math.random() - 0.5) * 2.2,
    size:    Math.random() * 2 + 0.8,
    alpha:   Math.random() * 0.65 + 0.2,
    cluster: i % 4,                        // 4 archetype clusters
    trail:   [],
  }))
}

function resizeCanvas() {
  if (!canvas) return
  const rect = canvas.parentElement.getBoundingClientRect()
  canvas.width  = rect.width  || 420
  canvas.height = rect.width  || 420
}

function getTarget(agent, phase, W, H) {
  // 4 cluster centres mapped to hypothesis quadrants
  const centres = [
    { x: W * 0.28, y: H * 0.28 },
    { x: W * 0.72, y: H * 0.28 },
    { x: W * 0.28, y: H * 0.72 },
    { x: W * 0.72, y: H * 0.72 },
  ]
  if (phase === 0) return null                      // scatter
  if (phase === 1) return centres[agent.cluster]    // explore quadrant
  if (phase === 2) {
    // Converge: amber/steel agents head to top-left (H-001), others to centre
    return agent.cluster < 2
      ? { x: W * 0.32, y: H * 0.32 }
      : { x: W * 0.5,  y: H * 0.5  }
  }
  // Verdict: all converge to top-left hypothesis node
  return { x: W * 0.3, y: H * 0.3 }
}

function tick() {
  if (!ctx || !canvas) return
  const W = canvas.width, H = canvas.height
  // Fade trail
  ctx.fillStyle = 'rgba(8, 10, 15, 0.35)'
  ctx.fillRect(0, 0, W, H)

  agents.forEach(a => {
    const target = getTarget(a, currentPhase, W, H)
    if (target) {
      const pull = currentPhase === 3 ? 0.14 : currentPhase === 2 ? 0.08 : 0.04
      a.vx += (target.x - a.x) * pull * 0.012
      a.vy += (target.y - a.y) * pull * 0.012
    }

    // Add light noise to keep it organic
    a.vx += (Math.random() - 0.5) * 0.08
    a.vy += (Math.random() - 0.5) * 0.08

    const maxSpeed = currentPhase === 0 ? 2.8 : currentPhase === 3 ? 1.2 : 1.8
    const speed = Math.hypot(a.vx, a.vy)
    if (speed > maxSpeed) { a.vx = (a.vx / speed) * maxSpeed; a.vy = (a.vy / speed) * maxSpeed }

    a.x += a.vx; a.y += a.vy
    // Bounce off walls softly
    if (a.x < 2)   { a.x = 2;   a.vx = Math.abs(a.vx) }
    if (a.x > W-2) { a.x = W-2; a.vx = -Math.abs(a.vx) }
    if (a.y < 2)   { a.y = 2;   a.vy = Math.abs(a.vy) }
    if (a.y > H-2) { a.y = H-2; a.vy = -Math.abs(a.vy) }

    const col = ARCHETYPE_COLS[a.cluster]
    ctx.beginPath()
    ctx.arc(a.x, a.y, a.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${col},${a.alpha})`
    ctx.fill()
  })

  // Draw hypothesis label nodes in Verdict phase
  if (currentPhase >= 2) {
    const nodes = [
      { x: W * 0.3,  y: H * 0.3,  label: 'H-001', prob: '43%', col: '245,166,35' },
      { x: W * 0.7,  y: H * 0.28, label: 'H-002', prob: '31%', col: '46,170,240' },
      { x: W * 0.28, y: H * 0.7,  label: 'H-003', prob: '18%', col: '46,204,113' },
      { x: W * 0.7,  y: H * 0.72, label: 'H-004', prob: ' 8%', col: '155,89,182' },
    ]
    nodes.forEach(n => {
      const alpha = currentPhase === 3 && n.label === 'H-001' ? 1.0 : 0.55
      const radius = currentPhase === 3 && n.label === 'H-001' ? 14 : 9
      // Glow
      const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, radius * 3)
      grd.addColorStop(0, `rgba(${n.col},${alpha * 0.35})`)
      grd.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.beginPath(); ctx.arc(n.x, n.y, radius * 3, 0, Math.PI * 2)
      ctx.fillStyle = grd; ctx.fill()
      // Node
      ctx.beginPath(); ctx.arc(n.x, n.y, radius, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(${n.col},${alpha})`; ctx.fill()
      // Label
      if (currentPhase >= 3) {
        ctx.fillStyle = `rgba(${n.col},0.9)`
        ctx.font = `500 10px 'JetBrains Mono', monospace`
        ctx.fillText(`${n.label} ${n.prob}`, n.x + radius + 4, n.y + 4)
      }
    })

    // Draw connection lines between nearby agents during convergence
    const sample = agents.slice(0, 100)
    for (let i = 0; i < sample.length; i++) {
      for (let j = i + 1; j < sample.length; j++) {
        const dx = sample[i].x - sample[j].x
        const dy = sample[i].y - sample[j].y
        const d  = Math.hypot(dx, dy)
        if (d < 38) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(245,166,35,${(1 - d / 38) * 0.18})`
          ctx.lineWidth = 0.8
          ctx.moveTo(sample[i].x, sample[i].y)
          ctx.lineTo(sample[j].x, sample[j].y)
          ctx.stroke()
        }
      }
    }
  }

  animFrame = requestAnimationFrame(tick)
}

function setPhase(p) {
  currentPhase = p
  document.querySelectorAll('.swarm-phase').forEach((el, i) => {
    el.classList.toggle('active', i === p)
  })
  const label = document.querySelector('.swarm-state-label')
  if (label) label.textContent = PHASES[p].name
  const fill = document.querySelector('.swarm-progress-fill')
  if (fill) gsap.to(fill, { width: `${((p + 1) / 4) * 100}%`, duration: 0.7, ease: 'power2.inOut' })
}

export function initSwarmViz() {
  canvas = document.getElementById('swarm-canvas')
  if (!canvas) return
  ctx = canvas.getContext('2d')
  resizeCanvas()
  agents = makeAgents(220, canvas)

  // Phase click handlers
  document.querySelectorAll('.swarm-phase').forEach((el, i) => {
    el.addEventListener('click', () => setPhase(i))
  })

  // Auto-cycle on scroll enter
  ScrollTrigger.create({
    trigger: '#swarm-viz',
    start: 'top 75%',
    onEnter: () => {
      cancelAnimationFrame(animFrame)
      tick()
      setPhase(0)
      ;[0, 1, 2, 3].forEach((p, i) => gsap.delayedCall(i * 3.2, () => setPhase(p)))
    },
    onLeave:     () => cancelAnimationFrame(animFrame),
    onEnterBack: () => { cancelAnimationFrame(animFrame); tick() },
    onLeaveBack: () => cancelAnimationFrame(animFrame),
  })

  // Animate phase pills
  gsap.to('.swarm-phase', {
    opacity: 1, y: 0, duration: 0.6, ease: 'power3.out', stagger: 0.09,
    scrollTrigger: { trigger: '#swarm-viz', start: 'top 75%' }
  })

  gsap.from('.swarm-text .section-label, .swarm-text .section-heading, .swarm-text .section-sub', {
    opacity: 0, y: 28, duration: 0.7, ease: 'power3.out', stagger: 0.12,
    scrollTrigger: { trigger: '#swarm-viz', start: 'top 75%' }
  })

  window.addEventListener('resize', () => {
    resizeCanvas()
    agents = makeAgents(220, canvas)
  })
}
