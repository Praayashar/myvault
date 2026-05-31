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

// Auto-check and send renewal reminders via EmailJS on dashboard load
async function checkAndSendReminders() {
  const EMAILJS_PUBLIC_KEY = document.body.dataset.emailjsKey;
  const EMAILJS_SERVICE_ID = document.body.dataset.emailjsService;
  const EMAILJS_REMINDER_TEMPLATE = document.body.dataset.emailjsReminder;

  if (!EMAILJS_PUBLIC_KEY || !EMAILJS_SERVICE_ID || !EMAILJS_REMINDER_TEMPLATE) return;

  try {
    const res = await fetch('/reminders/pending');
    const data = await res.json();
    if (!data.reminders || !data.reminders.length) return;

    // Load EmailJS if not loaded
    if (typeof emailjs === 'undefined') {
      await new Promise((resolve) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js';
        s.onload = resolve;
        document.head.appendChild(s);
      });
    }

    emailjs.init(EMAILJS_PUBLIC_KEY);

    for (const reminder of data.reminders) {
      try {
        await emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_REMINDER_TEMPLATE, reminder);
        await fetch('/reminders/mark-sent/' + reminder.id, { method: 'POST' });
        console.log('Reminder sent for:', reminder.sub_name);
      } catch (e) {
        console.error('Failed to send reminder:', e);
      }
    }
  } catch (e) {
    // Silent fail — don't disrupt the user
  }
}

// Run on dashboard page only
if (window.location.pathname === '/dashboard') {
  checkAndSendReminders();
}

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
