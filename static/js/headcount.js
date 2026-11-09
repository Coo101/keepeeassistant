// Live totals under the camp form's group table (SPEC §9.3). The page shows the
// same totals without JavaScript; this only updates them while typing.
(function () {
  const totals = document.querySelector("[data-group-totals]");
  if (!totals) return;
  const form = totals.closest("form");
  const factor = parseFloat(totals.dataset.childFactor) || 0.7;
  const portionFormat = new Intl.NumberFormat(document.documentElement.lang || undefined, {
    maximumFractionDigits: 1,
  });

  function update() {
    const sums = { children: 0, teens: 0, staff: 0 };
    form.querySelectorAll("input[data-group-count]").forEach((count) => {
      const prefix = count.name.slice(0, -"count".length);
      const kind = form.querySelector(`[name="${prefix}kind"]`);
      const remove = form.querySelector(`[name="${prefix}DELETE"]`);
      if (!kind || !(kind.value in sums) || (remove && remove.checked)) return;
      sums[kind.value] += Math.max(0, parseInt(count.value, 10) || 0);
    });
    for (const kind of Object.keys(sums)) {
      totals.querySelector(`[data-total="${kind}"]`).textContent = sums[kind];
    }
    const portions = sums.teens + sums.staff + factor * sums.children;
    totals.querySelector('[data-total="portions"]').textContent = portionFormat.format(portions);
  }

  form.addEventListener("input", update);
  form.addEventListener("change", update);
  // Rows added through HTMX.
  document.body.addEventListener("htmx:afterSwap", update);
})();
