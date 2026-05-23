/**
 * Dark / light theme toggle — persists in localStorage and sets data-bs-theme on <html>.
 */
(function () {
  const key = 'dlms-theme';
  const root = document.documentElement;
  const stored = localStorage.getItem(key);
  if (stored === 'dark' || stored === 'light') {
    root.setAttribute('data-bs-theme', stored);
  }
  const btn = document.getElementById('themeToggle');
  const icon = document.getElementById('themeIcon');
  function syncIcon() {
    const t = root.getAttribute('data-bs-theme') || 'light';
    if (icon) {
      icon.className = t === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars';
    }
  }
  syncIcon();
  if (btn) {
    btn.addEventListener('click', function () {
      const next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-bs-theme', next);
      localStorage.setItem(key, next);
      syncIcon();
    });
  }
})();
