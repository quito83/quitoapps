// QuitoApps - interactividad mínima para el sitio público

(function() {
  // 1. Selector de modo claro/oscuro
  const themeToggles = document.querySelectorAll('.theme-toggle');
  themeToggles.forEach(btn => {
    btn.addEventListener('click', () => {
      const current = document.documentElement.dataset.theme;
      let next = 'dark';
      if (current === 'dark') {
        next = 'light';
      } else if (current === 'light') {
        next = 'dark';
      } else {
        // Si no está fijado, revisamos la preferencia del sistema
        const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        next = isDark ? 'light' : 'dark';
      }
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem('theme', next);
      } catch (e) {}
    });
  });

  // 2. Menú responsive (hamburguesa)
  const navToggle = document.querySelector('.nav-toggle');
  const siteNav = document.getElementById('site-nav');
  if (navToggle && siteNav) {
    navToggle.addEventListener('click', () => {
      const open = siteNav.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // 3. Auto-submit en filtros de catálogo cuando cambia select
  const autoSubmitForms = document.querySelectorAll('form[data-autosubmit]');
  autoSubmitForms.forEach(form => {
    const selects = form.querySelectorAll('select');
    selects.forEach(sel => {
      sel.addEventListener('change', () => form.submit());
    });
  });

  // 4. Lightbox de capturas
  const lightbox = document.querySelector('dialog.lightbox');
  const galleryItems = document.querySelectorAll('[data-gallery] .gallery-item');
  if (lightbox && galleryItems.length > 0) {
    const lbImg = lightbox.querySelector('img');
    const lbClose = lightbox.querySelector('.lb-close');
    const lbPrev = lightbox.querySelector('.lb-prev');
    const lbNext = lightbox.querySelector('.lb-next');
    let currentIndex = 0;
    const images = Array.from(galleryItems).map(item => ({
      src: item.getAttribute('href'),
      alt: item.querySelector('img') ? item.querySelector('img').alt : ''
    }));

    function showImage(idx) {
      if (idx < 0) idx = images.length - 1;
      if (idx >= images.length) idx = 0;
      currentIndex = idx;
      lbImg.src = images[currentIndex].src;
      lbImg.alt = images[currentIndex].alt;
    }

    galleryItems.forEach((item, idx) => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        showImage(idx);
        lightbox.showModal();
      });
    });

    if (lbClose) {
      lbClose.addEventListener('click', () => lightbox.close());
    }
    if (lbPrev) {
      lbPrev.addEventListener('click', (e) => {
        e.stopPropagation();
        showImage(currentIndex - 1);
      });
    }
    if (lbNext) {
      lbNext.addEventListener('click', (e) => {
        e.stopPropagation();
        showImage(currentIndex + 1);
      });
    }
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) {
        lightbox.close();
      }
    });
    document.addEventListener('keydown', (e) => {
      if (!lightbox.open) return;
      if (e.key === 'ArrowLeft') showImage(currentIndex - 1);
      if (e.key === 'ArrowRight') showImage(currentIndex + 1);
    });
  }
})();

// 4. Héroe interactivo: parallax + red de partículas que reacciona al cursor
(function() {
  const scene = document.querySelector('[data-hero-scene]');
  if (!scene) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = window.matchMedia('(pointer: fine)').matches;
  const layers = Array.from(scene.querySelectorAll('.hero-layer'));
  const canvas = scene.querySelector('.hero-net');
  const ctx = canvas ? canvas.getContext('2d') : null;

  // --- Parallax (solo con puntero preciso y sin reduce-motion) ---
  if (fine && !reduce) {
    let raf = null;
    const onMove = (e) => {
      const r = scene.getBoundingClientRect();
      const nx = ((e.clientX - r.left) / r.width - 0.5) * 2;   // -1..1
      const ny = ((e.clientY - r.top) / r.height - 0.5) * 2;
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = null;
        scene.style.transform = `rotateY(${nx * 4}deg) rotateX(${-ny * 4}deg)`;
        layers.forEach((l) => {
          const d = parseFloat(l.dataset.depth) || 0;
          l.style.transform = `translate(${-nx * d}px, ${-ny * d}px)`;
        });
      });
    };
    scene.addEventListener('pointermove', onMove);
    scene.addEventListener('pointerleave', () => {
      scene.style.transform = '';
      layers.forEach((l) => { l.style.transform = ''; });
    });
  }

  // --- Red de partículas en canvas ---
  if (!ctx) return;

  let w = 0, h = 0, dpr = 1;
  let particles = [];
  const pointer = { x: -999, y: -999, on: false };

  function netColor() {
    const c = getComputedStyle(scene).getPropertyValue('--hero-net').trim();
    return c || '#ea580c';
  }
  let color = netColor();

  function resize() {
    const r = scene.getBoundingClientRect();
    if (!r.width || !r.height) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = r.width; h = r.height;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.max(22, Math.min(60, Math.round((w * h) / 7000)));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      r: Math.random() * 1.6 + 1.1,
    }));
    color = netColor();
  }

  function hexToRgb(hex) {
    const m = hex.replace('#', '');
    const n = m.length === 3 ? m.split('').map((c) => c + c).join('') : m;
    const int = parseInt(n, 16);
    return `${(int >> 16) & 255}, ${(int >> 8) & 255}, ${int & 255}`;
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    const rgb = hexToRgb(color);
    const LINK = 118;

    for (const p of particles) {
      if (!reduce) { p.x += p.vx; p.y += p.vy; }
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
      p.x = Math.max(0, Math.min(w, p.x));
      p.y = Math.max(0, Math.min(h, p.y));

      if (pointer.on) {
        const dx = p.x - pointer.x, dy = p.y - pointer.y;
        const dist = Math.hypot(dx, dy);
        if (dist < 150 && dist > 0.1) {
          const f = (150 - dist) / 150 * 0.6;
          p.x += (dx / dist) * f;
          p.y += (dy / dist) * f;
        }
      }
    }

    for (let i = 0; i < particles.length; i++) {
      const a = particles[i];
      for (let j = i + 1; j < particles.length; j++) {
        const b = particles[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < LINK) {
          ctx.strokeStyle = `rgba(${rgb}, ${(1 - d / LINK) * 0.5})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
      if (pointer.on) {
        const d = Math.hypot(a.x - pointer.x, a.y - pointer.y);
        if (d < 170) {
          ctx.strokeStyle = `rgba(${rgb}, ${(1 - d / 170) * 0.8})`;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(pointer.x, pointer.y);
          ctx.stroke();
        }
      }
      ctx.fillStyle = `rgba(${rgb}, 0.9)`;
      ctx.beginPath();
      ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
      ctx.fill();
    }

    if (!reduce) rafDraw = requestAnimationFrame(draw);
  }

  let rafDraw = null;
  scene.addEventListener('pointermove', (e) => {
    const r = scene.getBoundingClientRect();
    pointer.x = e.clientX - r.left;
    pointer.y = e.clientY - r.top;
    pointer.on = true;
    if (reduce) draw();
  });
  scene.addEventListener('pointerleave', () => { pointer.on = false; if (reduce) draw(); });

  if ('ResizeObserver' in window) {
    new ResizeObserver(() => { resize(); if (reduce) draw(); }).observe(scene);
  } else {
    window.addEventListener('resize', resize);
  }

  resize();
  if (reduce) { draw(); } else { rafDraw = requestAnimationFrame(draw); }
})();
