/**
 * MyVault - Google Apps Script
 * ----------------------------------------------------------------------
 * This is what makes reminders automatic. It runs on Google's servers on a
 * timer, so it works even when nobody opens the app, and it wakes the
 * sleeping Render instance and keeps the free Supabase project active.
 *
 * SETUP (about 5 minutes)
 *  1. Go to script.google.com -> New project. Name it "MyVault Reminders".
 *  2. Delete the sample code and paste this whole file in.
 *  3. Edit APP_URL and CRON_SECRET below to match your Render settings.
 *  4. Save, then Run -> runDailyReminders once. Google asks for permission
 *     to send email as you; approve it. (On the "unverified app" screen,
 *     choose Advanced -> Go to MyVault Reminders.)
 *  5. Run -> setupTriggers once. That creates all three timers.
 *
 * To check it later: Executions in the left sidebar shows every run.
 * ----------------------------------------------------------------------
 */

// ===== EDIT THESE TWO =====================================================
const APP_URL     = 'https://myvault-oq8m.onrender.com';
const CRON_SECRET = 'PASTE_THE_SAME_CRON_SECRET_YOU_PUT_IN_RENDER';
// ==========================================================================

// Optional: a Google Drive folder name for weekly backups.
const BACKUP_FOLDER = 'MyVault Backups';


/**
 * Creates the timers. Run this ONCE, by hand, after the first test run.
 */
function setupTriggers() {
  // Clear any existing triggers so running this twice is harmless.
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));

  // Daily reminders, 9-10 AM IST.
  ScriptApp.newTrigger('runDailyReminders')
    .timeBased().atHour(9).everyDays(1)
    .inTimezone('Asia/Kolkata').create();

  // Monthly report, on the 1st.
  ScriptApp.newTrigger('runMonthlyReport')
    .timeBased().onMonthDay(1).atHour(10)
    .inTimezone('Asia/Kolkata').create();

  // Weekly backup to Google Drive, Sunday night.
  ScriptApp.newTrigger('runWeeklyBackup')
    .timeBased().onWeekDay(ScriptApp.WeekDay.SUNDAY).atHour(23)
    .inTimezone('Asia/Kolkata').create();

  Logger.log('Triggers created: daily reminders, monthly report, weekly backup.');
}


/**
 * Daily: fetch what is due and email a single digest per person.
 */
function runDailyReminders() {
  const data = callApp('/cron/reminders');
  if (!data || !data.success) {
    Logger.log('Could not fetch reminders: ' + JSON.stringify(data));
    return;
  }
  if (!data.digests || data.digests.length === 0) {
    Logger.log('Nothing due today.');
    return;
  }

  const delivered = [];

  data.digests.forEach(function (d) {
    try {
      MailApp.sendEmail({
        to: d.to_email,
        subject: d.subject,
        body: buildReminderText(d),
        htmlBody: buildReminderHtml(d),
        name: 'MyVault'
      });
      delivered.push(d);
      Logger.log('Sent ' + d.count + ' reminder(s) to ' + d.to_email);
    } catch (err) {
      Logger.log('FAILED for ' + d.to_email + ': ' + err);
    }
  });

  // Tell the app what actually went out, so nothing is sent twice.
  if (delivered.length) {
    callApp('/cron/reminders/sent', 'post', { digests: delivered });
  }
}


function buildReminderText(d) {
  return 'Hello ' + d.to_name + ',\n\n' +
         'These things are coming up:\n\n' +
         d.body + '\n\n' +
         'Open MyVault: ' + APP_URL + '\n\n' +
         '- MyVault';
}


function buildReminderHtml(d) {
  const rows = d.items.map(function (i) {
    const urgent = (i.when === 'today' || i.when === 'tomorrow');
    return '<tr>' +
      '<td style="padding:10px 12px;border-bottom:1px solid #e6e6e6;font-size:16px;">' +
        '<strong>' + escapeHtml(i.title) + '</strong>' +
        (i.detail ? '<br><span style="color:#666;font-size:14px;">' + escapeHtml(i.detail) + '</span>' : '') +
      '</td>' +
      '<td style="padding:10px 12px;border-bottom:1px solid #e6e6e6;text-align:right;white-space:nowrap;font-size:15px;' +
        (urgent ? 'color:#B3261E;font-weight:700;' : 'color:#444;') + '">' +
        escapeHtml(i.when) + '<br><span style="color:#888;font-size:13px;">' + escapeHtml(i.due_date_str) + '</span>' +
      '</td></tr>';
  }).join('');

  return '' +
    '<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:560px;margin:0 auto;">' +
      '<div style="background:#1B4332;color:#fff;padding:18px 20px;border-radius:12px 12px 0 0;">' +
        '<div style="font-size:20px;font-weight:700;">MyVault</div>' +
        '<div style="font-size:14px;opacity:.85;">Hello ' + escapeHtml(d.to_name) + ', here is what is coming up</div>' +
      '</div>' +
      '<table style="width:100%;border-collapse:collapse;background:#fff;">' + rows + '</table>' +
      '<div style="padding:18px 20px;background:#f6f8f6;border-radius:0 0 12px 12px;text-align:center;">' +
        '<a href="' + APP_URL + '" style="display:inline-block;background:#1B4332;color:#fff;' +
        'padding:13px 26px;border-radius:9px;text-decoration:none;font-size:16px;font-weight:600;">Open MyVault</a>' +
      '</div>' +
    '</div>';
}


/**
 * Monthly: last month's summary, on the 1st.
 */
function runMonthlyReport() {
  const data = callApp('/cron/monthly-report');
  if (!data || !data.success) {
    Logger.log('Could not fetch monthly report: ' + JSON.stringify(data));
    return;
  }

  (data.reports || []).forEach(function (r) {
    const body =
      'Hello ' + r.to_name + ',\n\n' +
      'MyVault report for ' + r.month_name + '\n\n' +
      'Income       : ' + r.monthly_income + '\n' +
      'Expenses     : ' + r.monthly_expense + '\n' +
      r.balance_label + '       : ' + r.balance + '\n' +
      'Savings rate : ' + r.savings_rate + '\n\n' +
      'Top categories:\n' + r.top_categories + '\n\n' +
      'Open MyVault: ' + APP_URL + '\n\n- MyVault';
    try {
      MailApp.sendEmail({ to: r.to_email, subject: r.subject, body: body, name: 'MyVault' });
      Logger.log('Monthly report sent to ' + r.to_email);
    } catch (err) {
      Logger.log('Monthly report FAILED for ' + r.to_email + ': ' + err);
    }
  });
}


/**
 * Weekly: full JSON backup into Google Drive.
 * Supabase's free tier takes no backups of its own, so this is the safety net.
 * Password vault entries in this file are encrypted - VAULT_KEY is needed to
 * read them, and that lives only in Render and in your own records.
 */
function runWeeklyBackup() {
  const data = callApp('/cron/backup');
  if (!data) {
    Logger.log('Backup fetch failed.');
    return;
  }

  let folder;
  const found = DriveApp.getFoldersByName(BACKUP_FOLDER);
  folder = found.hasNext() ? found.next() : DriveApp.createFolder(BACKUP_FOLDER);

  const stamp = Utilities.formatDate(new Date(), 'Asia/Kolkata', 'yyyy-MM-dd');
  folder.createFile('myvault-backup-' + stamp + '.json',
                    JSON.stringify(data, null, 2),
                    MimeType.PLAIN_TEXT);
  Logger.log('Backup saved: myvault-backup-' + stamp + '.json');

  // Keep the last 8 weeks only.
  const files = [];
  const it = folder.getFiles();
  while (it.hasNext()) files.push(it.next());
  files.sort(function (a, b) { return b.getDateCreated() - a.getDateCreated(); });
  files.slice(8).forEach(function (f) { f.setTrashed(true); });
}


/**
 * Shared HTTP helper.
 */
function callApp(path, method, payload) {
  const sep = path.indexOf('?') === -1 ? '?' : '&';
  const url = APP_URL + path + sep + 'key=' + encodeURIComponent(CRON_SECRET);

  const options = {
    method: method || 'get',
    muteHttpExceptions: true,
    // The free Render instance may be asleep; the first call wakes it and
    // can take close to a minute.
    followRedirects: true
  };
  if (payload) {
    options.contentType = 'application/json';
    options.payload = JSON.stringify(payload);
  }

  // Retry once, because a cold start sometimes times out the first attempt.
  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const res = UrlFetchApp.fetch(url, options);
      const code = res.getResponseCode();
      if (code === 200) return JSON.parse(res.getContentText());
      Logger.log('HTTP ' + code + ' from ' + path + ': ' + res.getContentText().slice(0, 300));
      if (code === 401) return null;  // wrong secret - retrying will not help
    } catch (err) {
      Logger.log('Attempt ' + attempt + ' to ' + path + ' failed: ' + err);
    }
    if (attempt === 1) Utilities.sleep(45000);  // let the instance wake up
  }
  return null;
}


function escapeHtml(s) {
  return String(s === null || s === undefined ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}


/**
 * Handy for testing: shows what WOULD be sent, without sending anything.
 */
function previewReminders() {
  const data = callApp('/cron/reminders');
  Logger.log(JSON.stringify(data, null, 2));
}
