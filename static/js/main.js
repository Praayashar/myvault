// ===========================================================================
// Global fetch wrapper
//
// Two problems this solves across every form in the app:
//   1. CSRF - attaches the token to every same-origin POST automatically.
//   2. Silent failures - every form used to do
//          if ((await res.json()).success) location.reload();
//      with no else branch, so a failed save did nothing at all: no message,
//      no hint, nothing. Now any failure shows a visible message.
//
// Doing it here means all 30 fetch calls are covered without touching each
// template, and new ones are covered automatically.
// ===========================================================================
(function () {
  const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const nativeFetch = window.fetch.bind(window);

  function showError(message) {
    document.querySelectorAll('.mv-error-toast').forEach(el => el.remove());
    const box = document.createElement('div');
    box.className = 'mv-error-toast';
    box.innerHTML =
      '<strong>Could not save</strong><span>' +
      String(message || 'Something went wrong. Please try again.')
        .replace(/</g, '&lt;') +
      '</span><button aria-label="Close">&times;</button>';
    document.body.appendChild(box);
    box.querySelector('button').addEventListener('click', () => box.remove());
    setTimeout(() => box.remove(), 9000);
  }
  window.myvaultShowError = showError;

  window.fetch = async function (input, init) {
    init = init || {};
    const url = (typeof input === 'string') ? input : (input && input.url) || '';
    const sameOrigin = url.startsWith('/') || url.startsWith(window.location.origin);
    const method = (init.method || 'GET').toUpperCase();

    if (sameOrigin && method !== 'GET' && method !== 'HEAD' && CSRF_TOKEN) {
      const headers = new Headers(init.headers || {});
      if (!headers.has('X-CSRFToken')) headers.set('X-CSRFToken', CSRF_TOKEN);
      init = Object.assign({}, init, { headers });
    }

    let res;
    try {
      res = await nativeFetch(input, init);
    } catch (networkError) {
      if (sameOrigin && method !== 'GET') {
        showError('No internet connection. Please check and try again.');
      }
      throw networkError;
    }

    // Inspect a copy so the caller still gets an unread body.
    if (sameOrigin && method !== 'GET') {
      try {
        const peek = await res.clone().json();
        if (peek && peek.success === false) {
          showError(peek.message || 'Please check what you entered and try again.');
        }
      } catch (e) {
        if (!res.ok) {
          showError('The server had a problem (error ' + res.status +
                    '). Please refresh the page and try again.');
          // Stop `await res.json()` in the caller from throwing on an HTML
          // error page, which used to freeze the form with no feedback.
          return new Response(
            JSON.stringify({ success: false, message: 'Server error ' + res.status }),
            { status: res.status, headers: { 'Content-Type': 'application/json' } }
          );
        }
      }
    }
    return res;
  };
})();

// More Menu
const moreMenuBtn = document.getElementById('moreMenuBtn');
const moreMenu = document.getElementById('moreMenu');
const closeMM = document.getElementById('closeMM');

if (moreMenuBtn) {
  moreMenuBtn.addEventListener('click', (e) => {
    e.preventDefault();
    moreMenu.classList.add('active');
  });
}
if (closeMM) {
  closeMM.addEventListener('click', () => moreMenu.classList.remove('active'));
}
if (moreMenu) {
  moreMenu.addEventListener('click', (e) => {
    if (e.target === moreMenu) moreMenu.classList.remove('active');
  });
}

// Quick Add Modal
const quickAddBtn = document.getElementById('quickAddBtn');
const quickAddModal = document.getElementById('quickAddModal');
const closeModal = document.getElementById('closeModal');
const qaSubmit = document.getElementById('qa-submit');
const qaDate = document.getElementById('qa-date');

if (qaDate) {
  qaDate.value = new Date().toISOString().split('T')[0];
}

if (quickAddBtn) {
  quickAddBtn.addEventListener('click', (e) => {
    e.preventDefault();
    quickAddModal.classList.add('active');
  });
}

if (closeModal) {
  closeModal.addEventListener('click', () => {
    quickAddModal.classList.remove('active');
  });
}

if (quickAddModal) {
  quickAddModal.addEventListener('click', (e) => {
    if (e.target === quickAddModal) quickAddModal.classList.remove('active');
  });
}

if (qaSubmit) {
  qaSubmit.addEventListener('click', async () => {
    const amount = document.getElementById('qa-amount').value;
    const category = document.getElementById('qa-category').value;
    const payment_method = document.getElementById('qa-payment').value;
    const description = document.getElementById('qa-desc').value;
    const date = document.getElementById('qa-date').value;

    if (!amount || parseFloat(amount) <= 0) {
      alert('Please enter a valid amount');
      return;
    }

    qaSubmit.textContent = 'Adding...';
    qaSubmit.disabled = true;

    try {
      const res = await fetch('/quick-add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, category, payment_method, description, date })
      });
      const data = await res.json();
      if (data.success) {
        quickAddModal.classList.remove('active');
        document.getElementById('qa-amount').value = '';
        document.getElementById('qa-desc').value = '';
        showToast('Expense added!');
        setTimeout(() => location.reload(), 800);
      } else {
        alert('Error: ' + data.message);
      }
    } catch (err) {
      alert('Something went wrong. Please try again.');
    } finally {
      qaSubmit.textContent = 'Add Expense';
      qaSubmit.disabled = false;
    }
  });
}

// Toast notification
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `flash flash-${type}`;
  toast.style.cssText = 'position:fixed;top:70px;left:16px;right:16px;z-index:400;animation:fadeIn 0.3s';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// Auto-dismiss flash messages
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => {
    el.style.transition = 'opacity 0.5s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 500);
  });
}, 3000);

// Renewal reminders are now sent server-side, triggered daily by Google
// Apps Script (see apps_script.gs). The old browser-based sender only ran
// when somebody happened to open the dashboard on exactly the right day.

// ===== SWIPE TO DELETE =====
function initSwipeToDelete(selector, deleteCallback) {
  const items = document.querySelectorAll(selector);
  items.forEach(item => {
    let startX = 0;
    let currentX = 0;
    let isDragging = false;

    item.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      isDragging = true;
    }, { passive: true });

    item.addEventListener('touchmove', (e) => {
      if (!isDragging) return;
      currentX = e.touches[0].clientX - startX;
      if (currentX < -30) item.classList.add('swiped');
      else item.classList.remove('swiped');
    }, { passive: true });

    item.addEventListener('touchend', () => {
      isDragging = false;
      if (currentX < -80) {
        // Confirm and delete
        if (confirm('Delete this item?')) {
          deleteCallback(item);
        } else {
          item.classList.remove('swiped');
        }
      } else {
        item.classList.remove('swiped');
      }
      currentX = 0;
    });
  });
}

// ===== VOICE NOTE FOR EXPENSE =====
let recognition = null;
let isRecording = false;

function initVoiceNote(btnId, targetFieldId, statusId) {
  const btn = document.getElementById(btnId);
  if (!btn) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    btn.title = 'Voice not supported on this browser';
    btn.style.opacity = '0.5';
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = 'en-IN';
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    const field = document.getElementById(targetFieldId);
    if (field) field.value = transcript;
    const status = document.getElementById(statusId);
    if (status) { status.textContent = '"' + transcript + '"'; status.style.display = 'block'; }
    // Try to parse amount from voice
    const amountMatch = transcript.match(/(\d+)/);
    const amountField = document.getElementById('qa-amount') || document.getElementById('exp-amount');
    if (amountMatch && amountField && !amountField.value) {
      amountField.value = amountMatch[1];
    }
  };

  recognition.onend = () => {
    isRecording = false;
    btn.classList.remove('recording');
    btn.textContent = '🎤';
  };

  recognition.onerror = () => {
    isRecording = false;
    btn.classList.remove('recording');
    btn.textContent = '🎤';
  };

  btn.addEventListener('click', () => {
    if (isRecording) {
      recognition.stop();
    } else {
      isRecording = true;
      btn.classList.add('recording');
      btn.textContent = '⏹️';
      recognition.start();
    }
  });
}

// ===== WHATSAPP SHARE =====
function shareOnWhatsApp(text) {
  const encoded = encodeURIComponent(text);
  window.open('https://wa.me/?text=' + encoded, '_blank');
}

function generateReportText(data) {
  return `*MyVault Report — ${data.month}*\n\n` +
    `💰 Income: ₹${data.income}\n` +
    `💸 Expenses: ₹${data.expense}\n` +
    `✅ Saved: ₹${data.balance}\n\n` +
    `📊 Top Categories:\n${data.categories}\n\n` +
    `_Sent from MyVault_`;
}

// Init voice on quick add modal
document.addEventListener('DOMContentLoaded', () => {
  initVoiceNote('voiceBtn', 'qa-desc', 'voiceStatus');
});
