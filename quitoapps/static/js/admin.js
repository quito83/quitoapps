// QuitoApps - interactividad para el panel de administración

(function() {
  // 1. Confirmaciones al borrar
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', (e) => {
      const msg = form.getAttribute('data-confirm') || '¿Confirmar acción?';
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // 2. Generador automático de slug en taxonomía (nombre -> slug)
  const nameInput = document.querySelector('[data-slug-source]');
  const slugInput = document.getElementById('slug');
  if (nameInput && slugInput && !slugInput.value) {
    nameInput.addEventListener('input', () => {
      const val = nameInput.value.toLowerCase().trim()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // Quitar tildes
        .replace(/[^a-z0-9]+/g, '-')                      // Solo letras, nums y guiones
        .replace(/^-+|-+$/g, '');
      slugInput.value = val;
    });
  }
})();
