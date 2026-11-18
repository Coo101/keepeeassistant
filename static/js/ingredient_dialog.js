// Add an ingredient from a form (recipe, bill review) without losing what was typed.
(() => {
  const dialog = document.getElementById("new-ingredient-dialog");
  const form = dialog.querySelector("form");
  const errors = document.getElementById("new-ingredient-errors");
  const nameInput = form.querySelector('input[name$="-name"]');
  // The select the dialog was opened for, if any.
  let target = null;

  const ingredientSelects = () => document.querySelectorAll(dialog.dataset.selects);

  const showErrors = (messages) => {
    errors.textContent = messages.join(" ");
    errors.hidden = false;
  };

  const addOption = (select, ingredient) => {
    const option = new Option(ingredient.label, ingredient.id);
    // The lists are sorted by name; the first option is the empty one.
    const next = Array.from(select.options)
      .slice(1)
      .find((other) => other.text.localeCompare(ingredient.label) > 0);
    select.add(option, next || null);
  };

  const use = (select, ingredient) => {
    if (!select) return;
    select.value = ingredient.id;
    const unitName = select.name.replace(/-ingredient$/, "-unit");
    const unit = document.querySelector(`select[name="${unitName}"]`);
    if (unit) unit.value = ingredient.unit;
  };

  // One listener for the whole page, so openers in rows added later (HTMX) work too.
  document.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-new-ingredient]");
    if (!opener) return;
    errors.hidden = true;
    target = opener.dataset.select
      ? document.querySelector(`select[name="${opener.dataset.select}"]`)
      : null;
    const source = opener.dataset.nameFrom
      ? document.querySelector(`[name="${opener.dataset.nameFrom}"]`)
      : null;
    if (source && nameInput && !nameInput.value) nameInput.value = source.value;
    dialog.showModal();
  });
  document
    .getElementById("new-ingredient-cancel")
    .addEventListener("click", () => {
      form.reset();
      dialog.close();
    });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errors.hidden = true;
    let response;
    let body;
    try {
      // An expired session redirects to the login page: treat that as a failure.
      response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        redirect: "error",
      });
      body = await response.json();
    } catch {
      showErrors([dialog.dataset.saveError]);
      return;
    }
    if (!response.ok) {
      showErrors(
        Object.values(body.errors)
          .flat()
          .map((error) => error.message),
      );
      return;
    }
    ingredientSelects().forEach((select) => addOption(select, body));
    use(target || Array.from(ingredientSelects()).find((s) => !s.value), body);
    form.reset();
    dialog.close();
  });
})();
