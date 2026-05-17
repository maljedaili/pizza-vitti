document.addEventListener('click', e => {
  if (e.target.matches('[data-nav]')) document.body.classList.toggle('nav-open');
  if (e.target.matches('[data-bot-toggle]')) document.querySelector('[data-bot]').classList.toggle('open');
});
const observer = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) entry.target.classList.add('show');
}), {threshold: .12});
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
const typeSelect = document.querySelector('[data-customer-type]');
const proBox = document.querySelector('[data-pro-box]');
if (typeSelect && proBox) {
  const togglePro = () => { proBox.hidden = typeSelect.value !== 'professionnel' && !proBox.dataset.force; };
  typeSelect.addEventListener('change', togglePro);
  togglePro();
}
const botForm = document.querySelector('[data-bot-form]');
if (botForm) {
  botForm.addEventListener('submit', async e => {
    e.preventDefault();
    const input = botForm.querySelector('input[name="message"]');
    const log = document.querySelector('[data-bot-log]');
    const text = input.value.trim();
    if (!text) return;
    log.insertAdjacentHTML('beforeend', `<p><strong>Vous :</strong> ${text.replace(/[<>]/g,'')}</p>`);
    const formData = new FormData(botForm);
    const res = await fetch(botForm.dataset.url, {method:'POST', body:formData, headers:{'X-Requested-With':'XMLHttpRequest'}});
    const data = await res.json();
    log.insertAdjacentHTML('beforeend', `<p><strong>Assistant :</strong> ${data.answer}</p>`);
    log.scrollTop = log.scrollHeight;
    input.value = '';
  });
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
