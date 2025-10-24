document.addEventListener("DOMContentLoaded", () => {
  const contentField = document.querySelector("textarea[name='content']");
  const counter = document.getElementById("contentLength");

  if (!contentField || !counter) {
    return;
  }

  const updateCounter = () => {
    const length = contentField.value.length;
    counter.textContent = length;
    if (length > 1000) {
      counter.classList.add("has-text-danger");
    } else {
      counter.classList.remove("has-text-danger");
    }
  };

  contentField.addEventListener("input", updateCounter);
  updateCounter();
});
