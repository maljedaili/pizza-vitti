const publicSite = document.body.classList.contains("public-site");

if (publicSite) {
  document.querySelectorAll("[data-hero-video]").forEach((video) => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dataSaver = navigator.connection?.saveData === true;
    if (reducedMotion || dataSaver) {
      video.pause();
      return;
    }
    video.querySelectorAll("source[data-src]").forEach((source) => {
      source.src = source.dataset.src;
    });
    video.load();
    video.play().catch(() => {});
  });

  document.querySelectorAll("[data-product-customizer]").forEach((form) => {
    const total = document.querySelector("[data-product-total]");
    const quantity = form.querySelector("[data-product-qty]");
    const supplements = [...form.querySelectorAll("[data-supplement-price]")];
    const updateTotal = () => {
      if (!total) return;
      const base = Number.parseFloat(total.dataset.basePrice || "0");
      const extras = supplements
        .filter((field) => field.checked)
        .reduce((sum, field) => sum + Number.parseFloat(field.dataset.supplementPrice || "0"), 0);
      const qty = Math.max(1, Number.parseInt(quantity?.value || "1", 10));
      total.textContent = ((base + extras) * qty).toFixed(2).replace(".", ",");
    };
    supplements.forEach((field) => field.addEventListener("change", updateTotal));
    quantity?.addEventListener("input", updateTotal);
  });

  document.querySelectorAll("[data-checkout-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("[data-submit-once]");
      if (button) {
        button.disabled = true;
        button.textContent = "Envoi en cours…";
      }
    });
  });

  const ageGate = document.querySelector("[data-age-gate]");
  const restrictedForms = [...document.querySelectorAll("form[data-age-restricted]")];
  let pendingRestrictedForm = null;
  const ageIsConfirmed = () => window.localStorage.getItem("pizzaVittiAge18") === "yes";
  const markAgeConfirmed = (form) => {
    if (!form.querySelector('input[name="age_confirmed"]')) {
      const confirmation = document.createElement("input");
      confirmation.type = "hidden";
      confirmation.name = "age_confirmed";
      confirmation.value = "1";
      form.append(confirmation);
    }
  };
  restrictedForms.forEach((form) => {
    if (ageIsConfirmed()) markAgeConfirmed(form);
    form.addEventListener("submit", (event) => {
      if (ageIsConfirmed()) {
        markAgeConfirmed(form);
        return;
      }
      event.preventDefault();
      pendingRestrictedForm = form;
      if (ageGate) {
        ageGate.hidden = false;
        document.body.style.overflow = "hidden";
        ageGate.querySelector("[data-age-confirm]")?.focus();
      }
    });
  });
  ageGate?.querySelector("[data-age-confirm]")?.addEventListener("click", () => {
    window.localStorage.setItem("pizzaVittiAge18", "yes");
    restrictedForms.forEach(markAgeConfirmed);
    ageGate.hidden = true;
    document.body.style.overflow = "";
    const form = pendingRestrictedForm;
    pendingRestrictedForm = null;
    form?.requestSubmit();
  });
  ageGate?.querySelector("[data-age-decline]")?.addEventListener("click", () => {
    ageGate.hidden = true;
    document.body.style.overflow = "";
    pendingRestrictedForm = null;
  });

  document.querySelectorAll("[data-hero-motion]").forEach((hero) => {
    hero.addEventListener("pointermove", (event) => {
      const bounds = hero.getBoundingClientRect();
      const x = ((event.clientX - bounds.left) / bounds.width) * 100;
      const y = ((event.clientY - bounds.top) / bounds.height) * 100;
      hero.style.setProperty("--pointer-x", `${x.toFixed(1)}%`);
      hero.style.setProperty("--pointer-y", `${y.toFixed(1)}%`);
    });
  });

  document.querySelectorAll("[data-loyalty-progress]").forEach((tracker) => {
    const progress = Number.parseInt(tracker.dataset.loyaltyProgress || "0", 10);
    tracker.style.setProperty("--loyalty-progress", `${Math.min(100, Math.max(0, progress))}%`);
  });

  const appPromo = document.querySelector("[data-mobile-app-promo]");
  if (appPromo && "IntersectionObserver" in window) {
    const promoObserver = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          appPromo.classList.add("is-visible");
          promoObserver.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    promoObserver.observe(appPromo);
  }

  document.querySelectorAll("[data-hero-slider]").forEach((slider) => {
    const slides = [...slider.querySelectorAll("[data-hero-slide]")];
    const tabs = [...slider.querySelectorAll("[data-hero-go]")];
    const previous = slider.querySelector("[data-hero-previous]");
    const next = slider.querySelector("[data-hero-next]");
    const progress = slider.querySelector(".hero-slider-progress span");
    let current = 0;
    let timer;
    let touchStart = 0;

    const restartProgress = () => {
      if (!progress) return;
      progress.style.animation = "none";
      progress.offsetHeight;
      progress.style.animation = "";
    };

    const showSlide = (index, restartTimer = true) => {
      current = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === current;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", active ? "false" : "true");
      });
      tabs.forEach((tab, tabIndex) => {
        const active = tabIndex === current;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-selected", active ? "true" : "false");
      });
      restartProgress();
      if (restartTimer) {
        window.clearInterval(timer);
        timer = window.setInterval(() => showSlide(current + 1, false), 6500);
      }
    };

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => showSlide(Number(tab.dataset.heroGo)));
    });
    previous?.addEventListener("click", () => showSlide(current - 1));
    next?.addEventListener("click", () => showSlide(current + 1));
    slider.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") showSlide(current - 1);
      if (event.key === "ArrowRight") showSlide(current + 1);
    });
    slider.addEventListener("touchstart", (event) => {
      touchStart = event.changedTouches[0].clientX;
    }, { passive: true });
    slider.addEventListener("touchend", (event) => {
      const distance = event.changedTouches[0].clientX - touchStart;
      if (Math.abs(distance) > 45) showSlide(current + (distance < 0 ? 1 : -1));
    }, { passive: true });
    slider.addEventListener("mouseenter", () => window.clearInterval(timer));
    slider.addEventListener("mouseleave", () => showSlide(current));
    slider.addEventListener("focusin", () => window.clearInterval(timer));
    slider.addEventListener("focusout", () => showSlide(current));
    showSlide(0);
  });

}
