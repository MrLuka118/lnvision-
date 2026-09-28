import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import { Flip } from 'gsap/Flip';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import 'photoswipe/style.css';
gsap.registerPlugin(ScrollTrigger, SplitText, Flip);
Object.assign(window, { gsap, ScrollTrigger, SplitText, Flip, Lenis });
if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.fonts.ready.then(() => {
    const heading = document.querySelector('.g-cover h1, .pf-hero h1');
    if (heading) SplitText.create(heading, { type: 'words', autoSplit: true, onSplit(self) {
      return gsap.from(self.words, { opacity: 0, y: 12, duration: .48, stagger: .025, ease: 'power3.out' });
    }});
  });
}
