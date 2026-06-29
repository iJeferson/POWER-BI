const API = window.location.origin;

const COLORS = {
  CIN: '#0d9488',
  CNH: '#1a3a6e',
  RENAVAM: '#c41e3a',
  CONSORCIO: '#1a3a6e',
  DPT: '#3b6fd4',
  PREFEITURA: '#0d9488',
  SAEB: '#c41e3a',
};

const CHART = {
  grid: 'rgba(12, 35, 64, 0.06)',
  tick: '#8b9cb3',
  navy: '#1a3a6e',
  accent: '#3b6fd4',
  regiao: ['#1a3a6e', '#3b6fd4', '#0d9488', '#c41e3a', '#7c3aed'],
};

const charts = {};
const DESKTOP_BP = 1100;
let dashboardCarregado = false;
let carregandoDashboard = false;

function fmt(n) { return n == null ? '—' : Number(n).toLocaleString('pt-BR'); }
function fmtPct(n) { return n == null ? '—' : n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%'; }
function fmtTempo(m) { return m == null ? '—' : m.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' min'; }
function isDesktop() { return window.innerWidth >= DESKTOP_BP; }

const PAGE_COPY = {
  captura: {
    title: 'Painel de Captura',
    subtitle: 'Capturas por emissora, posto e tipo de documento.',
  },
  produtividade: {
    title: 'Produtividade Operacional',
    subtitle: 'Desempenho por posto e atendente.',
  },
};

const DOCUMENT_TITLE = 'Consórcio Bahia Digital';

function syncDocumentTitle() {
  if (document.title !== DOCUMENT_TITLE) {
    document.title = DOCUMENT_TITLE;
  }
}

function formatBrandEyebrow(resumo) {
  const anoAtual = new Date().getFullYear();
  const anos = resumo?.anos?.length ? resumo.anos : null;
  if (anos?.length) {
    const yMin = anos[0];
    const yMax = anos[anos.length - 1];
    const label = yMin === yMax ? String(yMax) : `${yMin}–${yMax}`;
    return `Inteligência de Dados · ${label}`;
  }
  if (resumo?.data_minima && resumo?.data_maxima) {
    const yMin = new Date(resumo.data_minima + 'T12:00:00').getFullYear();
    const yMax = new Date(resumo.data_maxima + 'T12:00:00').getFullYear();
    const label = yMin === yMax ? String(yMax) : `${yMin}–${yMax}`;
    return `Inteligência de Dados · ${label}`;
  }
  return `Inteligência de Dados · ${anoAtual}`;
}

function atualizarPagina(tab = 'captura') {
  const copy = PAGE_COPY[tab] || PAGE_COPY.captura;
  document.getElementById('pageTitle').textContent = copy.title;
  document.getElementById('pageSubtitle').textContent = copy.subtitle;
  syncDocumentTitle();
}

function atualizarBrandEyebrow(resumo) {
  const el = document.getElementById('brandEyebrow');
  if (el) el.textContent = formatBrandEyebrow(resumo);
}
function refreshIcons(root = document) {
  if (window.lucide) lucide.createIcons({ attrs: { 'stroke-width': 1.75 }, root });
}

function selectedChips(containerId) {
  return [...document.querySelectorAll(`#${containerId} .chip.selected`)].map(c => c.dataset.value);
}

function params() {
  const p = new URLSearchParams();
  const di = document.getElementById('dataInicio').value;
  const df = document.getElementById('dataFim').value;
  const posto = document.getElementById('posto').value;
  const operador = document.getElementById('operador').value;
  if (di) p.set('data_inicio', di);
  if (df) p.set('data_fim', df);
  if (posto) p.set('posto', posto);
  if (operador) p.set('operador', operador);
  const mes = selectedChips('filtroMes');
  const regiao = selectedChips('filtroRegiao');
  const emissora = selectedChips('filtroEmissora');
  const tipoPosto = selectedChips('filtroTipoPosto');
  const tipo = selectedChips('filtroTipo');
  if (mes.length) p.set('mes', mes.join(','));
  if (regiao.length) p.set('regiao', regiao.join(','));
  if (emissora.length) p.set('emissora', emissora.join(','));
  if (tipoPosto.length) p.set('tipo_posto', tipoPosto.join(','));
  if (tipo.length) p.set('tipo_captura', tipo.join(','));
  const s = p.toString();
  return s ? '?' + s : '';
}

function qs(extra = '') {
  const q = params();
  if (!extra) return q;
  return q ? q + '&' + extra : '?' + extra;
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 5000);
}

let loadingInterval = null;
let loadingProgress = 0;

function setLoading(on, text = 'Carregando dados', mode = 'fetch') {
  const overlay = document.getElementById('loading');
  const bar = document.getElementById('loadingBar');
  const sub = document.getElementById('loadingSub');

  if (!on) {
    clearInterval(loadingInterval);
    loadingInterval = null;
    loadingProgress = 0;
    if (bar) bar.style.width = '0%';
    overlay.classList.remove('show', 'loading-import', 'loading-fetch');
    return;
  }

  overlay.classList.add('show', mode === 'import' ? 'loading-import' : 'loading-fetch');
  document.getElementById('loadingText').textContent = text;
  if (sub) {
    sub.textContent = mode === 'import'
      ? 'Lendo planilha, validando registros e gravando no banco'
      : 'Atualizando indicadores e visualizações';
  }

  loadingProgress = 0;
  if (bar) bar.style.width = '0%';
  clearInterval(loadingInterval);
  const cap = mode === 'import' ? 88 : 90;
  const pace = mode === 'import' ? 0.028 : 0.045;
  loadingInterval = setInterval(() => {
    if (loadingProgress < cap) {
      const delta = Math.max((cap - loadingProgress) * pace, 0.25);
      loadingProgress = Math.min(cap, loadingProgress + delta);
      if (bar) bar.style.width = loadingProgress + '%';
    }
  }, 180);
}

function finishLoading() {
  const bar = document.getElementById('loadingBar');
  clearInterval(loadingInterval);
  loadingInterval = null;
  if (bar) bar.style.width = '100%';
  setTimeout(() => setLoading(false), 550);
}

async function fetchJson(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error('Erro ao carregar dados');
  return res.json();
}

function buildChips(id, items, labelFn = x => x) {
  const el = document.getElementById(id);
  const prev = new Set([...el.querySelectorAll('.chip.selected')].map(c => c.dataset.value));
  el.innerHTML = items.map(v => {
    const val = typeof v === 'object' ? (v.nome || v) : v;
    const label = labelFn(v);
    const sel = prev.has(String(val)) ? ' selected' : '';
    return `<button type="button" class="chip${sel}" data-value="${val}">${label}</button>`;
  }).join('');
  el.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('selected');
      updateActiveChips();
    });
  });
}

function fillSelect(id, items) {
  const sel = document.getElementById(id);
  if (!sel || sel.tagName !== 'SELECT') return;
  const cur = sel.value;
  while (sel.options.length > 1) sel.remove(1);
  items.forEach(v => {
    const o = document.createElement('option');
    o.value = v; o.textContent = v;
    sel.appendChild(o);
  });
  if (cur) sel.value = cur;
}

const AC = { posto: { items: [], suggestions: [], active: -1 }, operador: { items: [], suggestions: [], active: -1 } };

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

function highlightMatch(text, query) {
  const q = query.trim().toLowerCase();
  if (!q) return escapeHtml(text);
  const lower = text.toLowerCase();
  const idx = lower.indexOf(q);
  if (idx < 0) return escapeHtml(text);
  return `${escapeHtml(text.slice(0, idx))}<mark>${escapeHtml(text.slice(idx, idx + q.length))}</mark>${escapeHtml(text.slice(idx + q.length))}`;
}

function normalizeAutocompleteQuery(q) {
  return q.trim().toLowerCase();
}

function autocompleteMatches(text, query) {
  const q = normalizeAutocompleteQuery(query);
  if (!q) return true;
  const lower = text.toLowerCase();
  if (lower.includes(q)) return true;
  const spaced = q.replace(/\./g, ' ').replace(/_/g, ' ');
  if (spaced !== q && lower.includes(spaced)) return true;
  const compact = q.replace(/[._]/g, '');
  if (compact !== q && lower.replace(/\s+/g, '').includes(compact)) return true;
  return false;
}

function filterAutocompleteItems(items, query) {
  const q = query.trim();
  const list = q ? items.filter(v => autocompleteMatches(v, q)) : items;
  return list.slice(0, 20);
}

function autocompleteParams(key) {
  const p = new URLSearchParams();
  const di = document.getElementById('dataInicio').value;
  const df = document.getElementById('dataFim').value;
  if (di) p.set('data_inicio', di);
  if (df) p.set('data_fim', df);
  if (key !== 'posto') {
    const posto = document.getElementById('posto').value;
    if (posto) p.set('posto', posto);
  }
  if (key !== 'operador') {
    const operador = document.getElementById('operador').value;
    if (operador) p.set('operador', operador);
  }
  const mes = selectedChips('filtroMes');
  const regiao = selectedChips('filtroRegiao');
  const emissora = selectedChips('filtroEmissora');
  const tipoPosto = selectedChips('filtroTipoPosto');
  const tipo = selectedChips('filtroTipo');
  if (mes.length) p.set('mes', mes.join(','));
  if (regiao.length) p.set('regiao', regiao.join(','));
  if (emissora.length) p.set('emissora', emissora.join(','));
  if (tipoPosto.length) p.set('tipo_posto', tipoPosto.join(','));
  if (tipo.length) p.set('tipo_captura', tipo.join(','));
  const s = p.toString();
  return s ? '&' + s : '';
}

function hideAutocompleteList(key) {
  const list = document.getElementById(`${key}List`);
  list.hidden = true;
  list.innerHTML = '';
  AC[key].active = -1;
}

function selectAutocompleteValue(key, value) {
  document.getElementById(key).value = value;
  document.getElementById(`${key}Input`).value = value;
  hideAutocompleteList(key);
  updateActiveChips();
}

function clearAutocomplete(key) {
  document.getElementById(key).value = '';
  document.getElementById(`${key}Input`).value = '';
  hideAutocompleteList(key);
}

function renderAutocompleteList(key, query, suggestions) {
  const list = document.getElementById(`${key}List`);
  const items = suggestions ?? filterAutocompleteItems(AC[key].items, query);
  AC[key].suggestions = items;
  if (!items.length) {
    hideAutocompleteList(key);
    return;
  }
  const q = query.trim().toLowerCase();
  list.innerHTML = items.map((v, i) =>
    `<li class="autocomplete-item" role="option" data-idx="${i}">${highlightMatch(v, q)}</li>`
  ).join('');
  list.hidden = false;
  AC[key].active = -1;
}

const acDebounce = {};
const acSearchGen = { posto: 0, operador: 0 };

async function loadAutocompleteSuggestions(key, query) {
  const q = query.trim();
  if (!q) {
    renderAutocompleteList(key, '');
    return;
  }
  const gen = ++acSearchGen[key];
  try {
    const items = await fetchJson(
      `/api/dashboard/filtros/buscar?tipo=${key}&q=${encodeURIComponent(q)}${autocompleteParams(key)}`
    );
    if (gen !== acSearchGen[key]) return;
    renderAutocompleteList(key, q, items);
  } catch {
    if (gen !== acSearchGen[key]) return;
    renderAutocompleteList(key, q);
  }
}

async function resolveAutocompleteValue(key, typed) {
  const t = typed.trim();
  if (!t) return null;
  const exact = list => list.find(v => v.toLowerCase() === t.toLowerCase());
  let hit = exact(AC[key].suggestions) || exact(AC[key].items);
  if (hit) return hit;
  hit = AC[key].suggestions.find(v => autocompleteMatches(v, t));
  if (hit) return hit;
  try {
    const items = await fetchJson(
      `/api/dashboard/filtros/buscar?tipo=${key}&q=${encodeURIComponent(t)}${autocompleteParams(key)}`
    );
    hit = exact(items) || items.find(v => autocompleteMatches(v, t));
    if (hit) return hit;
    if (items.length === 1) return items[0];
  } catch {
    /* fallback local */
  }
  return null;
}

function setAutocompleteItems(key, items) {
  AC[key].items = items;
  const hidden = document.getElementById(key);
  const input = document.getElementById(`${key}Input`);
  const cur = hidden.value;
  if (cur) input.value = cur;
  else input.value = '';
}

function setupAutocomplete(key) {
  const input = document.getElementById(`${key}Input`);
  const list = document.getElementById(`${key}List`);
  const hidden = document.getElementById(key);

  input.addEventListener('input', () => {
    clearTimeout(acDebounce[key]);
    acDebounce[key] = setTimeout(() => loadAutocompleteSuggestions(key, input.value), 250);
  });

  input.addEventListener('focus', () => {
    const q = input.value.trim();
    if (q) loadAutocompleteSuggestions(key, q);
    else renderAutocompleteList(key, '');
  });

  input.addEventListener('keydown', (e) => {
    const items = [...list.querySelectorAll('.autocomplete-item')];
    if (!items.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      AC[key].active = Math.min(AC[key].active + 1, items.length - 1);
      items.forEach((el, i) => el.classList.toggle('active', i === AC[key].active));
      items[AC[key].active]?.scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      AC[key].active = Math.max(AC[key].active - 1, 0);
      items.forEach((el, i) => el.classList.toggle('active', i === AC[key].active));
      items[AC[key].active]?.scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const idx = AC[key].active >= 0 ? AC[key].active : 0;
      const val = AC[key].suggestions[idx];
      if (val) selectAutocompleteValue(key, val);
    } else if (e.key === 'Escape') {
      hideAutocompleteList(key);
    }
  });

  input.addEventListener('blur', () => {
    setTimeout(async () => {
      hideAutocompleteList(key);
      const typed = input.value.trim();
      const committed = hidden.value;
      if (!typed) {
        if (committed) {
          hidden.value = '';
          updateActiveChips();
        }
        return;
      }
      const resolved = await resolveAutocompleteValue(key, typed);
      if (resolved) {
        hidden.value = resolved;
        input.value = resolved;
        updateActiveChips();
      } else {
        input.value = committed;
      }
    }, 160);
  });

  list.addEventListener('mousedown', (e) => {
    e.preventDefault();
    const item = e.target.closest('.autocomplete-item');
    const val = item ? AC[key].suggestions[+item.dataset.idx] : null;
    if (val) selectAutocompleteValue(key, val);
  });
}

function initAutocompletes() {
  ['posto', 'operador'].forEach(setupAutocomplete);
}

function updateActiveChips() {
  const chips = [];
  const add = (label, clearFn) => chips.push({ label, clearFn });

  if (document.getElementById('dataInicio').value)
    add('De ' + document.getElementById('dataInicio').value, () => { document.getElementById('dataInicio').value = ''; });
  if (document.getElementById('dataFim').value)
    add('Até ' + document.getElementById('dataFim').value, () => { document.getElementById('dataFim').value = ''; });
  selectedChips('filtroMes').forEach(v => add('Mês: ' + v, () => toggleChip('filtroMes', v)));
  selectedChips('filtroRegiao').forEach(v => add(v, () => toggleChip('filtroRegiao', v)));
  selectedChips('filtroEmissora').forEach(v => add(v, () => toggleChip('filtroEmissora', v)));
  selectedChips('filtroTipoPosto').forEach(v => add(v, () => toggleChip('filtroTipoPosto', v)));
  selectedChips('filtroTipo').forEach(v => add(v, () => toggleChip('filtroTipo', v)));
  const posto = document.getElementById('posto').value;
  if (posto) add('Posto: ' + posto, () => clearAutocomplete('posto'));
  const op = document.getElementById('operador').value;
  if (op) add('Operador: ' + op, () => clearAutocomplete('operador'));

  const el = document.getElementById('activeChips');
  el.innerHTML = chips.map((c, i) =>
    `<span class="chip-active">${c.label}<button type="button" data-idx="${i}" aria-label="Remover"><i data-lucide="x"></i></button></span>`
  ).join('');

  el.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      chips[+btn.dataset.idx].clearFn();
      updateActiveChips();
    });
  });

  const count = document.getElementById('filterCount');
  if (chips.length) {
    count.textContent = chips.length;
    count.hidden = false;
  } else {
    count.hidden = true;
  }
  refreshIcons(el);
}

function toggleChip(containerId, value) {
  const chip = document.querySelector(`#${containerId} .chip[data-value="${CSS.escape(value)}"]`);
  if (chip) chip.classList.remove('selected');
}

function toggleFilterExpand(force) {
  const panel = document.getElementById('filterPanel');
  const btn = document.getElementById('btnOpenFilters');
  const expand = force !== undefined ? force : !panel.classList.contains('expanded');
  panel.classList.toggle('expanded', expand);
  if (btn) btn.setAttribute('aria-expanded', String(expand));
  refreshIcons(panel);
}

function openFilters() {
  if (isDesktop()) {
    toggleFilterExpand();
    return;
  }
  document.getElementById('filterPanel').classList.add('open');
  document.getElementById('filterBackdrop').hidden = false;
  requestAnimationFrame(() => document.getElementById('filterBackdrop').classList.add('show'));
  document.getElementById('btnOpenFilters').setAttribute('aria-expanded', 'true');
}
function closeFilters() {
  if (isDesktop()) {
    toggleFilterExpand(false);
    return;
  }
  document.getElementById('filterPanel').classList.remove('open');
  document.getElementById('filterBackdrop').classList.remove('show');
  setTimeout(() => { document.getElementById('filterBackdrop').hidden = true; }, 250);
  document.getElementById('btnOpenFilters').setAttribute('aria-expanded', 'false');
}

async function carregarOpcoesFiltros() {
  const d = await fetchJson('/api/dashboard/filtros' + params());
  buildChips('filtroMes', d.meses || [], m => m.nome);
  buildChips('filtroRegiao', d.regioes || []);
  buildChips('filtroEmissora', d.emissoras || []);
  buildChips('filtroTipoPosto', d.tipos_posto || []);
  buildChips('filtroTipo', d.tipos_captura || []);
  setAutocompleteItems('posto', d.postos || []);
  setAutocompleteItems('operador', d.operadores || []);
  updateActiveChips();
}

async function carregarFiltros() {
  await carregarOpcoesFiltros();
}

function kpiCard(label, value, variant = 'total', sub = '', icon = 'bar-chart-3') {
  return `<div class="kpi-premium kpi-${variant}">
    <div class="kpi-premium-accent" aria-hidden="true"></div>
    <span class="kpi-premium-icon" aria-hidden="true"><i data-lucide="${icon}"></i></span>
    <span class="kpi-premium-label">${label}</span>
    <span class="kpi-premium-value">${value}</span>
    ${sub ? `<span class="kpi-premium-sub">${sub}</span>` : ''}
  </div>`;
}

function renderKpisCaptura(k) {
  document.getElementById('kpiCaptura').innerHTML = [
    kpiCard('Total de capturas', fmt(k.total_atendimentos), 'total', '', 'layers'),
    kpiCard('CIN', fmtPct(k.pct_cin), 'cin', fmt(k.total_cin) + ' registros', 'id-card'),
    kpiCard('CNH', fmtPct(k.pct_cnh), 'cnh', fmt(k.total_cnh) + ' registros', 'car'),
    kpiCard('RENAVAM', fmtPct(k.pct_renavam), 'renavam', fmt(k.total_renavam) + ' registros', 'file-text'),
  ].join('');
  refreshIcons(document.getElementById('kpiCaptura'));
}

function renderKpisInsights(k) {
  const horaLabel = k.hora_pico != null ? String(k.hora_pico).padStart(2, '0') + 'h' : '—';
  document.getElementById('kpiInsights').innerHTML = [
    kpiCard('Horário de pico', horaLabel, 'highlight', fmt(k.hora_pico_qtd) + ' atendimentos', 'clock-3'),
    kpiCard('Dia mais movimentado', k.dia_semana_pico || '—', 'highlight', fmt(k.dia_semana_pico_qtd) + ' atendimentos', 'calendar'),
    kpiCard('Média diária', k.media_diaria != null ? fmt(k.media_diaria) : '—', 'total', 'atendimentos/dia', 'activity'),
    kpiCard('Fim de semana', fmtPct(k.pct_fim_semana), 'time', 'do volume total', 'sun'),
  ].join('');
  refreshIcons(document.getElementById('kpiInsights'));
}

function renderKpisProd(k) {
  document.getElementById('kpiProd').innerHTML = [
    kpiCard('Total atendimentos', fmt(k.total_atendimentos), 'total', '', 'clipboard-list'),
    kpiCard('Posto destaque', k.posto_mais_produtivo || '—', 'highlight', fmt(k.qtd_posto_destaque) + ' atendimentos', 'trophy'),
    kpiCard('Colaborador destaque', k.operador_mais_produtivo || '—', 'highlight', fmt(k.qtd_operador_destaque) + ' atendimentos', 'award'),
    kpiCard('Total de postos', fmt(k.total_postos), 'total', '', 'map-pin'),
    kpiCard('Tempo médio CNH', fmtTempo(k.tempo_medio_cnh), 'time', '', 'timer'),
    kpiCard('Tempo médio CIN', fmtTempo(k.tempo_medio_cin), 'time', '', 'clock'),
  ].join('');
  refreshIcons(document.getElementById('kpiProd'));
}

function destroyChart(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function chartFont() {
  const size = isDesktop() ? (window.innerWidth >= 1920 ? 12 : 10) : 9;
  return { family: "'Plus Jakarta Sans', sans-serif", size, weight: '500' };
}

function chartOpts(horizontal = false) {
  const font = chartFont();
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? 'y' : 'x',
    plugins: { legend: { display: false }, tooltip: { backgroundColor: '#0c2340', titleFont: font, bodyFont: font, padding: 12, cornerRadius: 8 } },
    scales: {
      x: {
        ticks: { color: CHART.tick, font, maxRotation: horizontal ? 0 : 45 },
        grid: { color: CHART.grid, drawBorder: false },
        border: { display: false },
      },
      y: {
        ticks: { color: CHART.tick, font },
        grid: { color: CHART.grid, drawBorder: false },
        border: { display: false },
      },
    },
  };
}

function hBar(id, labels, data, colors) {
  destroyChart(id);
  const bg = Array.isArray(colors) ? colors : labels.map(() => colors);
  charts[id] = new Chart(document.getElementById(id), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: bg,
        borderRadius: 6,
        borderSkipped: false,
        maxBarThickness: 28,
      }],
    },
    options: chartOpts(true),
  });
}

function vBar(id, labels, data, peakIndex = -1) {
  destroyChart(id);
  const max = Math.max(...data, 0);
  const bg = labels.map((_, i) => {
    if (i === peakIndex) return CHART.accent;
    const v = data[i];
    const alpha = max ? 0.28 + (v / max) * 0.55 : 0.35;
    return `rgba(59, 111, 212, ${alpha.toFixed(2)})`;
  });
  charts[id] = new Chart(document.getElementById(id), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: bg,
        borderRadius: 5,
        borderSkipped: false,
        maxBarThickness: 24,
      }],
    },
    options: chartOpts(false),
  });
}

function donutPercent(id, labels, data, colors) {
  destroyChart(id);
  const total = data.reduce((a, b) => a + b, 0);
  const pcts = data.map(v => (total ? +(v / total * 100).toFixed(2) : 0));
  const font = chartFont();
  charts[id] = new Chart(document.getElementById(id), {
    type: 'doughnut',
    data: {
      labels: labels.map((l, i) => `${l} · ${pcts[i].toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`),
      datasets: [{
        data: pcts,
        backgroundColor: colors,
        borderWidth: 3,
        borderColor: '#ffffff',
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 16,
            font,
            color: '#4a5d75',
          },
        },
        tooltip: {
          backgroundColor: '#0c2340',
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label(ctx) {
              const abs = data[ctx.dataIndex];
              return ` ${ctx.label.split(' · ')[0]}: ${ctx.parsed.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}% (${fmt(abs)} capturas)`;
            },
          },
        },
      },
    },
  });
}

function donut(id, labels, data, colors) {
  destroyChart(id);
  charts[id] = new Chart(document.getElementById(id), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 3,
        borderColor: '#ffffff',
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            usePointStyle: true,
            pointStyle: 'circle',
            padding: 16,
            font: chartFont(),
            color: '#4a5d75',
          },
        },
        tooltip: { backgroundColor: '#0c2340', padding: 12, cornerRadius: 8 },
      },
    },
  });
}

function areaChart(id, labels, data) {
  destroyChart(id);
  const ctx = document.getElementById(id).getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 300);
  grad.addColorStop(0, 'rgba(59, 111, 212, 0.22)');
  grad.addColorStop(1, 'rgba(59, 111, 212, 0.02)');
  const font = chartFont();

  charts[id] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Capturas',
        data,
        fill: true,
        tension: 0.4,
        borderColor: CHART.accent,
        backgroundColor: grad,
        borderWidth: 2.5,
        pointRadius: 0,
        pointHitRadius: 14,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: CHART.accent,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
      }],
    },
    options: {
      ...chartOpts(),
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          backgroundColor: '#0c2340',
          padding: 12,
          cornerRadius: 8,
          titleFont: font,
          bodyFont: font,
          displayColors: false,
          callbacks: {
            title(items) {
              return items[0]?.label || '';
            },
            label(ctx) {
              return ` ${fmt(ctx.parsed.y)} capturas`;
            },
          },
        },
      },
    },
  });
}

async function carregarResumo() {
  const r = await fetchJson('/api/dashboard/resumo' + params());
  const filtrado = params() !== '';
  atualizarBrandEyebrow(r);
  const anosHtml = r.anos?.length
    ? `<span><i data-lucide="calendar-range" class="icon icon-sm" aria-hidden="true"></i>Anos: <strong>${r.anos.join(', ')}</strong></span>`
    : '';
  document.getElementById('resumoStrip').innerHTML = `
    <span><i data-lucide="database" class="icon icon-sm" aria-hidden="true"></i><strong>${fmt(r.total_capturas)}</strong> capturas${filtrado ? ' (filtrado)' : ''}</span>
    <span><i data-lucide="file-spreadsheet" class="icon icon-sm" aria-hidden="true"></i><strong>${r.total_arquivos}</strong> planilhas importadas</span>
    ${anosHtml}
    <span><i data-lucide="calendar-days" class="icon icon-sm" aria-hidden="true"></i>Período: <strong>${r.data_minima ? new Date(r.data_minima + 'T12:00:00').toLocaleDateString('pt-BR') : '—'}</strong> – <strong>${r.data_maxima ? new Date(r.data_maxima + 'T12:00:00').toLocaleDateString('pt-BR') : '—'}</strong></span>`;
  refreshIcons(document.getElementById('resumoStrip'));
}

async function carregarDashboard(opcoes = {}) {
  const { fecharFiltros = false, silencioso = false } = opcoes;
  carregandoDashboard = true;
  if (!silencioso) setLoading(true, 'Aplicando filtros', 'fetch');
  updateActiveChips();
  const q = params();
  try {
    const [kpis, emissora, tipo, porMes, porHora, porDia, porTipoPosto, regiao, rankP, rankO] = await Promise.all([
      fetchJson('/api/dashboard/kpis' + q),
      fetchJson('/api/dashboard/por-emissora' + q),
      fetchJson('/api/dashboard/por-tipo' + q),
      fetchJson('/api/dashboard/por-mes' + q),
      fetchJson('/api/dashboard/por-hora' + q),
      fetchJson('/api/dashboard/por-dia-semana' + q),
      fetchJson('/api/dashboard/por-tipo-posto' + q),
      fetchJson('/api/dashboard/por-regiao' + q),
      fetchJson('/api/dashboard/ranking/postos' + qs('limit=15')),
      fetchJson('/api/dashboard/ranking/operadores' + qs('limit=15')),
    ]);
    renderKpisCaptura(kpis);
    renderKpisInsights(kpis);
    renderKpisProd(kpis);
    hBar('chartEmissora', emissora.map(e => e.emissora), emissora.map(e => e.total), emissora.map(e => COLORS[e.emissora] || CHART.accent));
    donutPercent('chartEmissoraDonut', emissora.map(e => e.emissora), emissora.map(e => e.total), emissora.map(e => COLORS[e.emissora] || CHART.accent));
    areaChart('chartEvolucaoMes', porMes.map(m => m.mes || ('Mês ' + m.mes_numero)), porMes.map(m => m.total));
    const peakH = porHora.reduce((best, h, i) => (h.total > porHora[best].total ? i : best), 0);
    vBar('chartHora', porHora.map(h => String(h.hora).padStart(2, '0') + 'h'), porHora.map(h => h.total), peakH);
    hBar('chartDiaSemana', porDia.map(d => d.dia), porDia.map(d => d.total), CHART.regiao);
    hBar('chartTipoPosto', porTipoPosto.map(t => t.tipo_posto), porTipoPosto.map(t => t.total), CHART.navy);
    hBar('chartTipoDoc', tipo.map(t => t.tipo), tipo.map(t => t.total), tipo.map(t => COLORS[t.tipo] || CHART.navy));
    hBar('chartPosto', rankP.map(r => r.nome), rankP.map(r => r.total), CHART.navy);
    hBar('chartColab', rankO.map(r => r.nome), rankO.map(r => r.total), CHART.accent);
    donutPercent('chartRegiaoDonut', regiao.map(r => r.regiao), regiao.map(r => r.total), CHART.regiao);
    hBar('chartRegiao', regiao.map(r => r.regiao), regiao.map(r => r.total), CHART.regiao);
    await carregarResumo();
    await carregarOpcoesFiltros();
    dashboardCarregado = true;
    document.getElementById('status').textContent = 'Atualizado em ' + new Date().toLocaleString('pt-BR');
    if (fecharFiltros && !isDesktop()) closeFilters();
  } catch (e) {
    toast('Erro: ' + e.message);
    setLoading(false);
  } finally {
    carregandoDashboard = false;
    if (!silencioso && document.getElementById('loading').classList.contains('show')) finishLoading();
  }
}

function limparFiltros() {
  document.querySelectorAll('.chip.selected').forEach(c => c.classList.remove('selected'));
  ['dataInicio', 'dataFim'].forEach(id => { document.getElementById(id).value = ''; });
  clearAutocomplete('posto');
  clearAutocomplete('operador');
  updateActiveChips();
  carregarDashboard();
}

document.querySelectorAll('.tab').forEach(btn => {
  if (btn.dataset.tabBound === '1') return;
  btn.dataset.tabBound = '1';
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    atualizarPagina(btn.dataset.tab);
    setTimeout(() => Object.keys(charts).forEach(k => charts[k]?.resize()), 120);
    refreshIcons();
  });
});

document.getElementById('btnOpenFilters').addEventListener('click', openFilters);
document.getElementById('btnCloseFilters').addEventListener('click', closeFilters);
document.getElementById('btnRecolherFiltros').addEventListener('click', () => toggleFilterExpand(false));
document.getElementById('filterBackdrop').addEventListener('click', closeFilters);
document.getElementById('btnFiltrar').addEventListener('click', () => {
  carregarDashboard({ fecharFiltros: true });
  if (isDesktop()) toggleFilterExpand(false);
});
document.getElementById('btnLimpar').addEventListener('click', limparFiltros);
['dataInicio', 'dataFim'].forEach(id => {
  document.getElementById(id).addEventListener('change', updateActiveChips);
});

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

let importConfig = { requer_senha: true, disponivel: true };
let importAutenticado = false;
let importToken = '';

function importFetchHeaders(extra = {}) {
  const headers = { ...extra };
  if (importToken) headers['X-Import-Token'] = importToken;
  return headers;
}

async function carregarImportConfig() {
  try {
    importConfig = await fetchJson('/api/importacao/config');
  } catch {
    importConfig = { requer_senha: true, disponivel: true };
  }
}

function showAdminStep(step) {
  document.getElementById('adminAuthStep').hidden = step !== 'auth';
  document.getElementById('adminImportStep').hidden = step !== 'import';
  document.getElementById('adminBlockedStep').hidden = step !== 'blocked';
  const err = document.getElementById('importAuthError');
  err.hidden = true;
  if (step === 'auth') {
    document.getElementById('importSenha').value = '';
  }
}

function openAdminModal(focusSenha = false) {
  document.getElementById('adminBackdrop').hidden = false;
  document.getElementById('adminModal').hidden = false;
  requestAnimationFrame(() => {
    document.getElementById('adminBackdrop').classList.add('show');
    document.getElementById('adminModal').classList.add('show');
  });
  refreshIcons();
  if (focusSenha) document.getElementById('importSenha').focus();
}

function hideAdminModal() {
  document.getElementById('adminBackdrop').classList.remove('show');
  document.getElementById('adminModal').classList.remove('show');
  setTimeout(() => {
    document.getElementById('adminBackdrop').hidden = true;
    document.getElementById('adminModal').hidden = true;
  }, 200);
}

function closeAdminModal() {
  hideAdminModal();
  importToken = '';
  importAutenticado = false;
  document.getElementById('importSenha').value = '';
  document.getElementById('arquivoExcel').value = '';
  atualizarArquivoSelecionado();
}

async function abrirPainelImportacao() {
  await carregarImportConfig();
  importAutenticado = false;
  importToken = '';

  if (importConfig.disponivel === false) {
    const msg = importConfig.motivo_bloqueio || 'Importação indisponível no momento.';
    document.getElementById('adminBlockedMsg').textContent = msg;
    showAdminStep('blocked');
    openAdminModal();
    return;
  }

  if (importConfig.requer_senha) {
    showAdminStep('auth');
    openAdminModal(true);
    return;
  }

  importAutenticado = true;
  showAdminStep('import');
  openAdminModal();
}

async function autenticarImportacao() {
  const senha = document.getElementById('importSenha').value;
  const err = document.getElementById('importAuthError');
  err.hidden = true;
  if (!senha.trim()) {
    err.textContent = 'Informe a senha de acesso.';
    err.hidden = false;
    return;
  }
  try {
    const res = await fetch(API + '/api/importacao/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ senha }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Senha incorreta');
    importToken = data.token || '';
    importAutenticado = true;
    showAdminStep('import');
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
  }
}

function atualizarArquivoSelecionado() {
  const input = document.getElementById('arquivoExcel');
  const info = document.getElementById('arquivoSelecionadoInfo');
  const btn = document.getElementById('btnImportar');
  const label = document.getElementById('btnSelecionarArquivo');
  const labelText = document.getElementById('btnSelecionarTexto');
  if (input.files.length) {
    const file = input.files[0];
    info.textContent = `Planilha selecionada: ${file.name} (${formatFileSize(file.size)})`;
    info.classList.add('has-file');
    label.classList.add('has-file');
    if (labelText) labelText.textContent = 'Trocar planilha';
    btn.disabled = false;
  } else {
    info.textContent = 'Nenhuma planilha selecionada';
    info.classList.remove('has-file');
    label.classList.remove('has-file');
    if (labelText) labelText.textContent = 'Selecionar planilha';
    btn.disabled = true;
  }
}

document.getElementById('arquivoExcel').addEventListener('change', atualizarArquivoSelecionado);

document.getElementById('btnAdminGear').addEventListener('click', abrirPainelImportacao);
document.getElementById('btnCloseAdmin').addEventListener('click', closeAdminModal);
document.getElementById('adminBackdrop').addEventListener('click', closeAdminModal);
document.getElementById('btnImportAuth').addEventListener('click', autenticarImportacao);
document.getElementById('importSenha').addEventListener('keydown', e => {
  if (e.key === 'Enter') autenticarImportacao();
});

document.getElementById('btnImportar').addEventListener('click', async () => {
  const input = document.getElementById('arquivoExcel');
  if (!input.files.length) { toast('Selecione uma planilha Excel para importar'); return; }
  if (importConfig.requer_senha && !importAutenticado) {
    toast('Informe a senha de acesso para importar');
    showAdminStep('auth');
    return;
  }
  const fd = new FormData();
  fd.append('arquivo', input.files[0]);
  const headers = importFetchHeaders();
  hideAdminModal();
  setLoading(true, 'Importando planilha', 'import');
  try {
    const res = await fetch(API + '/api/importacao/arquivo', {
      method: 'POST',
      headers,
      body: fd,
    });
    const data = await res.json();
    if (res.status === 401) {
      importAutenticado = false;
      importToken = '';
      showAdminStep('auth');
      openAdminModal(true);
      throw new Error('Senha necessária novamente.');
    }
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Falha na importação');
    toast(data.mensagem);
    await carregarDashboard();
    closeAdminModal();
  } catch (e) {
    toast('Erro: ' + e.message);
  } finally {
    if (document.getElementById('loading').classList.contains('show')) {
      finishLoading();
    }
  }
});

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    Object.values(charts).forEach(c => c?.resize());
    const panel = document.getElementById('filterPanel');
    if (isDesktop()) {
      panel.classList.remove('open');
    } else {
      panel.classList.remove('expanded');
    }
  }, 150);
});

initAutocompletes();
refreshIcons();
syncDocumentTitle();
carregarImportConfig();
atualizarPagina('captura');
carregarDashboard();
