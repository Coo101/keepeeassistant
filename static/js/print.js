// Buttons marked data-print open the browser's print dialog.
document.addEventListener("click", (event) => {
  if (event.target.closest("[data-print]")) {
    window.print();
  }
});
