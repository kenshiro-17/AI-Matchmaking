(() => {
  const root = document.documentElement;
  root.classList.add("js");

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const revealSelectors = [
    ".hero",
    ".panel",
    ".kpi",
    ".match-card",
    ".scenario-card",
    ".list-card",
    ".program-card",
    ".quality-item",
    ".audit-row",
  ];

  const revealTargets = Array.from(document.querySelectorAll(revealSelectors.join(",")));
  revealTargets.forEach((el, index) => {
    el.setAttribute("data-reveal", "");
    el.style.setProperty("--reveal-index", String(index % 12));
  });

  if (prefersReducedMotion) {
    revealTargets.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries, obs) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) {
          continue;
        }
        entry.target.classList.add("is-visible");
        obs.unobserve(entry.target);
      }
    },
    {
      threshold: 0.12,
      rootMargin: "0px 0px -8% 0px",
    },
  );

  revealTargets.forEach((el) => observer.observe(el));

  const topbar = document.querySelector(".topbar");
  if (!topbar) {
    return;
  }

  let scheduled = false;
  const updateTopbar = () => {
    scheduled = false;
    topbar.classList.toggle("topbar-scrolled", window.scrollY > 10);
  };

  const onScroll = () => {
    if (scheduled) {
      return;
    }
    scheduled = true;
    window.requestAnimationFrame(updateTopbar);
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  updateTopbar();
})();

