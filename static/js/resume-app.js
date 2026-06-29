/* ============================================================
   刘俊 · 简历  —  双语切换 + 滚动动效
   ZH 为 DOM 默认文本，EN 存于 data-en；切换时互换
   ============================================================ */
(function () {
  'use strict';

  /* ---------- i18n ---------- */
  var nodes = document.querySelectorAll('[data-en]');
  // cache original ZH content
  nodes.forEach(function (el) { el.setAttribute('data-zh', el.innerHTML); });

  function setLang(lang) {
    var en = lang === 'en';
    document.documentElement.lang = en ? 'en' : 'zh-CN';
    nodes.forEach(function (el) {
      el.innerHTML = en ? el.getAttribute('data-en') : el.getAttribute('data-zh');
    });
    document.querySelectorAll('#langToggle button').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    });
    try { localStorage.setItem('lj_lang', lang); } catch (e) {}
  }

  document.querySelectorAll('#langToggle button').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.getAttribute('data-lang')); });
  });

  var saved = 'zh';
  try { saved = localStorage.getItem('lj_lang') || 'zh'; } catch (e) {}
  setLang(saved);

  /* ---------- reveal on scroll ---------- */
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) {
    document.querySelectorAll('.reveal').forEach(function (el) { el.classList.add('in'); });
    document.querySelectorAll('.fill').forEach(function (f) { f.style.width = f.getAttribute('data-pct') + '%'; });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        // animate skill bars within
        e.target.querySelectorAll('.fill').forEach(function (f) {
          f.style.width = f.getAttribute('data-pct') + '%';
        });
        io.unobserve(e.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
  }

  /* ---------- active nav link ---------- */
  var sections = document.querySelectorAll('section[id], header[id]');
  var navlinks = {};
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    navlinks[a.getAttribute('href').slice(1)] = a;
  });
  if ('IntersectionObserver' in window) {
    var navIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var a = navlinks[e.target.id];
        if (a && e.isIntersecting) {
          Object.values(navlinks).forEach(function (l) { l.style.color = ''; });
          a.style.color = 'var(--accent)';
        }
      });
    }, { threshold: 0.5 });
    sections.forEach(function (s) { navIO.observe(s); });
  }
})();

/* ---- Demo modal ---- */
(function () {
  var modal = document.getElementById('demoModal');
  if (!modal) return;
  var frame = document.getElementById('demoModalFrame');
  var title = document.getElementById('demoModalTitle');
  var openLink = document.getElementById('demoModalOpen');

  function open(url, label) {
    frame.src = url;
    title.textContent = (label || 'Demo') + ' · Live Demo';
    openLink.href = url;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function close() {
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    frame.src = 'about:blank';
  }

  document.querySelectorAll('[data-demo]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      open(btn.getAttribute('data-demo'), btn.getAttribute('data-demo-title'));
    });
  });
  modal.querySelectorAll('[data-demo-close]').forEach(function (el) {
    el.addEventListener('click', close);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal.classList.contains('open')) close();
  });
})();
