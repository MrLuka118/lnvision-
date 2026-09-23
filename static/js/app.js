// Entry point. Every dependency is resolved through the import map in base.html.
import htmx from "htmx";
import Alpine from "alpine";
import { registerComponents } from "app/components";
import { initRefraction } from "app/refraction";
import { initPopovers, polyfillCommands, polyfillDialogLightDismiss } from "app/popover";
import { initActions } from "app/actions";

window.htmx = htmx;
window.Alpine = Alpine;

registerComponents(Alpine);
Alpine.start();

initRefraction();
initPopovers();
polyfillCommands();
polyfillDialogLightDismiss();
initActions();

htmx.on("htmx:afterSettle", (event) => initRefraction(event.target));

// Fade photos in over their blurred placeholder once they have loaded.
const markLoaded = (img) => img.classList.add("is-loaded");
document.addEventListener(
  "load",
  (event) => {
    if (event.target instanceof HTMLImageElement && event.target.closest(".photo")) {
      markLoaded(event.target);
    }
  },
  true,
);
for (const img of document.querySelectorAll(".photo img")) {
  if (img.complete && img.naturalWidth) markLoaded(img);
}
htmx.on("htmx:afterSettle", (event) => {
  for (const img of event.target.querySelectorAll(".photo img")) {
    if (img.complete && img.naturalWidth) markLoaded(img);
  }
});

// Don't swap the photo grid away from under an open photo menu.
htmx.on("htmx:beforeRequest", (event) => {
  const grid = event.detail.elt;
  if (grid.id === "photo-grid" && grid.querySelector(":popover-open")) event.preventDefault();
});
