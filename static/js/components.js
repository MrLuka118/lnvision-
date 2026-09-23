// Alpine components. The CSP build of Alpine is used, so behaviour lives here, not in markup.

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Run a DOM change inside a same-document view transition when the browser supports it. */
export function morph(update) {
  if (!document.startViewTransition || reducedMotion()) {
    return Promise.resolve(update());
  }
  return document.startViewTransition(update).finished;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const csrfToken = () => JSON.parse(document.body.getAttribute("hx-headers") || "{}")["X-CSRFToken"];

export function registerComponents(Alpine) {
  // Chunked, resumable photo upload for the gallery editor (see apps/photos/views.py).
  Alpine.data("uploader", () => ({
    items: [],
    active: 0,
    dragging: false,
    open: false,
    refreshTimer: null,

    get total() {
      return this.items.length;
    },
    get finished() {
      return this.items.filter((i) => i.state === "done").length;
    },
    get failed() {
      return this.items.filter((i) => i.state === "failed").length;
    },
    get busy() {
      return this.items.some((i) => i.state === "queued" || i.state === "uploading");
    },
    get percent() {
      const size = this.items.reduce((sum, i) => sum + i.size, 0) || 1;
      const sent = this.items.reduce((sum, i) => sum + i.sent, 0);
      return `${Math.round((sent / size) * 100)}%`;
    },
    get summary() {
      return (this.$root.dataset.summary || "%(done)s / %(total)s")
        .replace("%(done)s", this.finished)
        .replace("%(total)s", this.total);
    },

    init() {
      window.addEventListener("beforeunload", (event) => {
        if (this.busy) event.preventDefault();
      });
    },

    pick() {
      this.$refs.input.click();
    },
    chosen(event) {
      this.add(event.target.files);
      event.target.value = "";
    },
    dragover(event) {
      if (!event.dataTransfer?.types?.includes("Files")) return;
      event.preventDefault();
      this.dragging = true;
    },
    dragleave() {
      this.dragging = false;
    },
    drop(event) {
      if (!event.dataTransfer?.files?.length) return;
      event.preventDefault();
      this.dragging = false;
      this.add(event.dataTransfer.files);
    },
    close() {
      if (!this.busy) {
        this.items = [];
        this.open = false;
      }
    },

    add(files) {
      for (const file of files) {
        if (!file.type.startsWith("image/") && !/\.(tiff?|avif)$/i.test(file.name)) continue;
        this.items.push({
          key: `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`,
          file,
          name: file.name,
          size: file.size,
          sent: 0,
          state: "queued",
          error: "",
          get width() {
            return `${Math.round((this.sent / (this.size || 1)) * 100)}%`;
          },
        });
      }
      if (this.items.length) this.open = true;
      this.pump();
    },

    pump() {
      while (this.active < 3) {
        const next = this.items.find((i) => i.state === "queued");
        if (!next) return;
        this.upload(next);
      }
    },

    async upload(item) {
      this.active += 1;
      item.state = "uploading";
      try {
        const start = await fetch(this.$root.dataset.startUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
          body: JSON.stringify({
            name: item.name,
            size: item.size,
            section: this.$refs.section?.value || null,
          }),
        });
        const session = await start.json();
        if (!start.ok) throw new Error(session.error || start.statusText);
        let offset = 0;
        while (offset < item.size) {
          const result = await this.sendChunk(session.url, item.file, offset, session.chunkSize);
          if (result.error) throw new Error(result.error);
          offset = result.received;
          item.sent = offset;
        }
        item.state = "done";
        this.refreshGrid();
      } catch (error) {
        item.state = "failed";
        item.error = error.message;
      } finally {
        this.active -= 1;
        this.pump();
        if (!this.busy) this.refreshGrid(0);
      }
    },

    async sendChunk(url, file, offset, size) {
      for (let attempt = 0; ; attempt++) {
        try {
          const response = await fetch(url, {
            method: "PUT",
            headers: {
              "Content-Type": "application/octet-stream",
              "Upload-Offset": String(offset),
              "X-CSRFToken": csrfToken(),
            },
            body: file.slice(offset, offset + size),
          });
          const data = await response.json();
          // 409 tells us where the server really is (a retried chunk that did arrive).
          if (response.status === 409 && typeof data.received === "number") return data;
          if (!response.ok) return { error: data.error || response.statusText };
          return data;
        } catch (error) {
          if (attempt >= 3) throw error;
          await sleep(1000 * 2 ** attempt);
          const probe = await fetch(url).then((r) => r.json()).catch(() => null);
          if (probe && typeof probe.received === "number") offset = probe.received;
        }
      }
    },

    // The grid polls while photos process; nudge it as uploads finish, at most every 1.5 s.
    refreshGrid(delay = 1500) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = setTimeout(() => window.htmx.trigger(document.body, "grid:refresh"), delay);
    },
  }));

  Alpine.data("themeSwitch", () => ({
    theme: document.documentElement.dataset.theme || "dark",

    choose(event) {
      const theme = event.target.value;
      morph(() => {
        document.documentElement.dataset.theme = theme;
        // The browser chrome follows the page surround (--theme-color in tokens.css).
        const meta = document.querySelector('meta[name="theme-color"]');
        const color = getComputedStyle(document.documentElement).getPropertyValue("--theme-color").trim();
        if (meta && color) meta.content = color;
      });
      this.theme = theme;
      document.cookie = `theme=${theme}; path=/; max-age=31536000; samesite=lax`;
    },
  }));

  Alpine.data("expander", () => ({
    open: false,

    toggle() {
      morph(async () => {
        this.open = !this.open;
        await this.$nextTick();
      });
    },

    close() {
      if (!this.open) return;
      morph(async () => {
        this.open = false;
        await this.$nextTick();
      });
    },
  }));

  Alpine.data("copy", () => ({
    label: "",

    init() {
      this.label = this.$root.querySelector("[x-text]")?.textContent.trim() || "";
      this.original = this.label;
    },

    async copy() {
      const value = this.$refs.value.value;
      try {
        await navigator.clipboard.writeText(value);
      } catch {
        this.$refs.value.select();
        return;
      }
      this.label = this.$root.dataset.copied || this.original;
      setTimeout(() => {
        this.label = this.original;
      }, 2000);
    },
  }));

  Alpine.data("toast", () => ({
    open: true,

    init() {
      setTimeout(() => this.dismiss(), 6000);
    },

    dismiss() {
      this.open = false;
    },
  }));

  // Counts up to data-to when it scrolls into view. data-format: "eur" | "int".
  Alpine.data("counter", () => ({
    init() {
      const el = this.$el;
      const target = Number.parseFloat(el.dataset.to || "0");
      const format =
        el.dataset.format === "eur"
          ? new Intl.NumberFormat("sl-SI", { style: "currency", currency: "EUR" })
          : new Intl.NumberFormat("sl-SI", { maximumFractionDigits: 0 });
      const render = (value) => {
        el.textContent = format.format(value);
      };
      if (reducedMotion()) {
        render(target);
        return;
      }
      // Keep the server-rendered figure until the counter is about to be seen.
      const observer = new IntersectionObserver((entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        observer.disconnect();
        render(0);
        const start = performance.now();
        const duration = 900;
        const step = (now) => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - (1 - t) ** 4;
          render(target * eased);
          if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
      observer.observe(el);
    },
  }));
}
