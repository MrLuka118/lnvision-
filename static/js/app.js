// Entry point. Every dependency is resolved through the import map in base.html.
import htmx from "htmx";
import Alpine from "alpine";
import { registerComponents } from "app/components";
import { initRefraction } from "app/refraction";
import { initPopovers, polyfillCommands } from "app/popover";

window.htmx = htmx;
window.Alpine = Alpine;

registerComponents(Alpine);
Alpine.start();

initRefraction();
initPopovers();
polyfillCommands();

htmx.on("htmx:afterSettle", (event) => initRefraction(event.target));
