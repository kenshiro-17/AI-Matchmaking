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
  const syncLayoutState = () => {
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
    const overflowX = document.documentElement.scrollWidth - document.documentElement.clientWidth > 1;
    root.classList.toggle("layout-compact", viewportWidth < 1180 || overflowX);
    root.classList.toggle("layout-overflow", overflowX);
  };

  let resizeScheduled = false;
  const scheduleLayoutSync = () => {
    if (resizeScheduled) {
      return;
    }
    resizeScheduled = true;
    window.requestAnimationFrame(() => {
      resizeScheduled = false;
      syncLayoutState();
    });
  };

  if (topbar) {
    let scrollScheduled = false;
    const updateTopbar = () => {
      scrollScheduled = false;
      topbar.classList.toggle("topbar-scrolled", window.scrollY > 10);
    };

    const onScroll = () => {
      if (scrollScheduled) {
        return;
      }
      scrollScheduled = true;
      window.requestAnimationFrame(updateTopbar);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    updateTopbar();
  }

  window.addEventListener("resize", scheduleLayoutSync, { passive: true });
  window.addEventListener("orientationchange", scheduleLayoutSync, { passive: true });
  window.setTimeout(syncLayoutState, 0);
  window.setTimeout(syncLayoutState, 150);
  syncLayoutState();
})();
