// Popover menus anchor to their trigger with CSS anchor positioning. Browsers without it get
// the same placement computed here. Also a tiny polyfill for invoker commands (command="show-modal").

const supportsAnchor = CSS.supports("anchor-name: --a");

function place(popover) {
  const trigger = document.querySelector(`[popovertarget="${popover.id}"]`);
  if (!trigger) return;
  const gap = 8;
  const r = trigger.getBoundingClientRect();
  const p = popover.getBoundingClientRect();
  const above = popover.dataset.placement === "top";
  let top = above ? r.top - p.height - gap : r.bottom + gap;
  if (top < gap) top = r.bottom + gap;
  if (top + p.height > innerHeight - gap) top = Math.max(gap, r.top - p.height - gap);
  const left = Math.min(Math.max(gap, r.left), innerWidth - p.width - gap);
  Object.assign(popover.style, { position: "fixed", inset: "auto", top: `${top}px`, left: `${left}px` });
}

export function initPopovers() {
  if (supportsAnchor) return;
  document.addEventListener(
    "toggle",
    (event) => {
      const el = event.target;
      if (el instanceof HTMLElement && el.matches("[popover]") && event.newState === "open") {
        place(el);
      }
    },
    true,
  );
}

export function polyfillCommands() {
  if ("command" in HTMLButtonElement.prototype) return;
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button[commandfor][command]");
    if (!button) return;
    const target = document.getElementById(button.getAttribute("commandfor"));
    const command = button.getAttribute("command");
    if (target instanceof HTMLDialogElement) {
      if (command === "show-modal") target.showModal();
      if (command === "close") target.close();
    }
  });
}
