(function () {
  const launcher = document.getElementById("app-launcher");
  const search = document.getElementById("launcher-search");
  const sidebar = document.getElementById("app-sidebar");

  function openLauncher() {
    if (!launcher) return;
    launcher.hidden = false;
    document.body.classList.add("modal-open");
    window.setTimeout(() => search?.focus(), 30);
  }

  function closeLauncher() {
    if (!launcher) return;
    launcher.hidden = true;
    document.body.classList.remove("modal-open");
  }

  document.getElementById("app-launcher-open")?.addEventListener("click", openLauncher);
  document.getElementById("mobile-launcher-open")?.addEventListener("click", openLauncher);
  document.getElementById("command-search-open")?.addEventListener("click", openLauncher);
  document.getElementById("app-launcher-close")?.addEventListener("click", closeLauncher);
  launcher?.addEventListener("click", (event) => {
    if (event.target === launcher) closeLauncher();
  });
  search?.addEventListener("input", () => {
    const query = search.value.trim().toLocaleLowerCase("pt-BR");
    document.querySelectorAll("[data-launcher-item]").forEach((item) => {
      item.hidden = Boolean(query) && !item.textContent.toLocaleLowerCase("pt-BR").includes(query);
    });
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openLauncher();
    }
    if (event.key === "Escape") closeLauncher();
  });
  document.getElementById("mobile-menu-toggle")?.addEventListener("click", () => sidebar?.classList.toggle("open"));

  const topbarDate = document.getElementById("topbar-date");
  if (topbarDate) {
    topbarDate.textContent = new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit", month: "short" }).format(new Date());
  }
})();
