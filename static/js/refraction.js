// Liquid Glass refraction for the few elements marked data-refract (navigation bars).
//
// Builds an SVG displacement map shaped like the element's rounded rectangle: the backdrop is
// pulled inwards along a narrow bezel, like light bending through the rim of a glass lens.
// Chromium is the only engine that applies SVG filters in backdrop-filter; everywhere else the
// element keeps the plain blur from glass.css.

const NS = "http://www.w3.org/2000/svg";
const BEZEL = 18; // px of the edge that bends light
const STRENGTH = 42; // px of maximum displacement

const supported =
  Boolean(navigator.userAgentData?.brands?.some((b) => b.brand === "Chromium")) &&
  !matchMedia("(prefers-reduced-transparency: reduce)").matches;

let defs;
let counter = 0;

function ensureDefs() {
  if (defs) return defs;
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.style.position = "absolute";
  defs = document.createElementNS(NS, "defs");
  svg.append(defs);
  document.body.append(svg);
  return defs;
}

/** Displacement map for a w×h rounded rect of radius r (R = x shift, G = y shift, 128 = none). */
function buildMap(w, h, r) {
  const scale = 0.5;
  const cw = Math.max(1, Math.round(w * scale));
  const ch = Math.max(1, Math.round(h * scale));
  const canvas = document.createElement("canvas");
  canvas.width = cw;
  canvas.height = ch;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(cw, ch);
  const hx = w / 2;
  const hy = h / 2;
  for (let j = 0; j < ch; j++) {
    for (let i = 0; i < cw; i++) {
      const px = (i + 0.5) / scale - hx;
      const py = (j + 0.5) / scale - hy;
      const qx = Math.abs(px) - (hx - r);
      const qy = Math.abs(py) - (hy - r);
      const ox = Math.max(qx, 0);
      const oy = Math.max(qy, 0);
      const outside = Math.hypot(ox, oy) + Math.min(Math.max(qx, qy), 0) - r;
      const depth = -outside; // distance from the edge, inside the shape
      let dx = 0;
      let dy = 0;
      if (depth > 0 && depth < BEZEL) {
        // Circular lens profile: steep at the rim, flat towards the middle.
        const t = 1 - depth / BEZEL;
        const mag = 1 - Math.sqrt(1 - t * t);
        let nx;
        let ny;
        if (qx > 0 && qy > 0) {
          const len = Math.hypot(ox, oy) || 1;
          nx = ox / len;
          ny = oy / len;
        } else if (qx > qy) {
          nx = 1;
          ny = 0;
        } else {
          nx = 0;
          ny = 1;
        }
        dx = -Math.sign(px) * nx * mag;
        dy = -Math.sign(py) * ny * mag;
      }
      const k = (j * cw + i) * 4;
      img.data[k] = 128 + dx * 127;
      img.data[k + 1] = 128 + dy * 127;
      img.data[k + 2] = 128;
      img.data[k + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return canvas.toDataURL();
}

function attach(el) {
  if (el.dataset.refractId) return;
  const id = `refract-${++counter}`;
  el.dataset.refractId = id;

  const filter = document.createElementNS(NS, "filter");
  filter.id = id;
  filter.setAttribute("color-interpolation-filters", "sRGB");
  filter.setAttribute("x", "0");
  filter.setAttribute("y", "0");
  filter.setAttribute("width", "100%");
  filter.setAttribute("height", "100%");
  const image = document.createElementNS(NS, "feImage");
  image.setAttribute("x", "0");
  image.setAttribute("y", "0");
  image.setAttribute("preserveAspectRatio", "none");
  image.setAttribute("result", "map");
  const displace = document.createElementNS(NS, "feDisplacementMap");
  displace.setAttribute("in", "SourceGraphic");
  displace.setAttribute("in2", "map");
  displace.setAttribute("scale", String(STRENGTH));
  displace.setAttribute("xChannelSelector", "R");
  displace.setAttribute("yChannelSelector", "G");
  filter.append(image, displace);
  ensureDefs().append(filter);

  const update = () => {
    const { width, height } = el.getBoundingClientRect();
    if (!width || !height) return;
    const style = getComputedStyle(el);
    const radius = Math.min(Number.parseFloat(style.borderTopLeftRadius) || 0, width / 2, height / 2);
    image.setAttribute("width", String(width));
    image.setAttribute("height", String(height));
    image.setAttribute("href", buildMap(width, height, radius));
    const blur = style.getPropertyValue("--glass-blur").trim() || "24px";
    const sat = style.getPropertyValue("--glass-sat").trim() || "180%";
    const lum = style.getPropertyValue("--glass-lum").trim() || "";
    el.style.backdropFilter = `url(#${id}) blur(${blur}) saturate(${sat}) ${lum}`;
  };
  new ResizeObserver(update).observe(el);
}

export function initRefraction(root = document) {
  if (!supported) return;
  document.documentElement.classList.add("has-refraction");
  for (const el of root.querySelectorAll("[data-refract]")) attach(el);
}
