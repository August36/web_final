document.addEventListener("DOMContentLoaded", () => {
  console.log("modal.js loaded");

  const imgModal = document.getElementById("img-modal");
  const imgModalImg = document.getElementById("modal-img");
  const imgModalClose = document.querySelector(".modal-close");

  // Vi lytter på hele dokumentet og tjekker om der klikkes på et billede
  document.addEventListener("click", (e) => {
    const clickedImg = e.target.closest("img");
    if (clickedImg && clickedImg.closest("#img-wrapper")) {
      imgModal.classList.remove("hidden");
      imgModalImg.src = clickedImg.src;
    }
  });

  imgModalClose.addEventListener("click", () => {
    imgModal.classList.add("hidden");
  });

  window.addEventListener("click", e => {
    if (e.target === imgModal) {
      imgModal.classList.add("hidden");
    }
  });

  window.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      imgModal.classList.add("hidden");
    }
  });
});
