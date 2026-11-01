// Add an ingredient from the recipe form without losing what was typed.
(() => {
  const dialog = document.getElementById("new-ingredient-dialog");
  const form = dialog.querySelector("form");
  const errors = document.getElementById("new-ingredient-errors");

  const ingredientSelects = () =>
    document.querySelectorAll('select[name^="ingredients-"][name$="-ingredient"]');

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

  const useInFirstEmptyRow = (ingredient) => {
    const select = Array.from(ingredientSelects()).find((s) => !s.value);
    if (!select) return;
    select.value = ingredient.id;
    const unitName = select.name.replace(/-ingredient$/, "-unit");
    document.querySelector(`select[name="${unitName}"]`).value = ingredient.unit;
  };

  document.getElementById("new-ingredient-open").addEventListener("click", () => {
    errors.hidden = true;
    dialog.showModal();
  });
  document
    .getElementById("new-ingredient-cancel")
    .addEventListener("click", () => dialog.close());

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
      showErrors(["Couldn't save the ingredient. Check that you're still logged in."]);
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
    useInFirstEmptyRow(body);
    form.reset();
    dialog.close();
  });
})();
