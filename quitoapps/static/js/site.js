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
