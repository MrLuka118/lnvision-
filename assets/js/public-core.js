import '@fontsource-variable/fraunces';
import '@fontsource-variable/inter';
import '../css/app.css';
import { polyfillCommands, polyfillDialogLightDismiss } from '../../static/js/popover.js';
polyfillCommands();
polyfillDialogLightDismiss();
const mark = img => { if (img.naturalWidth) img.classList.add('is-loaded'); };
document.addEventListener('load', event => {
  if (event.target instanceof HTMLImageElement) mark(event.target);
}, true);
document.querySelectorAll('.photo img').forEach(mark);
// Only portfolio inquiry forms need HTMX; the delivery gallery stays lean.
if (document.querySelector('[hx-post]')) import('htmx').then(({default: htmx}) => { window.htmx = htmx; htmx.process(document.body); });
