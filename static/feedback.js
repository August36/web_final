// Validerer alle mix-check felter før submit
document.addEventListener("submit", function (e) {
  const form = e.target;
  if (!form.hasAttribute("mix-post")) return;

  let errors = [];

  form.querySelectorAll("[mix-check]").forEach(input => {
    const regex = new RegExp(input.getAttribute("mix-check"));
    if (!regex.test(input.value)) {
      input.classList.add("mix-error");
      errors.push({
        name: input.name,
        message: input.getAttribute("title") || "Invalid input"
      });
    } else {
      input.classList.remove("mix-error");
    }
  });

  if (errors.length > 0) {
    const errorHtml = `
      <div class="alert error">
        <ul>
          ${errors.map(err => `<li>${err.message}</li>`).join("")}
        </ul>
      </div>
    `;
    const fb = document.querySelector("#form-feedback");
    if (fb) fb.innerHTML = errorHtml;

    e.preventDefault(); // Stop MixHTML submit
  }
});

// Fjerner fejl når brugeren retter input
document.querySelectorAll("[mix-check]").forEach(input => {
  input.addEventListener("input", () => {
    const regex = new RegExp(input.getAttribute("mix-check"));
    const isValid = regex.test(input.value);

    if (isValid) {
      input.classList.remove("mix-error");

      const form = input.closest("form");
      const allValid = Array.from(form.querySelectorAll("[mix-check]")).every(i => {
        const re = new RegExp(i.getAttribute("mix-check"));
        return re.test(i.value);
      });

      if (allValid) {
        const fb = document.querySelector("#form-feedback");
        if (fb) fb.innerHTML = "";
      }
    }
  });
});

function resetButtonText() {
  const btn = document.querySelector('[mix-await]');
  if (btn) {
    btn.innerHTML = btn.getAttribute('mix-default');
    btn.removeAttribute('disabled');
  }
}
