// main.js — CrimeScope website orchestration
// Imports GSAP + ScrollTrigger from npm; CDN scripts in index.html
// are kept as fallbacks for SplitText/DrawSVG (GSAP Club plugins).
import './style.css'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

// ── Register plugins FIRST, before any module imports use them ──
gsap.registerPlugin(ScrollTrigger)

// Expose to window so CDN-loaded plugins (SplitText, DrawSVG) can register
window.gsap = gsap
window.ScrollTrigger = ScrollTrigger

// Set global GSAP defaults
gsap.defaults({ ease: 'power3.out', duration: 0.7 })

// ── Nav scroll handler ──
function initNav() {
  const nav = document.getElementById('cs-nav')
  if (!nav) return
  const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 60)
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
}

// ── Lazy-import section modules ──
async function initSections() {
  // Register any GSAP Club plugins that may have been loaded via CDN
  if (window.SplitText)     gsap.registerPlugin(window.SplitText)
  if (window.DrawSVGPlugin) gsap.registerPlugin(window.DrawSVGPlugin)

  const [
    { initHero },
    { initProblem },
    { initHowItWorks },
    { initThreeModes },
    { initSwarmViz },
    { initArchetypes },
    { initReportPreview },
    { initTargetUsers },
    { initDemoTeaser },
    { initCTA },
  ] = await Promise.all([
    import('./sections/01-hero.js'),
    import('./sections/02-problem.js'),
    import('./sections/03-how-it-works.js'),
    import('./sections/04-three-modes.js'),
    import('./sections/05-swarm-viz.js'),
    import('./sections/06-archetypes.js'),
    import('./sections/07-report-preview.js'),
    import('./sections/08-target-users.js'),
    import('./sections/09-demo-teaser.js'),
    import('./sections/10-cta.js'),
  ])

  initHero()
  initProblem()
  initHowItWorks()
  initThreeModes()
  initSwarmViz()
  initArchetypes()
  initReportPreview()
  initTargetUsers()
  initDemoTeaser()
  initCTA()

  // Final refresh after all sections are initialised
  ScrollTrigger.refresh()
}

// ── Boot ──
initNav()
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSections)
} else {
  initSections()
}
