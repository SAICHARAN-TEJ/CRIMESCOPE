// main.js — GSAP init + all section orchestrators
import './style.css'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

// Register GSAP plugins (ScrollTrigger is npm; SplitText/DrawSVG via GSAP CDN global)
gsap.registerPlugin(ScrollTrigger)

// Make GSAP + ScrollTrigger globally available for section modules
window.gsap = gsap
window.ScrollTrigger = ScrollTrigger

// Import section modules
import { initHero }          from './sections/01-hero.js'
import { initProblem }       from './sections/02-problem.js'
import { initHowItWorks }    from './sections/03-how-it-works.js'
import { initThreeModes }    from './sections/04-three-modes.js'
import { initSwarmViz }      from './sections/05-swarm-viz.js'
import { initArchetypes }    from './sections/06-archetypes.js'
import { initReportPreview } from './sections/07-report-preview.js'
import { initTargetUsers }   from './sections/08-target-users.js'
import { initDemoTeaser }    from './sections/09-demo-teaser.js'
import { initCTA }           from './sections/10-cta.js'

// Set GSAP defaults
gsap.defaults({ ease: 'power3.out', duration: 0.7 })

// Nav scroll handler
const nav = document.getElementById('cs-nav')
const onScroll = () => {
  if (!nav) return
  nav.classList.toggle('scrolled', window.scrollY > 80)
}
window.addEventListener('scroll', onScroll, { passive: true })
onScroll()

// Wait for DOM ready then init all sections
document.addEventListener('DOMContentLoaded', () => {
  // GSAP SplitText + DrawSVG ship as part of GSAP Club/CDN
  // If loaded from CDN script tags they register themselves globally
  if (window.SplitText) gsap.registerPlugin(window.SplitText)
  if (window.DrawSVGPlugin) gsap.registerPlugin(window.DrawSVGPlugin)

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

  // Refresh ScrollTrigger after all init
  ScrollTrigger.refresh()
})
