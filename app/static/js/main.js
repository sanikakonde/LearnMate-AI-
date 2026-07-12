/**
 * LearnMate AI – Main JavaScript
 * Theme toggle, sidebar, toast notifications, loading overlay, global utilities
 */

// ─────────────────────────────────────────────────────────
// THEME MANAGEMENT
// ─────────────────────────────────────────────────────────
function initTheme() {
  const stored = localStorage.getItem('learnmate-theme');
  const htmlEl = document.documentElement;

  // Server-side theme preference takes priority on first load
  const serverTheme = htmlEl.getAttribute('data-theme') || 'dark';
  const theme = stored || serverTheme;

  htmlEl.setAttribute('data-theme', theme);
  updateThemeUI(theme);
}

function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('learnmate-theme', next);
  updateThemeUI(next);

  // Persist to server preference if logged in
  const csrfEl = document.querySelector('input[name="csrf_token"]');
  if (csrfEl) {
    fetch('/auth/api/theme', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfEl.value },
      body: JSON.stringify({ theme: next }),
    }).catch(() => {});
  }
}

function updateThemeUI(theme) {
  const isDark = theme === 'dark';
  const themeIcon = document.getElementById('themeIcon');
  const themeLabel = document.getElementById('themeLabel');
  const topIcon = document.getElementById('topThemeIcon');

  // Highlight.js theme
  const hljsLink = document.getElementById('hljs-theme');
  if (hljsLink) {
    hljsLink.href = isDark
      ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css'
      : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css';
  }

  if (themeIcon) themeIcon.className = isDark ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
  if (themeLabel) themeLabel.textContent = isDark ? 'Dark Mode' : 'Light Mode';
  if (topIcon) topIcon.className = isDark ? 'bi bi-circle-half' : 'bi bi-circle-half';
}

// ─────────────────────────────────────────────────────────
// SIDEBAR
// ─────────────────────────────────────────────────────────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (!sidebar) return;
  const isOpen = sidebar.classList.contains('open');
  if (isOpen) {
    closeSidebar();
  } else {
    sidebar.classList.add('open');
    overlay?.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  sidebar?.classList.remove('open');
  overlay?.classList.remove('show');
  document.body.style.overflow = '';
}

// ─────────────────────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 5000) {
  const container = document.querySelector('.toast-container');
  if (!container) {
    // Fallback
    console.log(`[${type.toUpperCase()}] ${message}`);
    return;
  }

  const iconMap = {
    success: 'check-circle-fill',
    danger: 'exclamation-triangle-fill',
    warning: 'exclamation-triangle-fill',
    info: 'info-circle-fill',
  };
  const icon = iconMap[type] || 'info-circle-fill';
  const typeClass = type === 'error' ? 'danger' : type;

  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center text-bg-${typeClass} border-0`;
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body fw-semibold">
        <i class="bi bi-${icon} me-2"></i>${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;
  container.appendChild(toastEl);

  const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: duration });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// ─────────────────────────────────────────────────────────
// LOADING OVERLAY
// ─────────────────────────────────────────────────────────
function showLoading(text = 'Processing with IBM Granite...') {
  const overlay = document.getElementById('loadingOverlay');
  const textEl = document.getElementById('loadingText');
  if (overlay) overlay.style.display = 'flex';
  if (textEl) textEl.textContent = text;
}

function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) overlay.style.display = 'none';
}

// ─────────────────────────────────────────────────────────
// GLOBAL UTILITIES
// ─────────────────────────────────────────────────────────

/**
 * Auto-resize textarea based on content.
 */
function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 200) + 'px';
}

/**
 * Debounce function
 */
function debounce(fn, delay = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

/**
 * Format bytes
 */
function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!', 'success', 2000);
  } catch {
    showToast('Copy failed.', 'warning', 2000);
  }
}

// ─────────────────────────────────────────────────────────
// CSRF TOKEN HELPER
// ─────────────────────────────────────────────────────────
function getCsrfToken() {
  const metaEl = document.querySelector('meta[name="csrf-token"]');
  if (metaEl) return metaEl.getAttribute('content');
  const inputEl = document.querySelector('input[name="csrf_token"]');
  if (inputEl) return inputEl.value;
  return window.CSRF_TOKEN || '';
}

// ─────────────────────────────────────────────────────────
// DOM READY INITIALIZATIONS
// ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  // Highlight.js
  if (typeof hljs !== 'undefined') {
    document.querySelectorAll('pre code').forEach((block) => {
      hljs.highlightElement(block);
    });
  }

  // Add now variable for templates
  window.__now = new Date();

  // Re-init toasts from Flash messages (rendered in base.html)
  document.querySelectorAll('.toast').forEach((t) => {
    if (!bootstrap.Toast.getInstance(t)) {
      new bootstrap.Toast(t, { autohide: true, delay: 5000 }).show();
    }
  });

  // Mobile: close sidebar on nav-item click
  document.querySelectorAll('.nav-item').forEach((link) => {
    link.addEventListener('click', () => {
      if (window.innerWidth < 768) closeSidebar();
    });
  });

  // Keyboard shortcut: Ctrl+/ → focus tutor input
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      const tutorInput = document.getElementById('chatInput');
      if (tutorInput) {
        e.preventDefault();
        tutorInput.focus();
      }
    }
  });
});

// Inject `now` into Jinja2-rendered pages via a fallback data attribute
// (the dashboard template already uses a server-side `now` variable)
