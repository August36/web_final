document.querySelectorAll(".lang-switch").forEach(btn => {
  btn.addEventListener("click", () => {
    const lan = btn.dataset.lang;

    // Fjern eksisterende lan-del, hvis den findes
    let path = window.location.pathname.replace(/\/(en|dk)$/, "");

    // Tilføj det valgte sprog
    location.href = `${path}/${lan}`;
  });
});