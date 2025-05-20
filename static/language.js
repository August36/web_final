document.querySelectorAll(".lang-switch").forEach(btn => {
  btn.addEventListener("click", () => {
    const lan = btn.dataset.lang;

    // Gem sproget i session via POST
    fetch(`/set-language/${lan}`, { method: "POST" })
      .then(() => {
        let path = window.location.pathname.replace(/\/(en|dk)$/, "").replace(/^\/|\/$/g, "");
        location.href = path ? `/${path}/${lan}` : `/${lan}`;
      });
  });
});