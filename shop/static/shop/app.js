document.addEventListener('click', e => {
  if (e.target.matches('[data-nav]')) document.body.classList.toggle('nav-open');
  if (e.target.matches('[data-bot-toggle]')) document.querySelector('[data-bot]').classList.toggle('open');
});
const observer = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) entry.target.classList.add('show');
}), {threshold: .12});
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
const orderPreview = document.querySelector('[data-order-preview]');
if (orderPreview) {
  document.querySelector('[data-order-preview-toggle]')?.addEventListener('click', () => orderPreview.classList.toggle('open'));
  document.querySelector('[data-order-preview-close]')?.addEventListener('click', () => orderPreview.classList.remove('open'));
}
const prepBoard = document.querySelector('[data-prep-board]');
if (prepBoard) {
  const key = 'pizzaVittiLatestOrder';
  const soundKey = 'pizzaVittiPrepSound';
  const soundButton = document.querySelector('[data-prep-sound]');
  const speak = text => {
    try {
      const audio = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audio.createOscillator();
      const gain = audio.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(.001, audio.currentTime);
      gain.gain.exponentialRampToValueAtTime(.25, audio.currentTime + .03);
      gain.gain.exponentialRampToValueAtTime(.001, audio.currentTime + .55);
      oscillator.connect(gain).connect(audio.destination);
      oscillator.start();
      oscillator.stop(audio.currentTime + .6);
    } catch (error) {}
    if ('speechSynthesis' in window) window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  };
  const setSoundLabel = () => {
    if (soundButton) soundButton.textContent = localStorage.getItem(soundKey) === 'on' ? 'Son actif' : 'Activer son';
  };
  soundButton?.addEventListener('click', () => {
    localStorage.setItem(soundKey, 'on');
    setSoundLabel();
    speak('Son active. Vous recevrez une alerte a chaque nouvelle commande.');
  });
  setSoundLabel();
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
        if (localStorage.getItem(soundKey) === 'on') speak('Nouvelle commande recue.');
        setTimeout(() => window.location.reload(), 1200);
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
