document.querySelectorAll(".lang-switch").forEach(btn => {
  btn.addEventListener("click", () => {
    const lan = btn.dataset.lang;
    const path = window.location.pathname.replace(/\/(en|dk)$/, "").replace(/^\/|\/$/g, "");

    // Hvis man står på forsiden (path = ""), gå til /<lang>
    if (!path) {
      location.href = `/${lan}`;
    } else {
      location.href = `/${path}/${lan}`;
    }
  });
});