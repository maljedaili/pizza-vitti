document.addEventListener('click', e => {
  if (e.target.matches('[data-nav]')) {
    const isOpen = document.body.classList.toggle('nav-open');
    e.target.setAttribute('aria-expanded', String(isOpen));
    e.target.setAttribute('aria-label', isOpen ? 'Fermer le menu' : 'Ouvrir le menu');
  }
  if (e.target.closest('.site-header nav a') && document.body.classList.contains('nav-open')) {
    document.body.classList.remove('nav-open');
    const navToggle = document.querySelector('[data-nav]');
    navToggle?.setAttribute('aria-expanded', 'false');
    navToggle?.setAttribute('aria-label', 'Ouvrir le menu');
  }
  if (e.target.matches('[data-bot-toggle]')) document.querySelector('[data-bot]').classList.toggle('open');
});
const observer = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) entry.target.classList.add('show');
}), {threshold: .05});
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
document.querySelectorAll('.menu-photo-card').forEach(card => {
  card.addEventListener('mousemove', e => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width - .5) * 10;
    const y = ((e.clientY - rect.top) / rect.height - .5) * -10;
    card.style.setProperty('--tilt-x', `${y.toFixed(2)}deg`);
    card.style.setProperty('--tilt-y', `${x.toFixed(2)}deg`);
  });
  card.addEventListener('mouseleave', () => {
    card.style.setProperty('--tilt-x', '0deg');
    card.style.setProperty('--tilt-y', '0deg');
  });
});
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').then(registration => registration.update()).catch(() => {}));
}
let installPromptEvent = null;
const installButtons = document.querySelectorAll('[data-install-app]');
const installInstructions = document.querySelectorAll('[data-install-instructions]');
const showInstallInstructions = () => installInstructions.forEach(el => { el.hidden = false; });
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  installPromptEvent = event;
  installButtons.forEach(button => { button.hidden = false; });
});
installButtons.forEach(button => button.addEventListener('click', async () => {
  if (!installPromptEvent) {
    showInstallInstructions();
    return;
  }
  installPromptEvent.prompt();
  await installPromptEvent.userChoice;
  installPromptEvent = null;
  installButtons.forEach(item => { item.hidden = true; });
}));
const orderPreview = document.querySelector('[data-order-preview]');
if (orderPreview) {
  document.querySelector('[data-order-preview-toggle]')?.addEventListener('click', () => orderPreview.classList.toggle('open'));
  document.querySelector('[data-order-preview-close]')?.addEventListener('click', () => orderPreview.classList.remove('open'));
}
const prepBoard = document.querySelector('[data-prep-board]');
if (prepBoard) {
  const key = 'pizzaVittiLatestOrder';
  const soundKey = 'pizzaVittiPrepSound';
  const pendingAlertKey = 'pizzaVittiPendingPrepAlert';
  const soundButton = document.querySelector('[data-prep-sound]');
  const wakeButton = document.querySelector('[data-wake-lock]');
  const testAlertButton = document.querySelector('[data-test-alert]');
  const alertBox = document.querySelector('[data-prep-alert]');
  const alertClose = document.querySelector('[data-prep-alert-close]');
  let wakeLock = null;
  const setWakeLabel = text => { if (wakeButton) wakeButton.textContent = text; };
  const requestWakeLock = async () => {
    if (!('wakeLock' in navigator)) {
      setWakeLabel('Écran allumé non supporté');
      return;
    }
    try {
      wakeLock = await navigator.wakeLock.request('screen');
      setWakeLabel('Écran actif');
      wakeLock.addEventListener('release', () => {
        wakeLock = null;
        if (document.visibilityState === 'visible') setWakeLabel('Garder écran allumé');
      });
    } catch (error) {
      setWakeLabel('Garder écran allumé');
    }
  };
  wakeButton?.addEventListener('click', requestWakeLock);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && wakeLock === null && wakeButton?.textContent === 'Écran actif') requestWakeLock();
  });
  const ring = () => {
    try {
      const audio = new (window.AudioContext || window.webkitAudioContext)();
      [0, .22, .44].forEach((offset, index) => {
        const oscillator = audio.createOscillator();
        const gain = audio.createGain();
        oscillator.type = 'square';
        oscillator.frequency.value = index % 2 ? 740 : 980;
        gain.gain.setValueAtTime(.001, audio.currentTime + offset);
        gain.gain.exponentialRampToValueAtTime(.28, audio.currentTime + offset + .03);
        gain.gain.exponentialRampToValueAtTime(.001, audio.currentTime + offset + .18);
        oscillator.connect(gain).connect(audio.destination);
        oscillator.start(audio.currentTime + offset);
        oscillator.stop(audio.currentTime + offset + .2);
      });
    } catch (error) {}
  };
  const showPrepAlert = () => {
    document.body.classList.add('prep-alert-active');
    if (alertBox) alertBox.hidden = false;
  };
  const stopPrepAlert = () => {
    document.body.classList.remove('prep-alert-active');
    if (alertBox) alertBox.hidden = true;
    localStorage.removeItem(pendingAlertKey);
  };
  const speak = text => {
    ring();
    setTimeout(ring, 900);
    setTimeout(ring, 1800);
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
    }
  };
  const setSoundLabel = () => {
    if (soundButton) soundButton.textContent = localStorage.getItem(soundKey) === 'on' ? 'Son actif' : 'Activer son';
  };
  soundButton?.addEventListener('click', () => {
    localStorage.setItem(soundKey, 'on');
    setSoundLabel();
    speak('Son active. Vous recevrez une alerte a chaque nouvelle commande.');
  });
  testAlertButton?.addEventListener('click', () => {
    localStorage.setItem(soundKey, 'on');
    setSoundLabel();
    showPrepAlert();
    speak('Test alerte cuisine. Nouvelle commande recue.');
  });
  alertClose?.addEventListener('click', stopPrepAlert);
  setSoundLabel();
  if (localStorage.getItem(pendingAlertKey) === 'on') {
    showPrepAlert();
    if (localStorage.getItem(soundKey) === 'on') speak('Nouvelle commande recue.');
  }
  const initial = prepBoard.dataset.latestOrder || '';
  if (initial && !localStorage.getItem(key)) localStorage.setItem(key, initial);
  const checkOrders = async () => {
    try {
      const res = await fetch(prepBoard.dataset.pollUrl || window.location.href, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await res.json();
      const latest = data.latest_order_key || '';
      const previous = localStorage.getItem(key) || '';
      if (latest && previous && latest !== previous) {
        localStorage.setItem(key, latest);
        localStorage.setItem(pendingAlertKey, 'on');
        showPrepAlert();
        if (localStorage.getItem(soundKey) === 'on') speak('Nouvelle commande recue.');
        setTimeout(() => window.location.reload(), 2600);
      } else if (latest) {
        localStorage.setItem(key, latest);
      }
    } catch (error) {}
  };
  setInterval(checkOrders, 12000);
}
const typeSelect = document.querySelector('[data-customer-type]');
const proBox = document.querySelector('[data-pro-box]');
if (typeSelect && proBox) {
  const togglePro = () => { proBox.hidden = typeSelect.value !== 'professionnel' && !proBox.dataset.force; };
  typeSelect.addEventListener('change', togglePro);
  togglePro();
}
const appRole = document.querySelector('[data-app-role]');
if (appRole) {
  const staffFields = document.querySelector('[data-staff-fields]');
  const username = document.querySelector('#app-username');
  const password = document.querySelector('#app-password');
  const passwordLabel = document.querySelector('[data-password-label]');
  const note = document.querySelector('[data-app-login-note]');
  const syncAppLogin = () => {
    const staff = appRole.value === 'staff';
    if (staffFields) staffFields.hidden = !staff;
    if (username) username.required = staff;
    if (password) password.inputMode = appRole.value === 'kitchen' ? 'numeric' : 'text';
    if (passwordLabel) passwordLabel.textContent = staff ? 'Mot de passe staff' : 'Code secret';
    if (note) {
      note.textContent = staff
        ? 'Utilisez le compte créé dans le dashboard propriétaire.'
        : appRole.value === 'owner'
          ? 'Entrez le code confidentiel du propriétaire.'
          : 'Entrez le code confidentiel de la cuisine.';
    }
  };
  appRole.addEventListener('change', syncAppLogin);
  syncAppLogin();
}
document.querySelectorAll('[data-live-clock]').forEach(clock => {
  const timeNode = clock.querySelector('[data-clock-time]');
  const dateNode = clock.querySelector('[data-clock-date]');
  const updateClock = () => {
    const now = new Date();
    if (timeNode) timeNode.textContent = new Intl.DateTimeFormat('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(now);
    if (dateNode) dateNode.textContent = new Intl.DateTimeFormat('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(now);
  };
  updateClock();
  setInterval(updateClock, 1000);
});
const cameraWall = document.querySelector('[data-camera-wall]');
if (cameraWall) {
  const frames = [...cameraWall.querySelectorAll('iframe[data-camera-src]')];
  const setCameraWall = enabled => frames.forEach(frame => {
    const paused = frame.closest('.camera-frame')?.querySelector('[data-camera-paused]');
    if (enabled) {
      if (!frame.src) frame.src = frame.dataset.cameraSrc;
      if (paused) paused.hidden = true;
    } else {
      frame.removeAttribute('src');
      if (paused) paused.hidden = false;
    }
  });
  document.querySelector('[data-camera-wall-start]')?.addEventListener('click', () => setCameraWall(true));
  document.querySelector('[data-camera-wall-stop]')?.addEventListener('click', () => setCameraWall(false));
}
const cameraFocus = document.querySelector('[data-camera-focus]');
if (cameraFocus) {
  const frame = cameraFocus.querySelector('[data-camera-focus-frame]');
  const listenButton = cameraFocus.querySelector('[data-camera-listen]');
  const talkButton = cameraFocus.querySelector('[data-camera-talk]');
  const status = cameraFocus.querySelector('[data-camera-mode-status]');
  const setMode = (button, url, text) => {
    if (!frame || !url) return;
    frame.src = url;
    [listenButton, talkButton].forEach(item => item?.classList.remove('active'));
    button?.classList.add('active');
    if (status) status.textContent = text;
  };
  listenButton?.addEventListener('click', () => setMode(listenButton, listenButton.dataset.url, 'Mode écoute actif.'));
  talkButton?.addEventListener('click', async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      if (status) status.textContent = 'Microphone non disponible. Utilisez HTTPS et vérifiez les permissions.';
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      stream.getTracks().forEach(track => track.stop());
      setMode(talkButton, talkButton.dataset.url, 'Mode parler actif. Utilisez le bouton micro dans la vidéo.');
    } catch (error) {
      if (status) status.textContent = 'Autorisation microphone refusée. Activez-la dans les réglages du navigateur.';
    }
  });
}
const botForm = document.querySelector('[data-bot-form]');
const escapeHtml = text => text.replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
if (botForm) {
  botForm.addEventListener('submit', async e => {
    e.preventDefault();
    const input = botForm.querySelector('input[name="message"]');
    const log = document.querySelector('[data-bot-log]');
    const text = input.value.trim();
    if (!text) return;
    log.insertAdjacentHTML('beforeend', `<p><strong>Vous :</strong> ${escapeHtml(text)}</p>`);
    const formData = new FormData(botForm);
    const res = await fetch(botForm.dataset.url, {method:'POST', body:formData, headers:{'X-Requested-With':'XMLHttpRequest'}});
    const data = await res.json();
    log.insertAdjacentHTML('beforeend', `<p><strong>Assistant :</strong> ${escapeHtml(data.answer)}</p>`);
    log.scrollTop = log.scrollHeight;
    input.value = '';
  });
  document.querySelectorAll('[data-bot-suggest]').forEach(button => button.addEventListener('click', () => {
    const input = botForm.querySelector('input[name="message"]');
    input.value = button.dataset.botSuggest;
    botForm.requestSubmit();
  }));
}

// Language dropdown
const lang = document.querySelector('[data-lang]');
const langToggle = document.querySelector('[data-lang-toggle]');
if (lang && langToggle) {
  langToggle.addEventListener('click', e => { e.stopPropagation(); lang.classList.toggle('open'); });
  document.addEventListener('click', () => lang.classList.remove('open'));
}

// Gallery slider / lightbox
const galleryItems = [...document.querySelectorAll('[data-gallery-item]')].map((el, index) => ({
  el, index, src: el.dataset.src, title: el.dataset.title || 'Pizza Vitti'
})).filter(item => item.src);
const lightbox = document.querySelector('[data-lightbox]');
let galleryIndex = 0;
function openLightbox(index){
  if (!lightbox || !galleryItems.length) return;
  galleryIndex = (index + galleryItems.length) % galleryItems.length;
  const item = galleryItems[galleryIndex];
  lightbox.querySelector('[data-lightbox-img]').src = item.src;
  lightbox.querySelector('[data-lightbox-title]').textContent = item.title;
  lightbox.hidden = false;
  document.body.style.overflow = 'hidden';
}
function closeLightbox(){ if(lightbox){ lightbox.hidden = true; document.body.style.overflow = ''; } }
function nextLightbox(step){ openLightbox(galleryIndex + step); }
galleryItems.forEach(item => item.el.addEventListener('click', () => openLightbox(item.index)));
document.querySelector('[data-lightbox-close]')?.addEventListener('click', closeLightbox);
document.querySelector('[data-lightbox-prev]')?.addEventListener('click', () => nextLightbox(-1));
document.querySelector('[data-lightbox-next]')?.addEventListener('click', () => nextLightbox(1));
lightbox?.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });
document.addEventListener('keydown', e => {
  if (!lightbox || lightbox.hidden) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowRight') nextLightbox(1);
  if (e.key === 'ArrowLeft') nextLightbox(-1);
});
