// sections/05-swarm-viz.js — Pinned two-column + canvas node simulation
// Phases: Dispersion → Exploration → Convergence → Verdict
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

const PHASES = [
  { name: 'DISPERSION',   desc: '1,000 agents scatter across the evidence space' },
  { name: 'EXPLORATION',  desc: 'Sub-swarms probe each causal hypothesis' },
  { name: 'CONVERGENCE',  desc: 'High-confidence paths reinforce and cluster' },
  { name: 'VERDICT',      desc: 'Primary hypothesis emerges with probability score' },
]

let canvas, ctx, agents = [], animFrame, currentPhase = 0

function makeAgents(count, canvas) {
  const list = []
  for (let i = 0; i < count; i++) {
    list.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
      size: Math.random() * 2 + 1,
      alpha: Math.random() * 0.6 + 0.2,
      cluster: Math.floor(Math.random() * 4),
    })
  }
  return list
}

function resizeCanvas() {
  if (!canvas) return
  const rect = canvas.parentElement.getBoundingClientRect()
  canvas.width  = rect.width  || 420
  canvas.height = rect.width  || 420 // square
}

function getTargetForPhase(agent, phase, W, H) {
  // 4 quadrant centres
  const centres = [
    { x: W * 0.25, y: H * 0.25 },
    { x: W * 0.75, y: H * 0.25 },
    { x: W * 0.25, y: H * 0.75 },
    { x: W * 0.75, y: H * 0.75 },
  ]
  if (phase === 0) return null      // random scatter
  if (phase === 1) return centres[agent.cluster]  // explore quadrants
  if (phase === 2) return { x: W * 0.5, y: H * 0.5 } // converge centre
  return { x: W * 0.5, y: H * 0.5 }               // verdict ~ same
}

function tick() {
  if (!ctx || !canvas) return
  const W = canvas.width, H = canvas.height
  ctx.clearRect(0, 0, W, H)

  const accent = 'rgba(192,57,43,'
  const cold   = 'rgba(26,107,138,'

  agents.forEach(a => {
    const target = getTargetForPhase(a, currentPhase, W, H)
    if (target) {
      const pull = currentPhase === 2 ? 0.07 : currentPhase === 3 ? 0.12 : 0.04
      a.vx += (target.x - a.x) * pull * 0.01
      a.vy += (target.y - a.y) * pull * 0.01
    }
    const maxSpeed = currentPhase === 0 ? 2.5 : 1.8
    const speed = Math.hypot(a.vx, a.vy)
    if (speed > maxSpeed) { a.vx = (a.vx / speed) * maxSpeed; a.vy = (a.vy / speed) * maxSpeed }

    a.x += a.vx; a.y += a.vy
    if (a.x < 0 || a.x > W) a.vx *= -1
    if (a.y < 0 || a.y > H) a.vy *= -1

    // colour by cluster
    const col = a.cluster < 2 ? accent : cold
    ctx.beginPath()
    ctx.arc(a.x, a.y, a.size, 0, Math.PI * 2)
    ctx.fillStyle = col + a.alpha + ')'
    ctx.fill()
  })

  // Draw connections near verdict
  if (currentPhase >= 2) {
    const sample = agents.slice(0, 80)
    for (let i = 0; i < sample.length; i++) {
      for (let j = i + 1; j < sample.length; j++) {
        const dx = sample[i].x - sample[j].x
        const dy = sample[i].y - sample[j].y
        const d  = Math.hypot(dx, dy)
        if (d < 40) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(192,57,43,${(1 - d / 40) * 0.15})`
          ctx.lineWidth = 0.5
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
  if (fill) {
    gsap.to(fill, { width: `${((p + 1) / 4) * 100}%`, duration: 0.6, ease: 'power2.inOut' })
  }
}

export function initSwarmViz() {
  canvas = document.getElementById('swarm-canvas')
  if (!canvas) return
  ctx = canvas.getContext('2d')
  resizeCanvas()
  agents = makeAgents(200, canvas)

  // Phase buttons
  document.querySelectorAll('.swarm-phase').forEach((el, i) => {
    el.addEventListener('click', () => setPhase(i))
  })

  // Auto-cycle phases on scroll
  ScrollTrigger.create({
    trigger: '#swarm-viz',
    start: 'top 80%',
    onEnter: () => {
      animFrame && cancelAnimationFrame(animFrame)
      tick()
      // Auto-advance phases
      const seq = [0, 1, 2, 3]
      seq.forEach((p, i) => {
        gsap.delayedCall(i * 3, () => setPhase(p))
      })
    },
    onLeave: () => { cancelAnimationFrame(animFrame) },
    onEnterBack: () => { tick() },
    onLeaveBack: () => { cancelAnimationFrame(animFrame) },
  })

  // Stagger phase pills in
  gsap.to('.swarm-phase', {
    opacity: 1, y: 0,
    duration: 0.6,
    ease: 'power3.out',
    stagger: 0.08,
    scrollTrigger: { trigger: '#swarm-viz', start: 'top 80%' }
  })

  gsap.from('.swarm-text .section-label, .swarm-text .section-heading, .swarm-text .section-sub', {
    opacity: 0, y: 25, duration: 0.7, ease: 'power3.out', stagger: 0.1,
    scrollTrigger: { trigger: '#swarm-viz', start: 'top 80%' }
  })

  window.addEventListener('resize', () => {
    resizeCanvas()
    agents = makeAgents(200, canvas)
  })
}
