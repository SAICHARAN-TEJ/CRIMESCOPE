<template>
  <canvas ref="canvasRef" class="particle-field"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvasRef = ref(null)
let ctx = null
let animFrame = null
let mouse = { x: -9999, y: -9999 }
let particles = []
let connections = []
const PARTICLE_COUNT = 80
const CONNECTION_DIST = 150
const MOUSE_RADIUS = 200

class Particle {
  constructor(w, h) {
    this.x = Math.random() * w
    this.y = Math.random() * h
    this.vx = (Math.random() - 0.5) * 0.5
    this.vy = (Math.random() - 0.5) * 0.5
    this.radius = 1.5 + Math.random() * 2.5
    this.baseRadius = this.radius
    const rand = Math.random()
    if (rand < 0.4) this.color = [120, 255, 160]      // green
    else if (rand < 0.7) this.color = [140, 140, 160]  // gray
    else this.color = [255, 100, 100]                    // red
    this.alpha = 0.3 + Math.random() * 0.4
    this.pulseOffset = Math.random() * Math.PI * 2
  }

  update(w, h, time) {
    this.x += this.vx
    this.y += this.vy

    if (this.x < 0 || this.x > w) this.vx *= -1
    if (this.y < 0 || this.y > h) this.vy *= -1

    const dx = mouse.x - this.x
    const dy = mouse.y - this.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist < MOUSE_RADIUS) {
      const force = (MOUSE_RADIUS - dist) / MOUSE_RADIUS
      this.vx -= (dx / dist) * force * 0.02
      this.vy -= (dy / dist) * force * 0.02
      this.radius = this.baseRadius + force * 3
    } else {
      this.radius += (this.baseRadius - this.radius) * 0.05
    }

    this.alpha = 0.3 + 0.2 * Math.sin(time * 0.002 + this.pulseOffset)
  }

  draw(ctx) {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${this.color[0]}, ${this.color[1]}, ${this.color[2]}, ${this.alpha})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(this.x, this.y, this.radius + 4, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${this.color[0]}, ${this.color[1]}, ${this.color[2]}, ${this.alpha * 0.15})`
    ctx.fill()
  }
}

function initParticles(w, h) {
  particles = []
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle(w, h))
  }
}

function drawConnections(ctx) {
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)

      if (dist < CONNECTION_DIST) {
        const alpha = (1 - dist / CONNECTION_DIST) * 0.15
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.strokeStyle = `rgba(120, 255, 160, ${alpha})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  }
}

function animate(time) {
  if (!ctx || !canvasRef.value) return

  const w = canvasRef.value.width
  const h = canvasRef.value.height

  ctx.clearRect(0, 0, w, h)

  particles.forEach(p => {
    p.update(w, h, time)
    p.draw(ctx)
  })

  drawConnections(ctx)
  animFrame = requestAnimationFrame(animate)
}

function resize() {
  if (!canvasRef.value) return
  const dpr = window.devicePixelRatio || 1
  const rect = canvasRef.value.getBoundingClientRect()
  canvasRef.value.width = rect.width * dpr
  canvasRef.value.height = rect.height * dpr
  ctx.scale(dpr, dpr)
  canvasRef.value.style.width = rect.width + 'px'
  canvasRef.value.style.height = rect.height + 'px'
  initParticles(rect.width, rect.height)
}

function onMouse(e) {
  mouse.x = e.clientX
  mouse.y = e.clientY
}

function onMouseLeave() {
  mouse.x = -9999
  mouse.y = -9999
}

onMounted(() => {
  ctx = canvasRef.value.getContext('2d')
  resize()
  animFrame = requestAnimationFrame(animate)

  window.addEventListener('resize', resize)
  window.addEventListener('mousemove', onMouse)
  window.addEventListener('mouseleave', onMouseLeave)
})

onUnmounted(() => {
  cancelAnimationFrame(animFrame)
  window.removeEventListener('resize', resize)
  window.removeEventListener('mousemove', onMouse)
  window.removeEventListener('mouseleave', onMouseLeave)
})
</script>

<style scoped>
.particle-field {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}
</style>
