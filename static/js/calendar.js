// Calendar page: FullCalendar v7 (global build, loaded with defer before this module),
// our own toolbar, event popovers and dialogs loaded with HTMX.

const config = JSON.parse(document.getElementById("calendar-config").textContent);
const el = document.getElementById("calendar");
const title = document.getElementById("cal-title");
const popover = document.getElementById("event-popover");
const dialog = document.getElementById("event-dialog");
const dialogBody = document.getElementById("event-dialog-body");
const csrf = JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"];
const compact = matchMedia("(max-width: 40rem)");
const VIEW_KEY = "aperture.calendar.view";

function storedView() {
  try {
    return localStorage.getItem(VIEW_KEY);
  } catch {
    return null;
  }
}

function rememberView(view) {
  try {
    localStorage.setItem(VIEW_KEY, view);
  } catch {
    // Private mode: the view just isn't remembered.
  }
}

/** Our event chip: a colour bar for the type, neutral text. Built with DOM APIs, never HTML. */
function eventContent(arg) {
  const { colour, tentative, client } = arg.event.extendedProps;
  const chip = document.createElement("div");
  chip.className = "cal-event" + (tentative ? " is-tentative" : "");
  if (arg.view.type.startsWith("timeGrid")) chip.classList.add("is-tall");
  chip.style.setProperty("--dot", colour);
  if (arg.timeText && !arg.event.allDay) {
    const time = document.createElement("span");
    time.className = "cal-event-time";
    time.textContent = arg.timeText;
    chip.append(time);
  }
  const name = document.createElement("span");
  name.className = "cal-event-title";
  name.textContent = arg.event.title;
  chip.append(name);
  if (client && client !== arg.event.title && arg.view.type.startsWith("list")) {
    const who = document.createElement("span");
    who.className = "cal-event-meta";
    who.textContent = client;
    chip.append(who);
  }
  return { domNodes: [chip] };
}

async function move(info) {
  const url = config.moveUrl.replace("/0/", `/${info.event.id}/`);
  const body = { start: info.event.startStr, end: info.event.endStr || null, allDay: info.event.allDay };
  try {
    const response = await fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(String(response.status));
  } catch {
    info.revert();
  }
}

function openDialog(url) {
  popover.hidePopover?.();
  return window.htmx.ajax("GET", url, { target: dialogBody, swap: "innerHTML" }).then(() => {
    if (!dialog.open) dialog.showModal();
  });
}

let anchored;
function openPopover(info) {
  const url = config.detailUrl.replace("/0/", `/${info.event.id}/`);
  if (compact.matches) {
    return openDialog(url);
  }
  anchored?.style.removeProperty("anchor-name");
  anchored = info.el;
  anchored.style.setProperty("anchor-name", "--event-anchor");
  return window.htmx.ajax("GET", url, { target: popover, swap: "innerHTML" }).then(() => {
    if (!popover.matches(":popover-open")) popover.showPopover();
    if (!CSS.supports("anchor-name: --a")) {
      const r = info.el.getBoundingClientRect();
      const p = popover.getBoundingClientRect();
      const top = r.bottom + 8 + p.height > innerHeight ? r.top - p.height - 8 : r.bottom + 8;
      const left = Math.min(Math.max(8, r.left), innerWidth - p.width - 8);
      Object.assign(popover.style, { position: "fixed", inset: "auto", top: `${top}px`, left: `${left}px` });
    }
  });
}

function createUrl(start, end, allDay) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  if (allDay !== undefined) params.set("allDay", String(allDay));
  return `${config.createUrl}?${params}`;
}

const calendar = new FullCalendar.Calendar(el, {
  locale: "sl",
  firstDay: 1,
  initialView: storedView() || (compact.matches ? "listWeek" : "dayGridMonth"),
  headerToolbar: false,
  height: "auto",
  editable: true,
  selectable: true,
  selectMirror: true,
  dayMaxEvents: 3,
  eventDisplay: "block",
  nowIndicator: true,
  weekNumbers: false,
  slotMinTime: "07:00:00",
  slotMaxTime: "22:00:00",
  scrollTime: "08:00:00",
  eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
  events: { url: config.feedUrl },
  eventContent,
  eventDrop: move,
  eventResize: move,
  eventClick(info) {
    info.jsEvent.preventDefault();
    const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!document.startViewTransition || calm) { openPopover(info); return; }
    document.querySelectorAll('[style*="view-transition-name: calendar-event"]').forEach(el => el.style.viewTransitionName = 'none');
    const title = info.el.querySelector('.cal-event-title');
    if (title) title.style.viewTransitionName = 'calendar-event';
    const transition = document.startViewTransition(async () => {
      if (title) title.style.viewTransitionName = 'none';
      await openPopover(info);
    });
    transition.ready.catch(() => {});
  },
  select(info) {
    openDialog(createUrl(info.startStr, info.endStr, info.allDay));
    calendar.unselect();
  },
  datesSet(info) {
    const text = info.view.title;
    title.textContent = text.charAt(0).toLocaleUpperCase("sl") + text.slice(1);
    for (const input of document.querySelectorAll('input[name="cal-view"]')) {
      input.checked = input.value === info.view.type;
    }
  },
});
calendar.render();

document.querySelector('[data-cal="prev"]').addEventListener("click", () => calendar.prev());
document.querySelector('[data-cal="next"]').addEventListener("click", () => calendar.next());
document.querySelector('[data-cal="today"]').addEventListener("click", () => calendar.today());
document.querySelector('[data-cal="new"]').addEventListener("click", () => openDialog(config.createUrl));
for (const input of document.querySelectorAll('input[name="cal-view"]')) {
  input.addEventListener("change", () => {
    calendar.changeView(input.value);
    rememberView(input.value);
  });
}

// Edit buttons inside the popover open the form in the dialog.
popover.addEventListener("click", (event) => {
  const button = event.target.closest("[data-edit-url]");
  if (button) { event.preventDefault(); openDialog(button.dataset.editUrl); }
});

// Server responses: HX-Trigger {"calendar:refresh", "dialog:close"}.
document.body.addEventListener("calendar:refresh", () => calendar.refetchEvents());
document.body.addEventListener("dialog:close", () => {
  dialog.close();
  popover.hidePopover?.();
});
