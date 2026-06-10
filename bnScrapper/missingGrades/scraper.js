/**
 * Brightspace Dropbox Submission Scraper (Console Multi-Page Scraper)
 * ===================================================================
 * A pure console-based scraper that extracts student submission data
 * across multiple pages WITHOUT requiring any browser extensions.
 *
 * How it works:
 *   1. Paste and run this script on Page 1. It saves Page 1 and goes to Page 2.
 *   2. On Page 2, press Up Arrow + Enter in the console. It saves Page 2 and goes to Page 3.
 *   3. Repeat until the last page. On the last page, it automatically downloads
 *      the consolidated CSV named after the activity title!
 */

(function () {
  'use strict';

  // ── Helper: strip and clean inner text ──────────────────────────────────────
  function cleanText(el) {
    return el ? el.textContent.trim().replace(/\s+/g, ' ') : '';
  }

  // ── Detect activity type ─────────────────────────────────────────────────────
  const isGroup = !!document.querySelector('[name="restrictGroups"]');
  const pageSelect = document.querySelector('select[name*="_pg"]:not([name*="pgS"]):not([name*="pgs"])');

  // ── Activity Title ──────────────────────────────────────────────────────────
  const titleEl = document.getElementById('d_page_title');
  let activityTitle = titleEl ? cleanText(titleEl) : '';
  activityTitle = activityTitle.replace(/\s*-\s*(Envíos en carpeta|Folder Submissions|Submissions|Envíos)\s*/i, '');
  if (!activityTitle) {
    activityTitle = document.title || 'submissions';
  }
  const safeFilename = activityTitle.replace(/[^a-zA-Z0-9_ -]/g, '').trim() || 'submissions';

  // ── Scraper Core logic ───────────────────────────────────────────────────────
  function extractCurrentPageRows() {
    const table = document.querySelector('table[type="data"]');
    if (!table) return [];

    const rows = Array.from(table.querySelectorAll('tr.d_ggl2'));
    const pageResults = [];

    rows.forEach((headerRow) => {
      // 1. Name (Student or Group)
      const nameLink = headerRow.querySelector('td.dlay_l a');
      const name = nameLink ? cleanText(nameLink) : '(unknown)';

      // 2. Evaluated Status
      const tooltipHelp = headerRow.querySelector('td.dlay_r d2l-tooltip-help');
      let evaluated = false;
      if (tooltipHelp) {
        const tooltipSpan = tooltipHelp.querySelector('span');
        const txt = tooltipSpan ? cleanText(tooltipSpan) : '';
        const attrTxt = tooltipHelp.getAttribute('text') || '';
        const combinedTxt = (txt + ' ' + attrTxt).toLowerCase();
        evaluated = combinedTxt.includes('guardado') ||
          combinedTxt.includes('publicad') ||
          combinedTxt.includes('evaluad');
      }

      // 3. Delivery Status
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

      // 4. Group Members (Group activities only)
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

      const entry = { name, submitted, evaluated };
      if (isGroup) {
        entry.type = 'group';
        entry.members = members;
      } else {
        entry.type = 'individual';
      }

      pageResults.push(entry);
    });

    return pageResults;
  }

  // ── CSV Generator & Downloader ───────────────────────────────────────────────
  function downloadCSV(data) {
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

    const csv = toCSV(data, isGroup);
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeFilename}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ── Session Flow ─────────────────────────────────────────────────────────────
  const isRunning = sessionStorage.getItem('__d2l_scraper_running') === 'true';

  if (!isRunning) {
    // ─── START NEW SESSION ───
    console.log('%c[Scraper] Iniciando nueva sesión de extracción...', 'color: #4f8ef7; font-weight: bold;');

    const results = [];
    sessionStorage.setItem('__d2l_scraper_running', 'true');
    sessionStorage.setItem('__d2l_scraper_results', JSON.stringify(results));

    // Scrape Page 1
    const pageRows = extractCurrentPageRows();
    results.push(...pageRows);
    sessionStorage.setItem('__d2l_scraper_results', JSON.stringify(results));

    if (pageSelect && pageSelect.options.length > 1) {
      console.log('%c[Scraper] Página 1 guardada. Cambiando a la Página 2...', 'color: #7c5af7;');
      pageSelect.selectedIndex = 1;
      pageSelect.dispatchEvent(new Event('change'));
      console.log('Cuando cargue la Página 2, pulsa Flecha Arriba (↑) + Enter en la consola.', 'color: #f0c050; font-weight: bold;');
    } else {
      // Single page scenario
      console.log('%c[Scraper] Extracción finalizada (Página única). Descargando...', 'color: #22d3a0; font-weight: bold;');
      downloadCSV(results);
      sessionStorage.removeItem('__d2l_scraper_running');
      sessionStorage.removeItem('__d2l_scraper_results');
    }
  } else {
    // ─── CONTINUING SESSION ───
    const results = JSON.parse(sessionStorage.getItem('__d2l_scraper_results') || '[]');
    const currentPageIndex = pageSelect ? pageSelect.selectedIndex : 0;
    const totalPages = pageSelect ? pageSelect.options.length : 1;

    console.log(`%c[Scraper] Continuando sesión. Escaneando Página ${currentPageIndex + 1} de ${totalPages}...`, 'color: #4f8ef7;');
    const pageRows = extractCurrentPageRows();

    // Prevent duplicate entries
    pageRows.forEach(row => {
      if (!results.some(r => r.name === row.name)) {
        results.push(row);
      }
    });

    sessionStorage.setItem('__d2l_scraper_results', JSON.stringify(results));

    if (pageSelect && currentPageIndex < totalPages - 1) {
      console.log(`%c[Scraper] Página ${currentPageIndex + 1} guardada. Cambiando a la Página ${currentPageIndex + 2}...`, 'color: #7c5af7;');
      pageSelect.selectedIndex = currentPageIndex + 1;
      pageSelect.dispatchEvent(new Event('change'));
      console.log(`Cuando cargue la Página ${currentPageIndex + 2}, pulsa Flecha Arriba (↑) + Enter en la consola.`, 'color: #f0c050; font-weight: bold;');
    } else {
      // Completed last page
      console.log('%c[Scraper] ¡Todas las páginas escaneadas correctamente!', 'color: #22d3a0; font-weight: bold;');
      console.log(`%cDescargando CSV consolidado: "${safeFilename}.csv"`, 'color: #22d3a0; font-weight: bold;');
      downloadCSV(results);

      // Clean session storage
      sessionStorage.removeItem('__d2l_scraper_running');
      sessionStorage.removeItem('__d2l_scraper_results');
      console.log('[Scraper] Sesión y memoria limpiadas con éxito.');
    }
  }
})();