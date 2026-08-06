(() => {
  const root = document.querySelector('[data-cookie-consent]');
  if (!root) return;

  const storageKey = 'pizzaVittiConsentV1';
  const settings = root.querySelector('[data-cookie-settings]');
  const analyticsInput = root.querySelector('[data-cookie-analytics]');
  const customizeButton = root.querySelector('[data-cookie-customize]');
  const saveButton = root.querySelector('[data-cookie-save]');
  const acceptButton = root.querySelector('[data-cookie-accept]');
  const rejectButton = root.querySelector('[data-cookie-reject]');
  let trackersLoaded = false;

  const injectScript = (src) => {
    if (!src) return;
    const script = document.createElement('script');
    script.async = true;
    script.src = src;
    document.head.appendChild(script);
  };

  const loadAnalytics = () => {
    if (trackersLoaded) return;
    trackersLoaded = true;
    const {ga4Id, gtmId, clarityId} = document.body.dataset;

    if (ga4Id) {
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () { window.dataLayer.push(arguments); };
      window.gtag('js', new Date());
      window.gtag('config', ga4Id);
      injectScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(ga4Id)}`);
    }
    if (gtmId) {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({'gtm.start': Date.now(), event: 'gtm.js'});
      injectScript(`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(gtmId)}`);
    }
    if (clarityId) {
      window.clarity = window.clarity || function () {
        (window.clarity.q = window.clarity.q || []).push(arguments);
      };
      injectScript(`https://www.clarity.ms/tag/${encodeURIComponent(clarityId)}`);
    }
  };

  const readConsent = () => {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey));
      return value && typeof value.analytics === 'boolean' ? value : null;
    } catch (_) {
      return null;
    }
  };

  const closeDialog = () => {
    root.hidden = true;
    document.body.classList.remove('cookie-consent-open');
  };

  const saveConsent = (analytics) => {
    localStorage.setItem(storageKey, JSON.stringify({necessary: true, analytics, savedAt: new Date().toISOString()}));
    if (analytics) loadAnalytics();
    closeDialog();
  };

  const openDialog = (showSettings = false) => {
    const consent = readConsent();
    analyticsInput.checked = Boolean(consent?.analytics);
    settings.hidden = !showSettings;
    customizeButton.hidden = showSettings;
    saveButton.hidden = !showSettings;
    root.hidden = false;
    document.body.classList.add('cookie-consent-open');
    (showSettings ? analyticsInput : rejectButton).focus();
  };

  rejectButton.addEventListener('click', () => saveConsent(false));
  acceptButton.addEventListener('click', () => saveConsent(true));
  customizeButton.addEventListener('click', () => openDialog(true));
  saveButton.addEventListener('click', () => saveConsent(analyticsInput.checked));
  document.querySelectorAll('[data-cookie-manage]').forEach(button => {
    button.addEventListener('click', () => openDialog(true));
  });

  const consent = readConsent();
  if (!consent) openDialog();
  else if (consent.analytics) loadAnalytics();
})();
