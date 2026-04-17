'use client';
// components/CinematicCityCanvas.tsx — Scroll-driven Three.js hero
import { useEffect, useRef, useCallback } from 'react';
import type { MotionValue } from 'framer-motion';
import { useMotionValueEvent } from 'framer-motion';
import { smoothstep } from '@/lib/utils';

interface Props {
  scrollYProgress: MotionValue<number>;
}

// ── Agent types and counts ────────────────────────────────────
const MAX_AGENTS = 2847;
const GRID_SIZE  = 80;  // city grid cells
const CELL       = 10;  // world units per cell

// Color palettes [R, G, B] (0..1)
const COLORS = {
  suspect:  [0.776, 0.157, 0.157] as [number, number, number],
  lea:      [0.051, 0.278, 0.631] as [number, number, number],
  witness:  [0.216, 0.278, 0.310] as [number, number, number],
};

function smoothstepFn(e0: number, e1: number, x: number) {
  return smoothstep(e0, e1, x);
}

function randRange(a: number, b: number) {
  return a + Math.random() * (b - a);
}

export default function CinematicCityCanvas({ scrollYProgress }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef  = useRef({
    zoom:          1,
    rotZ:          0,
    heatOpacity:   0,
    agentCount:    0,
    scroll:        0,
    frameId:       0,
  });

  // Agent positions
  const agentPositions = useRef<Float32Array>(new Float32Array(MAX_AGENTS * 2));
  const agentTargets   = useRef<Float32Array>(new Float32Array(MAX_AGENTS * 2));
  const agentTypes     = useRef<Uint8Array>(new Uint8Array(MAX_AGENTS)); // 0=suspect,1=lea,2=witness

  // Network edges (pairs of agent indices)
  const edgeIndices = useRef<Uint16Array>(new Uint16Array(0));

  useEffect(() => {
    // Initialize agent positions
    const pos = agentPositions.current;
    const tgt = agentTargets.current;
    const typ = agentTypes.current;
    const half = GRID_SIZE * CELL * 0.5;

    for (let i = 0; i < MAX_AGENTS; i++) {
      const x = randRange(-half, half);
      const y = randRange(-half, half);
      pos[i * 2]     = x; pos[i * 2 + 1] = y;
      tgt[i * 2]     = x; tgt[i * 2 + 1] = y;
      // Role distribution: 60% suspect, 25% lea, 15% witness
      typ[i] = i < MAX_AGENTS * 0.6 ? 0 : i < MAX_AGENTS * 0.85 ? 1 : 2;
    }

    // Initialize edges (connect suspect agents)
    const edgeCount = 600;
    const edges = new Uint16Array(edgeCount * 2);
    for (let e = 0; e < edgeCount; e++) {
      edges[e * 2]     = Math.floor(Math.random() * (MAX_AGENTS * 0.6));
      edges[e * 2 + 1] = Math.floor(Math.random() * (MAX_AGENTS * 0.6));
    }
    edgeIndices.current = edges;
  }, []);

  // Scatter targets randomly inside a cluster radius
  const reshuffleTargets = useCallback((clustered: boolean, scroll: number) => {
    const tgt = agentTargets.current;
    const typ = agentTypes.current;
    const half = GRID_SIZE * CELL * 0.5;
    // Hotspot centers (phase 50%+)
    const hotspots = [
      [half * 0.2,  half * 0.1],
      [-half * 0.3, half * 0.25],
      [half * 0.1, -half * 0.3],
    ];
    for (let i = 0; i < MAX_AGENTS; i++) {
      if (clustered && typ[i] === 0) {
        const hs = hotspots[i % hotspots.length];
        tgt[i * 2]     = hs[0] + randRange(-120, 120);
        tgt[i * 2 + 1] = hs[1] + randRange(-120, 120);
      } else if (scroll > 0.2) {
        // gentle drift
        tgt[i * 2]     += randRange(-60, 60);
        tgt[i * 2 + 1] += randRange(-60, 60);
        const max = half * 0.95;
        tgt[i * 2]     = Math.max(-max, Math.min(max, tgt[i * 2]));
        tgt[i * 2 + 1] = Math.max(-max, Math.min(max, tgt[i * 2 + 1]));
      }
    }
  }, []);

  // Lerp agents toward targets every frame
  const tickAgents = useCallback((alpha: number) => {
    const pos = agentPositions.current;
    const tgt = agentTargets.current;
    for (let i = 0; i < MAX_AGENTS; i++) {
      pos[i * 2]     += (tgt[i * 2]     - pos[i * 2])     * alpha;
      pos[i * 2 + 1] += (tgt[i * 2 + 1] - pos[i * 2 + 1]) * alpha;
    }
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let lastReshuffle = -1;
    let lastClustered = false;

    function resize() {
      if (!canvas) return;
      const px = window.devicePixelRatio || 1;
      canvas.width  = window.innerWidth  * px;
      canvas.height = window.innerHeight * px;
      canvas.style.width  = '100%';
      canvas.style.height = '100%';
    }
    resize();
    window.addEventListener('resize', resize);

    // ── Main render loop ──────────────────────────────────────
    function render() {
      if (!canvas || !ctx) return;
      const st = stateRef.current;
      const v  = st.scroll;
      const W  = canvas.width;
      const H  = canvas.height;
      const px = window.devicePixelRatio || 1;

      ctx.clearRect(0, 0, W, H);

      // Background
      const fadeIn = smoothstepFn(0, 0.06, v);
      ctx.fillStyle = `rgba(8,10,15,${1})`;
      ctx.fillRect(0, 0, W, H);

      ctx.save();
      ctx.translate(W / 2, H / 2);

      // Camera: zoom + slight rotation
      const worldZoom = st.zoom * Math.min(W, H) / (GRID_SIZE * CELL);
      ctx.scale(worldZoom, worldZoom);
      ctx.rotate(st.rotZ);

      const half = GRID_SIZE * CELL * 0.5;

      // ── Grid lines ────────────────────────────────────────
      const gridAlpha = Math.min(1, fadeIn * 2) * 0.55;
      ctx.strokeStyle = `rgba(30,42,56,${gridAlpha})`;
      ctx.lineWidth = 0.5 / worldZoom;
      const step = CELL * 4;
      for (let gx = -half; gx <= half; gx += step) {
        ctx.beginPath(); ctx.moveTo(gx, -half); ctx.lineTo(gx, half); ctx.stroke();
      }
      for (let gy = -half; gy <= half; gy += step) {
        ctx.beginPath(); ctx.moveTo(-half, gy); ctx.lineTo(half, gy); ctx.stroke();
      }

      // Faint city block fills
      if (v > 0.03) {
        const blockAlpha = smoothstepFn(0.03, 0.15, v) * 0.18;
        ctx.fillStyle = `rgba(13,17,23,${blockAlpha})`;
        const bStep = CELL * 8;
        for (let bx = -half; bx < half; bx += bStep) {
          for (let by = -half; by < half; by += bStep) {
            if ((Math.floor(bx / bStep) + Math.floor(by / bStep)) % 2 === 0) {
              ctx.fillRect(bx + 1, by + 1, bStep - 2, bStep - 2);
            }
          }
        }
      }

      // ── Heatmap overlay (phase 50%+) ───────────────────────
      if (st.heatOpacity > 0) {
        const hotspots = [
          { x: half * 0.2,  y: half * 0.1,  r: 200 },
          { x: -half * 0.3, y: half * 0.25, r: 150 },
          { x: half * 0.1,  y: -half * 0.3, r: 170 },
        ];
        for (const hs of hotspots) {
          const grad = ctx.createRadialGradient(hs.x, hs.y, 0, hs.x, hs.y, hs.r);
          grad.addColorStop(0,   `rgba(198,40,40,${st.heatOpacity * 0.45})`);
          grad.addColorStop(0.4, `rgba(245,127,23,${st.heatOpacity * 0.20})`);
          grad.addColorStop(1,   'rgba(0,0,0,0)');
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(hs.x, hs.y, hs.r, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // ── Network edges ──────────────────────────────────────
      const edgeAlpha = smoothstepFn(0.2, 0.45, v) * 0.25;
      if (edgeAlpha > 0) {
        const edges = edgeIndices.current;
        const pos   = agentPositions.current;
        ctx.strokeStyle = `rgba(198,40,40,${edgeAlpha})`;
        ctx.lineWidth   = 0.4 / worldZoom;
        ctx.setLineDash([3 / worldZoom, 6 / worldZoom]);
        ctx.beginPath();
        for (let e = 0; e < 300; e++) {
          const a = edges[e * 2], b = edges[e * 2 + 1];
          ctx.moveTo(pos[a * 2], pos[a * 2 + 1]);
          ctx.lineTo(pos[b * 2], pos[b * 2 + 1]);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // ── Agent dots ─────────────────────────────────────────
      const agentAlpha = smoothstepFn(0.18, 0.35, v);
      if (agentAlpha > 0) {
        const pos  = agentPositions.current;
        const typ  = agentTypes.current;
        const n    = st.agentCount;
        const r    = 2.5 / worldZoom;

        for (let i = 0; i < n; i++) {
          const [cr, cg, cb] = typ[i] === 0 ? COLORS.suspect : typ[i] === 1 ? COLORS.lea : COLORS.witness;
          ctx.fillStyle = `rgba(${Math.round(cr * 255)},${Math.round(cg * 255)},${Math.round(cb * 255)},${agentAlpha})`;
          ctx.beginPath();
          ctx.arc(pos[i * 2], pos[i * 2 + 1], r, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // ── Phase 0–20%: random node pings ────────────────────
      if (v < 0.22 && v > 0.01) {
        const pingCount = Math.floor(smoothstepFn(0.01, 0.22, v) * 12);
        for (let p = 0; p < pingCount; p++) {
          const px2 = Math.sin(p * 2.1 + Date.now() * 0.0008) * half * 0.7;
          const py2 = Math.cos(p * 1.7 + Date.now() * 0.001)  * half * 0.7;
          const pulseR = (Date.now() % 2000) / 2000 * 40;
          const pulseA = (1 - pulseR / 40) * 0.3;
          ctx.strokeStyle = `rgba(198,40,40,${pulseA})`;
          ctx.lineWidth   = 0.5 / worldZoom;
          ctx.beginPath();
          ctx.arc(px2, py2, pulseR, 0, Math.PI * 2);
          ctx.stroke();
          // Center dot
          ctx.fillStyle = `rgba(198,40,40,0.7)`;
          ctx.beginPath();
          ctx.arc(px2, py2, 2 / worldZoom, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.restore();

      // ── Phase 80–100%: freeze overlay vignette ────────────
      const freeze = smoothstepFn(0.8, 0.95, v);
      if (freeze > 0) {
        const vig = ctx.createRadialGradient(W / 2, H / 2, H * 0.2, W / 2, H / 2, H * 0.7);
        vig.addColorStop(0, 'rgba(0,0,0,0)');
        vig.addColorStop(1, `rgba(0,0,0,${freeze * 0.55})`);
        ctx.fillStyle = vig;
        ctx.fillRect(0, 0, W, H);
      }

      // Lerp agents (faster when more scroll progress)
      tickAgents(0.025 + v * 0.035);

      // Reshuffle targets periodically
      const now = Date.now();
      const clustered = v > 0.5;
      if (v > 0.2 && (now - lastReshuffle > 4000 || clustered !== lastClustered)) {
        reshuffleTargets(clustered, v);
        lastReshuffle  = now;
        lastClustered  = clustered;
      }

      stateRef.current.frameId = requestAnimationFrame(render);
    }

    stateRef.current.frameId = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(stateRef.current.frameId);
      window.removeEventListener('resize', resize);
    };
  }, [tickAgents, reshuffleTargets]);

  // ── Sync scroll → camera state ────────────────────────────
  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    const st = stateRef.current;
    st.scroll      = v;
    st.zoom        = 1 + smoothstepFn(0.2, 0.5, v) * 1.4;
    st.rotZ        = smoothstepFn(0.5, 0.8, v) * Math.PI * 0.04;
    st.heatOpacity = smoothstepFn(0.5, 0.7, v);
    st.agentCount  = Math.floor(smoothstepFn(0.2, 0.6, v) * MAX_AGENTS);
  });

  return (
    <div className="absolute inset-0 z-0" aria-hidden="true">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
      {/* Screen-reader summary */}
      <p className="sr-only">
        Cinematic city intelligence visualization. Top-down orthographic city grid showing
        {MAX_AGENTS.toLocaleString()} simulated agents — suspects in red, law enforcement in blue,
        witnesses in grey — converging on crime hotspot zones across a procedurally generated urban grid.
        Scroll to advance through four simulation phases: boot, scan, convergence, and report ready.
      </p>
    </div>
  );
}
