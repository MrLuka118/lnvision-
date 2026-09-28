import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'node:path';
import { utimesSync, existsSync } from 'node:fs';
export default defineConfig({
  plugins: [tailwindcss(), { name: 'django-reload', closeBundle() { const now = new Date(); if (existsSync('config/settings/dev.py')) utimesSync('config/settings/dev.py', now, now); } }],
  base: '/static/dist/',
  resolve: { alias: {
    htmx: resolve('static/vendor/htmx-2.0.10.esm.js'),
    alpine: resolve('static/vendor/alpine-csp-3.17.4.esm.min.js'),
    'app/components': resolve('static/js/components.js'),
    'app/popover': resolve('static/js/popover.js'),
    'app/actions': resolve('static/js/actions.js'),
    'app/refraction': resolve('static/js/refraction.js'),
  }},
  build: { outDir: 'static/dist', emptyOutDir: true, manifest: true,
    rollupOptions: { input: ['assets/js/main.js', 'assets/js/public.js', 'static/js/gallery.js', 'static/js/portfolio.js'] }
  },
  server: { cors: { origin: /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/ } }
});
