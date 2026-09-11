import { demoCaseNodes, demoCaseEdges } from '../data/demoCase'

interface SimNode {
  id: string
  label: string
  type: string
  color: string
  x: number
  y: number
  vx: number
  vy: number
  radius: number
}

interface SimEdge {
  source: string
  target: string
  label: string
  confidence: number
}

interface ScanRing {
  x: number
  y: number
  radius: number
  maxRadius: number
  alpha: number
}

export interface CaseGraphSimInstance {
  pause: () => void
  resume: () => void
  resize: (width: number, height: number) => void
  destroy: () => void
}

export function initCaseGraphSim(
  canvas: HTMLCanvasElement,
  container?: HTMLElement
): CaseGraphSimInstance {
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return {
      pause: () => {},
      resume: () => {},
      resize: () => {},
      destroy: () => {},
    }
  }

  let animationFrameId: number | null = null
  let isRunning = false
  let isVisible = true
  let isDocumentVisible = !document.hidden
  let lastTime = 0
  let scanIntervalTimer: ReturnType<typeof setInterval> | null = null

  // Check reduced motion
  const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  let prefersReducedMotion = reducedMotionQuery.matches

  const handleReducedMotionChange = (e: MediaQueryListEvent) => {
    prefersReducedMotion = e.matches
    if (prefersReducedMotion) {
      stopScanInterval()
    } else {
      startScanInterval()
    }
  }
  reducedMotionQuery.addEventListener('change', handleReducedMotionChange)

  // Bounded nodes and edges
  let width = canvas.clientWidth || 800
  let height = canvas.clientHeight || 600
  let dpr = Math.min(window.devicePixelRatio || 1, 2)

  function updateCanvasDimensions(w: number, h: number) {
    width = w
    height = h
    dpr = Math.min(window.devicePixelRatio || 1, 2)
    canvas.width = Math.floor(w * dpr)
    canvas.height = Math.floor(h * dpr)
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`
    ctx?.scale(dpr, dpr)
  }

  updateCanvasDimensions(width, height)

  // Initialize nodes distributed around center
  const cx = width / 2
  const cy = height / 2
  const radius = Math.min(width, height) * 0.32

  const nodes: SimNode[] = demoCaseNodes.map((node, i) => {
    const angle = (i / demoCaseNodes.length) * Math.PI * 2
    return {
      id: node.id,
      label: node.label,
      type: node.type,
      color: node.color,
      x: cx + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
      y: cy + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      radius: node.id === 'n5' ? 8 : 6.5,
    }
  })

  const nodeMap = new Map<string, SimNode>()
  nodes.forEach((n) => nodeMap.set(n.id, n))

  const edges: SimEdge[] = demoCaseEdges

  // Scan ring ripples
  const scanRings: ScanRing[] = []

  function triggerScanRing() {
    if (prefersReducedMotion || !nodes.length) return
    const randomNode = nodes[Math.floor(Math.random() * nodes.length)]
    scanRings.push({
      x: randomNode.x,
      y: randomNode.y,
      radius: 8,
      maxRadius: 180,
      alpha: 0.8,
    })
  }

  function startScanInterval() {
    stopScanInterval()
    if (!prefersReducedMotion) {
      scanIntervalTimer = setInterval(triggerScanRing, 5000)
    }
  }

  function stopScanInterval() {
    if (scanIntervalTimer) {
      clearInterval(scanIntervalTimer)
      scanIntervalTimer = null
    }
  }

  // Physics update (Repulsion ~1800, Damping 0.88, Center Pull)
  function stepPhysics() {
    if (prefersReducedMotion) return

    const kRepel = 1800
    const damping = 0.88
    const centerStrength = 0.0008

    for (let i = 0; i < nodes.length; i++) {
      const n1 = nodes[i]

      // Repulsion from other nodes
      for (let j = i + 1; j < nodes.length; j++) {
        const n2 = nodes[j]
        const dx = n2.x - n1.x
        const dy = n2.y - n1.y
        const distSq = dx * dx + dy * dy + 100
        const dist = Math.sqrt(distSq)
        const force = kRepel / distSq

        const fx = (dx / dist) * force
        const fy = (dy / dist) * force

        n1.vx -= fx
        n1.vy -= fy
        n2.vx += fx
        n2.vy += fy
      }

      // Spring pull along edges
      for (const edge of edges) {
        if (edge.source === n1.id) {
          const target = nodeMap.get(edge.target)
          if (target) {
            const dx = target.x - n1.x
            const dy = target.y - n1.y
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            const desiredDist = 130
            const springForce = (dist - desiredDist) * 0.003
            n1.vx += (dx / dist) * springForce
            n1.vy += (dy / dist) * springForce
          }
        }
      }

      // Center gravity
      const toCenterX = width / 2 - n1.x
      const toCenterY = height / 2 - n1.y
      n1.vx += toCenterX * centerStrength
      n1.vy += toCenterY * centerStrength

      // Damping
      n1.vx *= damping
      n1.vy *= damping

      // Velocity limit
      const speed = Math.sqrt(n1.vx * n1.vx + n1.vy * n1.vy)
      if (speed > 1.2) {
        n1.vx = (n1.vx / speed) * 1.2
        n1.vy = (n1.vy / speed) * 1.2
      }

      // Update positions
      n1.x += n1.vx
      n1.y += n1.vy

      // Soft boundary bounce
      const pad = 40
      if (n1.x < pad) { n1.x = pad; n1.vx *= -0.5 }
      if (n1.x > width - pad) { n1.x = width - pad; n1.vx *= -0.5 }
      if (n1.y < pad) { n1.y = pad; n1.vy *= -0.5 }
      if (n1.y > height - pad) { n1.y = height - pad; n1.vy *= -0.5 }
    }
  }

  // Draw frame
  function render() {
    if (!ctx) return
    ctx.clearRect(0, 0, width, height)

    // 1. Draw hairline edges
    ctx.lineWidth = 1
    for (const edge of edges) {
      const s = nodeMap.get(edge.source)
      const t = nodeMap.get(edge.target)
      if (!s || !t) continue

      ctx.beginPath()
      ctx.moveTo(s.x, s.y)
      ctx.lineTo(t.x, t.y)
      ctx.strokeStyle = 'rgba(180, 175, 168, 0.45)'
      ctx.stroke()

      // Edge label (10px mono)
      const midX = (s.x + t.x) / 2
      const midY = (s.y + t.y) / 2
      ctx.font = '10px "JetBrains Mono", monospace'
      ctx.fillStyle = 'rgba(120, 115, 110, 0.65)'
      ctx.fillText(edge.label, midX + 4, midY - 4)
    }

    // 2. Draw terracotta scan rings
    for (let i = scanRings.length - 1; i >= 0; i--) {
      const ring = scanRings[i]
      ring.radius += 1.2
      ring.alpha = Math.max(0, 0.8 * (1 - ring.radius / ring.maxRadius))

      if (ring.radius >= ring.maxRadius || ring.alpha <= 0) {
        scanRings.splice(i, 1)
        continue
      }

      ctx.save()
      ctx.beginPath()
      ctx.arc(ring.x, ring.y, ring.radius, 0, Math.PI * 2)
      ctx.strokeStyle = `rgba(180, 80, 50, ${ring.alpha})`
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.restore()
    }

    // 3. Draw nodes
    for (const node of nodes) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2)
      ctx.fillStyle = node.color
      ctx.fill()

      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 1.5
      ctx.stroke()

      // Node label
      ctx.font = '10px "JetBrains Mono", monospace'
      ctx.fillStyle = 'rgba(60, 55, 50, 0.9)'
      ctx.fillText(node.label, node.x + node.radius + 6, node.y + 3)
    }
  }

  function frameLoop(time: number) {
    if (!isRunning) return

    const delta = time - lastTime
    lastTime = time

    // Keep execution under 6ms
    const start = performance.now()
    stepPhysics()
    render()
    const elapsed = performance.now() - start

    if (elapsed > 6 && !prefersReducedMotion) {
      // Sub-sample physics if CPU is burdened
    }

    if (isRunning && isVisible && isDocumentVisible) {
      animationFrameId = requestAnimationFrame(frameLoop)
    }
  }

  function start() {
    if (isRunning) return
    isRunning = true
    lastTime = performance.now()
    startScanInterval()
    // Initial render
    render()
    animationFrameId = requestAnimationFrame(frameLoop)
  }

  function pause() {
    isRunning = false
    stopScanInterval()
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
  }

  function resume() {
    if (!isRunning && isVisible && isDocumentVisible) {
      start()
    }
  }

  // Handle visibility change (tab hidden)
  const handleVisibilityChange = () => {
    isDocumentVisible = !document.hidden
    if (isDocumentVisible) {
      resume()
    } else {
      pause()
    }
  }
  document.addEventListener('visibilitychange', handleVisibilityChange)

  // IntersectionObserver to pause when off-screen
  let observer: IntersectionObserver | null = null
  const observeTarget = container || canvas
  if (typeof IntersectionObserver !== 'undefined') {
    observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        isVisible = entry ? entry.isIntersecting : true
        if (isVisible) {
          resume()
        } else {
          pause()
        }
      },
      { threshold: 0.05 }
    )
    observer.observe(observeTarget)
  }

  // Start immediately
  start()

  return {
    pause,
    resume,
    resize: (w: number, h: number) => {
      updateCanvasDimensions(w, h)
      render()
    },
    destroy: () => {
      pause()
      reducedMotionQuery.removeEventListener('change', handleReducedMotionChange)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      if (observer) {
        observer.disconnect()
        observer = null
      }
    },
  }
}
