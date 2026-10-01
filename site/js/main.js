import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);
const still = location.search.includes("still"); // static mode for full-page screenshots
const reduce = still || matchMedia("(prefers-reduced-motion: reduce)").matches;
if (still) document.documentElement.classList.add("still");
const root = document.documentElement;
root.classList.add("motion");
document.getElementById("y").textContent = new Date().getFullYear();

/* ---------- Smooth scrolling ---------- */
let lenis = null;
if (!reduce) {
  lenis = new Lenis({ duration: 1.15, easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)) });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((time) => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);
}
document.querySelectorAll('a[href^="#"]').forEach((a) => {
  a.addEventListener("click", (e) => {
    const id = a.getAttribute("href");
    const el = id.length > 1 && document.querySelector(id);
    if (!el) return;
    e.preventDefault();
    lenis ? lenis.scrollTo(el, { offset: 0, duration: 1.4 }) : el.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  });
});

/* ---------- Nav: clear over the hero, frosted after ---------- */
const nav = document.getElementById("nav");
const hero = document.getElementById("hero");
ScrollTrigger.create({
  start: 0, end: "max",
  onUpdate: (self) => nav.classList.toggle("scrolled", self.scroll() > hero.offsetHeight - 80),
});

/* ---------- Text splitting (words masked, letters rise) ---------- */
function split(el, { chars = true, mask = true } = {}) {
  const out = [];
  const walk = (node) => {
    [...node.childNodes].forEach((n) => {
      if (n.nodeType === 3) {
        const frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach((part) => {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(" ")); return; }
          const word = document.createElement("span");
          word.className = "w";
          if (chars) {
            for (const ch of part) {
              const c = document.createElement("span");
              c.className = "c";
              c.textContent = ch;
              word.appendChild(c);
              out.push(c);
            }
          } else {
            word.textContent = part;
            out.push(word);
          }
          if (mask) {
            const m = document.createElement("span");
            m.className = "wm";
            m.appendChild(word);
            frag.appendChild(m);
          } else frag.appendChild(word);
        });
        n.replaceWith(frag);
      } else if (n.nodeType === 1 && n.classList.contains("inline")) {
        out.push(n);
      } else if (n.nodeType === 1 && n.tagName !== "BR") {
        walk(n);
      }
    });
  };
  walk(el);
  el.setAttribute("aria-label", el.textContent.replace(/\s+/g, " ").trim());
  return out;
}

document.fonts.ready.then(() => {
  /* Hero title: letters rise out of their masks */
  const heroTitle = document.getElementById("hero-title");
  const heroChars = split(heroTitle);
  const intro = gsap.timeline({ delay: 0.15 });
  if (!reduce) {
    intro.from(heroChars, { yPercent: 115, rotate: 6, duration: 1.3, ease: "expo.out", stagger: 0.035 })
      .from("[data-hero-fade]", { y: 22, opacity: 0, duration: 1.1, ease: "expo.out", stagger: 0.09 }, 0.55);
  }

  /* Section headlines */
  document.querySelectorAll("[data-split]").forEach((el) => {
    const chars = split(el);
    if (reduce) return;
    gsap.from(chars, {
      yPercent: 115, duration: 1.15, ease: "expo.out", stagger: 0.016,
      scrollTrigger: { trigger: el, start: "top 86%" },
    });
  });

  /* Statement: words light up as you read */
  document.querySelectorAll("[data-scrub]").forEach((el) => {
    const words = split(el, { chars: false, mask: false });
    words.forEach((w) => w.classList.add("word"));
    if (reduce) return;
    gsap.to(words, {
      opacity: 1, ease: "none", stagger: 0.12,
      scrollTrigger: { trigger: el, start: "top 78%", end: "bottom 42%", scrub: 0.6 },
    });
  });

  ScrollTrigger.refresh();
});

/* ---------- Reveals ---------- */
if (!reduce) {
  ScrollTrigger.batch("[data-reveal]", {
    start: "top 90%",
    onEnter: (els) => gsap.to(els, { opacity: 1, y: 0, duration: 1.2, ease: "expo.out", stagger: 0.08, overwrite: true }),
  });
} else {
  gsap.set("[data-reveal]", { opacity: 1, y: 0 });
}

/* ---------- 3D hero ---------- */
const canvas = document.getElementById("island");
const skyButtons = [...document.querySelectorAll("[data-sky]")];
const skyLabel = document.getElementById("sky-label");
let heroApi = null;
import("./hero3d.js")
  .then(({ createHero, skyForHour }) => {
    const now = new URLSearchParams(location.search).get("sky") || skyForHour(new Date().getHours());
    const mark = (name) => skyButtons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sky === name)));
    mark(now);
    return createHero(canvas, { reduce }).then((api) => {
      heroApi = api;
      skyButtons.forEach((b) => b.addEventListener("click", () => {
        api.setSky(b.dataset.sky);
        mark(b.dataset.sky);
        skyLabel.textContent = b.dataset.sky === now ? "Your sky, right now" : `Previewing ${b.dataset.sky}`;
      }));
    });
  })
  .catch((err) => {
    console.warn("3D hero unavailable", err);
    hero.classList.add("no-webgl");
  });

if (!reduce) {
  gsap.to(".hero .copy", {
    yPercent: -22, opacity: 0, ease: "none",
    scrollTrigger: { trigger: hero, start: "top top", end: "bottom top", scrub: true },
  });
  ScrollTrigger.create({
    trigger: hero, start: "top top", end: "bottom top", scrub: true,
    onUpdate: (s) => heroApi?.setScroll(s.progress),
  });
}

/* ---------- Showcase: the sticky iPhone follows the story ---------- */
const steps = [...document.querySelectorAll(".showcase .step")];
const screens = [...document.querySelectorAll(".showcase .stage img")];
const halo = document.getElementById("halo");
const halos = [
  "linear-gradient(120deg, #ffd36e, #f6a04a, #f0707e)",
  "linear-gradient(120deg, #b5ef8f, #5bb865)",
  "linear-gradient(120deg, #8fd0ff, #7d8cff)",
  "linear-gradient(120deg, #7b6cff, #1d2a6e)",
];
function showStep(i) {
  steps.forEach((s, k) => s.classList.toggle("active", k === i));
  screens.forEach((m, k) => m.classList.toggle("on", k === i));
  if (halo) halo.style.background = halos[i];
}
steps.forEach((step, i) => {
  ScrollTrigger.create({
    trigger: step, start: "top 55%", end: "bottom 55%",
    onToggle: (self) => { if (self.isActive) showStep(i); },
  });
});

/* ---------- Micro-interactions ---------- */
if (!reduce && matchMedia("(hover: hover)").matches) {
  document.querySelectorAll("[data-magnetic]").forEach((el) => {
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      gsap.to(el, { x: (e.clientX - r.left - r.width / 2) * 0.22, y: (e.clientY - r.top - r.height / 2) * 0.3, duration: 0.6, ease: "power3.out" });
    });
    el.addEventListener("pointerleave", () => gsap.to(el, { x: 0, y: 0, duration: 0.9, ease: "elastic.out(1, 0.4)" }));
  });
  document.querySelectorAll("[data-tilt]").forEach((el) => {
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
      gsap.to(el, { rotateY: px * 5, rotateX: -py * 5, transformPerspective: 1000, duration: 0.8, ease: "power3.out" });
    });
    el.addEventListener("pointerleave", () => gsap.to(el, { rotateY: 0, rotateX: 0, duration: 1, ease: "power3.out" }));
  });
}

/* ---------- FAQ: smooth open/close ---------- */
document.querySelectorAll(".faq details").forEach((d) => {
  const summary = d.querySelector("summary");
  const answer = d.querySelector(".answer");
  summary.addEventListener("click", (e) => {
    if (reduce) return;
    e.preventDefault();
    if (d.open) {
      gsap.to(answer, { height: 0, duration: 0.5, ease: "power3.inOut", onComplete: () => { d.open = false; gsap.set(answer, { clearProps: "height" }); } });
    } else {
      d.open = true;
      gsap.from(answer, { height: 0, duration: 0.6, ease: "power3.out", clearProps: "height" });
    }
  });
});
