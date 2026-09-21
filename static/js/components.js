// Alpine components. The CSP build of Alpine is used, so behaviour lives here, not in markup.

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Run a DOM change inside a same-document view transition when the browser supports it. */
export function morph(update) {
  if (!document.startViewTransition || reducedMotion()) {
    return Promise.resolve(update());
  }
  return document.startViewTransition(update).finished;
}

export function registerComponents(Alpine) {
  Alpine.data("themeSwitch", () => ({
    theme: document.documentElement.dataset.theme || "dark",

    choose(event) {
      const theme = event.target.value;
      const light =
        theme === "light" || (theme === "auto" && matchMedia("(prefers-color-scheme: light)").matches);
      morph(() => {
        document.documentElement.dataset.theme = theme;
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.content = light ? "#e9e9e9" : "#262626";
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
