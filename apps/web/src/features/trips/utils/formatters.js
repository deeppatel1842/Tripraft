// Purpose: Provides formatters logic and exports for apps\web\src\features\trips\utils.
/**
 * Formatting helpers for the Group Planner UI.
 */

export function formatDate(dateStr) {
  let date;
  if (dateStr instanceof Date || typeof dateStr === 'number') {
    date = new Date(dateStr);
  } else {
    const text = String(dateStr ?? '').trim();
    if (!text) return '';
    const dateOnly = text.split('T')[0];
    date = new Date(dateOnly + 'T00:00:00');
  }
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

export function formatTime(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

export function formatDateRange(startStr, endStr) {
  if (!startStr) return '';
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const s = new Date(startStr + 'T00:00:00');
  const end = endStr ? new Date(endStr + 'T00:00:00') : null;
  const sLabel = months[s.getMonth()] + ' ' + s.getDate() + ', ' + s.getFullYear();
  if (!end) return sLabel + ' \u2014 --';
  const eLabel = months[end.getMonth()] + ' ' + end.getDate() + ', ' + end.getFullYear();
  return sLabel + ' \u2014 ' + eLabel;
}

export function formatRelativeTime(dateStr) {
  if (!dateStr) return 'Just now';
  const diffMin = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return diffMin + 'm ago';
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return diffHr + 'h ago';
  return formatDate(dateStr);
}

export function getInitials(name) {
  if (!name) return '??';
  return name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
}

export function formatCurrency(amount, currency) {
  currency = currency || 'USD';
  try { return new Intl.NumberFormat('en-US', {
    style: 'currency', currency, minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(Number(amount) || 0); } catch { return (Number(amount) || 0).toFixed(2) + ' ' + currency; }
}

export function formatFileSize(bytes) {
  bytes = Math.max(0, Number(bytes) || 0);
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

export function formatActivityMessage(a) {
  const name = a.details?.name || a.details?.item || '';
  const action = a.action || '';
  switch (action) {
    case 'group_created':
      return 'Created the group' + (name ? ' "' + name + '"' : '');
    case 'place_added':
      return 'Added ' + (name || 'a place') + ' to the itinerary';
    case 'place_deleted':
      return 'Removed ' + (name || 'a place') + ' from the itinerary';
    case 'vault_upload':
      return 'Uploaded ' + (a.details?.filename || 'a file') + ' to the vault';
    case 'checklist_item_added':
      return 'Created a checklist task' + (name ? ': "' + name + '"' : '') + ' in Logistics';
    case 'poll_created':
      return 'Created a poll' + (name ? ': "' + name + '"' : '');
    case 'poll_deleted':
      return 'Deleted the poll' + (name ? ' "' + name + '"' : '');
    case 'member_joined':
      return 'Joined the group';
    case 'member_left':
      return 'Left the group';
    case 'invitation_sent':
      return 'Invited ' + (a.details?.invited_email || 'a member');
    default:
      return a.details?.message || action.replace(/_/g, ' ') || 'Activity';
  }
}
