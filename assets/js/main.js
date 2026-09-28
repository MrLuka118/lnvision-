import '@fontsource-variable/fraunces';
import '@fontsource-variable/inter';
import '../css/app.css';
import '../../static/js/app.js';

const reduced = matchMedia('(prefers-reduced-motion: reduce)');
document.addEventListener('htmx:beforeTransition', event => {
  if (reduced.matches) event.preventDefault();
  document.documentElement.classList.toggle('partial-transition', !event.detail.boosted);
});
document.addEventListener('htmx:afterSettle', event => {
  if (event.detail.target === document.body) {
    const main = document.getElementById('main');
    main?.setAttribute('tabindex', '-1');
    main?.focus({ preventScroll: true });
  }
});

let financeModule;
async function charts() {
  if (!document.getElementById('finance-chart') && !financeModule) return;
  financeModule ??= await import('./finance.js');
  financeModule.initFinance();
}
charts();
document.addEventListener('htmx:afterSettle', charts);

// Public pages and the calendar own their page modules and use native document navigation.
document.addEventListener('htmx:beforeRequest', event => {
  if (!event.detail.boosted) return;
  const link = event.detail.elt.closest('a');
  if (link && /^\/(koledar|g|p|racun)\//.test(new URL(link.href).pathname)) {
    event.preventDefault(); location.assign(link.href);
  }
});
