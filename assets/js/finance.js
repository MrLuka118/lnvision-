import Chart from 'chart.js/auto';
let charts = [];
export function initFinance() {
  charts.forEach(chart => chart.destroy());
  charts = [];
  const target = document.getElementById('finance-chart');
  if (!target) return;
  const style = getComputedStyle(document.documentElement);
  const color = name => style.getPropertyValue(name).trim();
  const monthly = JSON.parse(document.getElementById('finance-monthly').textContent);
  const previous = JSON.parse(document.getElementById('finance-previous').textContent);
  const categories = JSON.parse(document.getElementById('finance-categories').textContent);
  const money = value => new Intl.NumberFormat(document.documentElement.lang, { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value);
  Chart.defaults.color = color('--ink-2');
  Chart.defaults.font.family = color('--font-sans');
  Chart.defaults.borderColor = color('--line-soft');
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const options = {
    responsive: true, maintainAspectRatio: false, animation: calm ? false : { duration: 480 },
    plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 6, padding: 20 } }, tooltip: { backgroundColor: color('--surface'), titleColor: color('--ink'), bodyColor: color('--ink'), borderColor: color('--line'), borderWidth: 1, callbacks: { label: ctx => `${ctx.dataset.label || ctx.label}: ${money(ctx.parsed.y ?? ctx.parsed)}` } } },
  };
  const sl = document.documentElement.lang === 'sl';
  charts.push(new Chart(target, { type: 'bar', data: {
    labels: monthly.map(row => new Intl.DateTimeFormat(document.documentElement.lang, { month: 'short' }).format(new Date(2026,row.month-1,1))),
    datasets: [
      { label: sl ? 'Prihodki' : 'Income', data: monthly.map(r=>+r.income), backgroundColor: color('--accent'), borderRadius: 3, maxBarThickness: 18 },
      { label: sl ? 'Stroški' : 'Expenses', data: monthly.map(r=>+r.expenses), backgroundColor: color('--color-cc-moderate-red'), borderRadius: 3, maxBarThickness: 18 },
      { type: 'line', label: sl ? 'Neto prihodek' : 'Net income', data: monthly.map(r=>+r.profit), borderColor: color('--ink'), borderWidth: 1.5, pointRadius: 2, tension: .25 },
      { type: 'line', label: sl ? 'Preteklo leto' : 'Previous year', data: previous.map(r=>+r.income), borderColor: color('--ink-3'), borderDash: [4,4], borderWidth: 1, pointRadius: 0, tension: .25 },
    ] }, options: { ...options, scales: { x: { grid: { display: false } }, y: { ticks: { callback: money }, beginAtZero: true } } } }));
  const donut = document.getElementById('expense-chart');
  if (donut) charts.push(new Chart(donut, { type: 'doughnut', data: { labels: categories.map(r=>r.category__name), datasets: [{ data: categories.map(r=>+r.total), backgroundColor: categories.map(r=>r.category__colour), borderColor: color('--surround'), borderWidth: 4 }] }, options: { ...options, cutout: '78%', plugins: { ...options.plugins, legend: { display: false } } } }));
}
new MutationObserver(initFinance).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
matchMedia('(prefers-color-scheme: light)').addEventListener('change', initFinance);
