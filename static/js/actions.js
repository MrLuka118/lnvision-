// Confirmation and pending state for everything that changes data.
//
// Confirm: `hx-confirm="Question?"` on an HTMX element, or `data-confirm="Question?"` on a plain
// form or its submit button, opens the shared #confirm-dialog (partials/confirm_dialog.html)
// instead of the browser's confirm(). Optional `data-confirm-detail` and `data-confirm-label`
// fill in the explanation and the confirm button's label.
//
// Pending: the button (or menu item) that started a request gets aria-busy until the response
// arrives, and a plain POST form can't be submitted twice. The look lives in components.css.

import htmx from "htmx";

function ask({ question, detail, label }) {
  const dialog = document.getElementById("confirm-dialog");
  if (!dialog) return Promise.resolve(window.confirm(question));
  const ok = dialog.querySelector("[data-confirm-ok]");
  dialog.querySelector("[data-confirm-title]").textContent = question;
  const body = dialog.querySelector("[data-confirm-body]");
  body.textContent = detail || "";
  body.hidden = !detail;
  ok.textContent = label || ok.dataset.defaultLabel;
  dialog.returnValue = "";
  dialog.showModal();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
  });
}

const optionsFrom = (el, question) => ({
  question,
  detail: el.dataset.confirmDetail,
  label: el.dataset.confirmLabel,
});

// ------------------------------------------------------------------ pending
const busy = new WeakMap(); // request source element -> the element showing the pending state

function setBusy(el, on) {
  if (!el) return;
  if (on) {
    el.setAttribute("aria-busy", "true");
  } else {
    el.removeAttribute("aria-busy");
  }
}

// The control the person actually pressed: the submitter of a form, or the element itself.
function pressedControl(elt, triggeringEvent) {
  if (!triggeringEvent || !["click", "submit"].includes(triggeringEvent.type)) return null;
  if (triggeringEvent.submitter) return triggeringEvent.submitter;
  if (elt.matches("button, .menu-item, .action-link, [role=button]")) return elt;
  if (elt instanceof HTMLFormElement) return elt.querySelector("button:not([type=button])") || elt;
  return null;
}

export function initActions() {
  htmx.on("htmx:confirm", (event) => {
    const { question, elt } = event.detail;
    if (!question) return;
    event.preventDefault();
    ask(optionsFrom(elt, question)).then((ok) => ok && event.detail.issueRequest(true));
  });

  htmx.on("htmx:beforeRequest", (event) => {
    const control = pressedControl(event.detail.elt, event.detail.requestConfig?.triggeringEvent);
    if (!control) return;
    busy.set(event.detail.elt, control);
    setBusy(control, true);
  });
  htmx.on("htmx:afterRequest", (event) => {
    setBusy(busy.get(event.detail.elt), false);
    busy.delete(event.detail.elt);
  });

  // Plain forms. Capture phase, so a declined confirmation never reaches other handlers.
  document.addEventListener(
    "submit",
    (event) => {
      const form = event.target;
      const submitter = event.submitter;
      const source = submitter?.dataset.confirm ? submitter : form.dataset.confirm ? form : null;
      if (!source || form.dataset.confirmed) return;
      event.preventDefault();
      event.stopPropagation();
      ask(optionsFrom(source, source.dataset.confirm)).then((ok) => {
        if (!ok) return;
        form.dataset.confirmed = "true";
        form.requestSubmit(submitter);
        delete form.dataset.confirmed;
      });
    },
    true,
  );

  // Bubble phase on window: runs after every other handler has had its say.
  window.addEventListener("submit", (event) => {
    const form = event.target;
    if (event.defaultPrevented || form.method !== "post") return;
    if (form.closest("[hx-post], [hx-get], [hx-boost]") || form.matches("[hx-post], [hx-get]")) return;
    if (form.dataset.pending) {
      event.preventDefault(); // second click while the first submit is on its way
      return;
    }
    form.dataset.pending = "true";
    setBusy(event.submitter?.classList.contains("btn") ? event.submitter : form, true);
  });

  // Back/forward cache: a restored page must not keep its buttons spinning.
  window.addEventListener("pageshow", (event) => {
    if (!event.persisted) return;
    for (const form of document.querySelectorAll("form[data-pending]")) delete form.dataset.pending;
    for (const el of document.querySelectorAll("[aria-busy=true]")) setBusy(el, false);
  });
}
