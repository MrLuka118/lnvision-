// Public portfolio: Lenis smooth scroll, the hero moment, parallax on category photos,
// a quiet reveal. Nothing moves when the visitor prefers reduced motion.
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

let lenis = null;
if (!calm && window.Lenis) {
  lenis = new window.Lenis({ autoRaf: true, lerp: 0.12 });
  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href*="#"]');
    if (!link || link.pathname !== location.pathname) return;
    const target = document.querySelector(link.hash);
    if (!target) return;
    event.preventDefault();
    lenis.scrollTo(target, { offset: -90 });
  });
}

if (!calm && window.gsap && window.ScrollTrigger) {
  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);
  lenis?.on("scroll", ScrollTrigger.update);

  const hero = document.querySelector(".pf-hero:not(.is-plain)");
  if (hero) {
    const scrub = { trigger: hero, start: "top top", end: "bottom top", scrub: true };
    gsap.to(hero.querySelector(".pf-hero-photo"), { scale: 1.08, yPercent: 8, ease: "none", scrollTrigger: scrub });
    gsap.to(hero.querySelector(".pf-hero-text"), { yPercent: -35, opacity: 0, ease: "none", scrollTrigger: scrub });
  }

  for (const photo of document.querySelectorAll(".pf-parallax")) {
    gsap.fromTo(
      photo,
      { yPercent: -6 },
      { yPercent: 6, ease: "none", scrollTrigger: { trigger: photo.parentElement, scrub: true } },
    );
  }

  document.body.classList.add("pf-reveal-ready");
  ScrollTrigger.batch(".reveal", {
    start: "top 90%",
    once: true,
    onEnter: (batch) =>
      gsap.fromTo(
        batch,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.55, ease: "power2.out", stagger: 0.06, overwrite: true },
      ),
  });
}
