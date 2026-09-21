// The client's gallery: smooth scroll, the cover moment, the lightbox, favourites, ZIP, notes.
import PhotoSwipeLightbox from "photoswipe/lightbox";

const config = JSON.parse(document.getElementById("gallery-config").textContent);
const csrf = JSON.parse(document.body.getAttribute("hx-headers") || "{}")["X-CSRFToken"];
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
const main = document.getElementById("photos");
const urlFor = (name, uuid) => config.urls[name].replace(config.placeholder, uuid);

async function post(url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
    body: JSON.stringify(body),
  });
  let data = {};
  try {
    data = await response.json();
  } catch {
    // 204 and friends
  }
  return { ok: response.ok, status: response.status, data };
}

function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(ns, "use");
  use.setAttribute("href", `${config.sprite}#${name}`);
  svg.append(use);
  return svg;
}

// --- motion: Lenis on this public page, one orchestrated cover moment, a quiet reveal -------

let lenis = null;
if (!calm && window.Lenis) {
  lenis = new window.Lenis({ autoRaf: true, lerp: 0.12 });
}
if (!calm && window.gsap && window.ScrollTrigger) {
  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);
  lenis?.on("scroll", ScrollTrigger.update);

  const cover = document.querySelector(".g-cover");
  if (cover) {
    const scrub = { trigger: cover, start: "top top", end: "bottom top", scrub: true };
    gsap.to(".g-cover-photo", { scale: 1.08, yPercent: 8, ease: "none", scrollTrigger: scrub });
    gsap.to(".g-cover-text", { yPercent: -30, opacity: 0, ease: "none", scrollTrigger: scrub });
  }

  document.body.classList.add("g-reveal-ready");
  ScrollTrigger.batch(".reveal", {
    start: "top 92%",
    once: true,
    onEnter: (batch) =>
      gsap.fromTo(
        batch,
        { opacity: 0, y: 12 },
        { opacity: 1, y: 0, duration: 0.45, ease: "power2.out", stagger: 0.04, overwrite: true },
      ),
  });
}

// In-page links (chapters, "to the photos") glide with Lenis when it's running.
document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (!link || !lenis) return;
  const target = document.querySelector(link.getAttribute("href"));
  if (!target) return;
  event.preventDefault();
  lenis.scrollTo(target, { offset: -80 });
});

// --- who is choosing -----------------------------------------------------------------------

const identifyDialog = document.getElementById("g-identify");
let afterIdentify = null;

function askName(then) {
  afterIdentify = then;
  identifyDialog.showModal();
}

identifyDialog?.querySelector("form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const error = form.querySelector("[data-error]");
  const { ok, data } = await post(config.urls.identify, {
    name: form.name.value,
    email: form.email.value,
  });
  if (!ok) {
    error.textContent = data.error || config.labels.failed;
    error.hidden = false;
    return;
  }
  config.known = true;
  const zipEmail = document.getElementById("g-zip-email");
  if (zipEmail && !zipEmail.value) zipEmail.value = form.email.value;
  identifyDialog.close();
  afterIdentify?.();
  afterIdentify = null;
});

// --- favourites ----------------------------------------------------------------------------

const counter = document.querySelector("[data-favorite-count]");

function markFavorite(uuid, on) {
  const tile = main.querySelector(`.g-tile[data-uuid="${uuid}"]`);
  tile?.classList.toggle("is-favorite", on);
  const button = tile?.querySelector("[data-heart]");
  if (button) {
    button.setAttribute("aria-pressed", String(on));
    button.classList.remove("is-popping");
    if (on && !calm) {
      void button.offsetWidth;
      button.classList.add("is-popping");
    }
  }
  const pswpHeart = document.querySelector(".pswp__button--heart");
  if (pswpHeart && lightbox.pswp?.currSlide?.data.uuid === uuid) {
    pswpHeart.setAttribute("aria-pressed", String(on));
  }
  updateFavoritesFilter();
}

async function toggleFavorite(uuid) {
  if (!config.known) {
    askName(() => toggleFavorite(uuid));
    return;
  }
  const wasOn = main.querySelector(`.g-tile[data-uuid="${uuid}"]`)?.classList.contains("is-favorite");
  markFavorite(uuid, !wasOn); // optimistic
  const { ok, status, data } = await post(urlFor("favorite", uuid));
  if (status === 403 && data.needsName) {
    config.known = false;
    markFavorite(uuid, wasOn);
    askName(() => toggleFavorite(uuid));
    return;
  }
  if (!ok) {
    markFavorite(uuid, wasOn);
    return;
  }
  markFavorite(uuid, data.favorite);
  if (counter) counter.textContent = data.count;
}

main.addEventListener("click", (event) => {
  const heart = event.target.closest("[data-heart]");
  if (heart) toggleFavorite(heart.dataset.heart);
});

const filterButton = document.querySelector("[data-show-favorites]");
const emptyFavorites = document.querySelector("[data-empty-favorites]");

function updateFavoritesFilter() {
  const on = document.body.classList.contains("show-favorites");
  const any = main.querySelector(".g-tile.is-favorite");
  if (emptyFavorites) emptyFavorites.hidden = !on || Boolean(any);
  for (const section of main.querySelectorAll(".g-section")) {
    section.hidden = on && !section.querySelector(".g-tile.is-favorite");
  }
}

filterButton?.addEventListener("click", () => {
  const on = document.body.classList.toggle("show-favorites");
  filterButton.setAttribute("aria-pressed", String(on));
  lightbox.options.children = on ? ".g-tile.is-favorite .g-link" : ".g-tile .g-link";
  updateFavoritesFilter();
  window.ScrollTrigger?.refresh();
  if (on) (lenis ? lenis.scrollTo(main, { offset: -80 }) : main.scrollIntoView());
});

// --- notes ---------------------------------------------------------------------------------

const commentDialog = document.getElementById("g-comment");
let commentPhoto = null;

function openComment(uuid = null) {
  if (!config.known) {
    askName(() => openComment(uuid));
    return;
  }
  commentPhoto = uuid;
  commentDialog.querySelector("[data-status]").textContent = "";
  commentDialog.showModal();
}

commentDialog?.querySelector("form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const status = form.querySelector("[data-status]");
  const { ok, data } = await post(config.urls.comment, { body: form.body.value, photo: commentPhoto });
  if (!ok) {
    status.textContent = data.error || config.labels.failed;
    return;
  }
  form.reset();
  status.textContent = config.labels.sent;
  setTimeout(() => commentDialog.close(), 900);
});

// --- ZIP -----------------------------------------------------------------------------------

const zipDialog = document.getElementById("g-zip");
zipDialog?.querySelector("form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const status = form.querySelector("[data-status]");
  const link = form.querySelector("[data-zip-link]");
  const submit = form.querySelector("[data-zip-submit]");
  submit.disabled = true;
  const size = form.querySelector('[name="size"]:checked, [name="size"][type="hidden"]').value;
  let { ok, data } = await post(config.urls.zip, { size, email: form.email.value });
  if (!ok) {
    status.textContent = data.error || config.labels.failed;
    submit.disabled = false;
    return;
  }
  status.textContent = config.labels.preparing;
  while (data.status !== "ready" && data.status !== "failed") {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    data = await fetch(data.statusUrl).then((r) => r.json()).catch(() => ({ status: "failed" }));
  }
  if (data.status === "failed") {
    status.textContent = config.labels.failed;
    submit.disabled = false;
    return;
  }
  status.textContent = config.labels.ready;
  link.href = data.url;
  link.hidden = false;
  submit.hidden = true;
});

// --- lightbox ------------------------------------------------------------------------------

const seen = new Set();

const lightbox = new PhotoSwipeLightbox({
  gallery: "#photos",
  children: ".g-tile .g-link",
  pswpModule: () => import("photoswipe"),
  bgOpacity: 1,
  showHideAnimationType: calm ? "none" : "zoom",
  wheelToZoom: true,
  closeTitle: config.labels.close,
  arrowPrevTitle: config.labels.previous,
  arrowNextTitle: config.labels.next,
  zoomTitle: "",
  paddingFn: (viewport) => (viewport.x < 640 ? { top: 70, bottom: 20, left: 0, right: 0 } : { top: 80, bottom: 40, left: 70, right: 70 }),
});

lightbox.addFilter("itemData", (itemData) => {
  const el = itemData.element;
  if (el) {
    itemData.uuid = el.dataset.uuid;
    itemData.bright = el.dataset.bright === "1";
    itemData.name = el.dataset.name;
  }
  return itemData;
});

lightbox.on("uiRegister", () => {
  const { pswp } = lightbox;
  const button = (name, order, iconName, title, onClick) =>
    pswp.ui.registerElement({
      name,
      order,
      isButton: true,
      title,
      html: "",
      onInit: (el) => el.append(icon(iconName)),
      onClick,
    });

  if (config.favorites) {
    pswp.ui.registerElement({
      name: "heart",
      order: 8,
      isButton: true,
      title: config.labels.favorite,
      onInit: (el) => {
        el.append(icon("heart"));
        pswp.on("change", () => {
          const on = main
            .querySelector(`.g-tile[data-uuid="${pswp.currSlide.data.uuid}"]`)
            ?.classList.contains("is-favorite");
          el.setAttribute("aria-pressed", String(Boolean(on)));
        });
      },
      onClick: () => toggleFavorite(pswp.currSlide.data.uuid),
    });
  }
  if (config.comments) {
    button("comment", 9, "message-circle", config.labels.comment, () =>
      openComment(pswp.currSlide.data.uuid),
    );
  }
  if (config.web || config.original) {
    const size = config.web ? "web" : "original";
    button("download", 10, "download", config.labels.download, () => {
      window.location.href = `${urlFor("download", pswp.currSlide.data.uuid)}?velikost=${size}`;
    });
  }
});

lightbox.on("change", () => {
  const { pswp } = lightbox;
  const { uuid, bright } = pswp.currSlide.data;
  pswp.element.dataset.dim = bright ? "1" : "0";
  history.replaceState(null, "", `?foto=${uuid}`);
  if (!seen.has(uuid)) {
    seen.add(uuid);
    fetch(urlFor("seen", uuid), { method: "POST", headers: { "X-CSRFToken": csrf }, keepalive: true });
  }
});
lightbox.on("beforeOpen", () => lenis?.stop());
lightbox.on("close", () => {
  lenis?.start();
  history.replaceState(null, "", location.pathname);
});
lightbox.init();

// Deep link: /g/<token>/?foto=<uuid> opens that photo.
if (config.open) {
  const links = [...main.querySelectorAll(".g-link")];
  const index = links.findIndex((link) => link.dataset.uuid === config.open);
  if (index >= 0) lightbox.loadAndOpen(index, { gallery: main });
}
