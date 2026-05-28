/**
 * Brightspace Dropbox Submission Scraper
 * ========================================
 * Run this script in the browser console while on a Brightspace
 * "Folder Submissions" page to extract all submission data.
 *
 * Works with:
 *   - Individual activities  (restrictUsers table)
 *   - Group activities       (restrictGroups table)
 *
 * Output: JSON array + CSV download via console / auto-download
 *
 * Usage:
 *   1. Navigate to the Brightspace folder submissions page
 *   2. Open DevTools → Console
 *   3. Paste this entire script and press Enter
 */

(function () {
  'use strict';

  // ── Helper: strip and clean inner text ──────────────────────────────────────
  function cleanText(el) {
    return el ? el.textContent.trim().replace(/\s+/g, ' ') : '';
  }

  // ── Detect activity type ─────────────────────────────────────────────────────
  // Individual activities use name="restrictUsers",
  // Group activities use name="restrictGroups"
  const isGroup = !!document.querySelector('[name="restrictGroups"]');

  // ── Locate the submissions table ─────────────────────────────────────────────
  // The table's summary attribute distinguishes users vs groups
  const table = document.querySelector('table[type="data"]');
  if (!table) {
    console.error('[Scraper] Could not find the submissions table. Are you on the right page?');
    return;
  }

  // ── Parse rows ───────────────────────────────────────────────────────────────
  // Entity header rows have class "d_ggl2" and contain the name + evaluation info.
  // Submission file rows immediately follow and lack that class.
  const rows = Array.from(table.querySelectorAll('tr.d_ggl2'));
  if (rows.length === 0) {
    console.warn('[Scraper] No submission rows found. Make sure all students are visible (no filters).');
    return;
  }

  const results = [];

  rows.forEach((headerRow) => {
    // ── 1. Name ──────────────────────────────────────────────────────────────
    // The entity name (student or group) is in .dlay_l > a
    const nameLink = headerRow.querySelector('td.dlay_l a');
    const name = nameLink ? cleanText(nameLink) : '(unknown)';

    // ── 2. Evaluated ─────────────────────────────────────────────────────────
    // A d2l-tooltip-help element inside .dlay_r contains "Guardado <date>"
    // If the date is missing (just "Guardado "), it hasn't been evaluated yet.
    // We also check display:none on its parent .dco — if hidden it means never saved.
    const tooltipSpan = headerRow.querySelector('td.dlay_r d2l-tooltip-help span');
    let evaluated = false;
    if (tooltipSpan) {
      const txt = cleanText(tooltipSpan);
      // "Guardado 14 de marzo de 2026 17:04" → evaluated
      // "Guardado "                           → not evaluated
      evaluated = txt.startsWith('Guardado') && txt.replace('Guardado', '').trim().length > 0;
    }

    // ── 3. Submitted ─────────────────────────────────────────────────────────
    // File rows immediately follow the header row (sibling <tr> elements that
    // don't have class "d_ggl2"). They contain <label>DATE</label> for the
    // submission date. If there are no such file rows with a non-empty label,
    // the student has not submitted.
    let submitted = false;
    let nextSibling = headerRow.nextElementSibling;
    while (nextSibling && !nextSibling.classList.contains('d_ggl2')) {
      const dateLabel = nextSibling.querySelector('td.d_gc label');
      if (dateLabel && cleanText(dateLabel).length > 0) {
        submitted = true;
        break;
      }
      nextSibling = nextSibling.nextElementSibling;
    }

    // ── 4. Group members (group activities only) ──────────────────────────────
    // In group tables, member names appear in <th class="d_gn"> inside the
    // sibling file rows.
    let members = [];
    if (isGroup) {
      let sibling = headerRow.nextElementSibling;
      while (sibling && !sibling.classList.contains('d_ggl2')) {
        const memberLink = sibling.querySelector('th.d_gn a');
        if (memberLink) {
          const memberName = cleanText(memberLink);
          if (memberName && !members.includes(memberName)) {
            members.push(memberName);
          }
        }
        sibling = sibling.nextElementSibling;
      }
    }

    const entry = {
      name,
      submitted,
      evaluated,
    };
    if (isGroup) {
      entry.type = 'group';
      entry.members = members;
    } else {
      entry.type = 'individual';
    }

    results.push(entry);
  });

  // ── Output ───────────────────────────────────────────────────────────────────
  console.group(`[Scraper] Results (${isGroup ? 'Group' : 'Individual'} activity) — ${results.length} entries`);
  console.table(results);
  console.groupEnd();

  // ── CSV export ───────────────────────────────────────────────────────────────
  function toCSV(data, isGroup) {
    const headers = isGroup
      ? ['Nombre/Grupo', 'Enviado', 'Evaluado', 'Miembros']
      : ['Nombre', 'Enviado', 'Evaluado'];

    const rows = data.map((r) => {
      const base = [
        `"${r.name.replace(/"/g, '""')}"`,
        r.submitted ? 'Sí' : 'No',
        r.evaluated ? 'Sí' : 'No',
      ];
      if (isGroup) {
        base.push(`"${(r.members || []).join('; ').replace(/"/g, '""')}"`);
      }
      return base.join(',');
    });

    return [headers.join(','), ...rows].join('\n');
  }

  const csv = toCSV(results, isGroup);
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' }); // BOM for Excel
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `submissions_${isGroup ? 'group' : 'individual'}_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log('[Scraper] CSV downloaded successfully.');
  console.log('[Scraper] Raw JSON data stored in window.__scraperResults');
  window.__scraperResults = results;

  return results;
})();
