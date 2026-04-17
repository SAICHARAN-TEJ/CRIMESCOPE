// sections/10-cta.js — SplitText + scale-in buttons
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function initCTA() {
  const section = document.getElementById('final-cta')
  if (!section) return

  const tl = gsap.timeline({
    scrollTrigger: { trigger: '#final-cta', start: 'top 75%' }
  })

  // Eyebrow
  tl.to('.cta-eyebrow', { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' })

  // SplitText on CTA heading
  const heading = section.querySelector('.cta-h2')
  if (heading && window.SplitText) {
    const split = new SplitText(heading, { type: 'chars, words' })
    tl.from(split.chars, {
      opacity: 0,
      y: 40,
      rotationX: -20,
      duration: 0.6,
      ease: 'power3.out',
      stagger: 0.025,
    }, '-=0.2')
  } else if (heading) {
    tl.from(heading, { opacity: 0, y: 30, duration: 0.7, ease: 'power3.out' }, '-=0.2')
  }

  // Sub
  tl.to('.cta-sub', { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }, '-=0.3')

  // Scale-in buttons
  tl.to('.cta-actions', { opacity: 1, duration: 0.4, ease: 'power2.out' }, '-=0.2')
  tl.from('.cta-actions .btn', {
    scale: 0.85,
    opacity: 0,
    duration: 0.5,
    ease: 'back.out(1.7)',
    stagger: 0.08,
  }, '-=0.3')
}
