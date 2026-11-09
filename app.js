const COLORS = {normal:'#a8a77a',fire:'#ee8130',water:'#6390f0',electric:'#d6a900',grass:'#4caf50',ice:'#4fc3c3',fighting:'#c22e28',poison:'#a33ea1',ground:'#c9a24a',flying:'#8f7fd8',psychic:'#f95587',bug:'#a6b91a',rock:'#a38c21',ghost:'#735797',dragon:'#6f35fc',dark:'#5a4a3f',steel:'#8a8aa8',fairy:'#d685ad'};
const STATS = [['hp','HP'],['attack','ATK'],['defense','DEF'],['spatk','SP.ATK'],['spdef','SP.DEF'],['speed','SPD']];
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pad = n => String(n).padStart(4, '0');
let DATA = [], cur = null;

fetch('data.json')
  .then(r => { if (!r.ok) throw 0; return r.json(); })
  .then(d => { DATA = d; setupFilters(); apply(); })
  .catch(() => {
    $('screen').innerHTML = '<div class="msg">Could not load <code>data.json</code>.<br>Run <code>python build_data.py --serve</code> ' +
      'and open the dashboard from <code>http://localhost:8000</code> (browsers block loading data when opening the file directly).</div>';
  });

function setupFilters() {
  const types = [...new Set(DATA.flatMap(p => p.types))].sort();
  const gens = [...new Set(DATA.map(p => p.gen).filter(Boolean))].sort((a, b) => a - b);
  $('type').innerHTML += types.map(t => `<option value="${t}">${t[0].toUpperCase() + t.slice(1)}</option>`).join('');
  $('gen').innerHTML += gens.map(g => `<option value="${g}">Generation ${g}</option>`).join('');
}

function apply() {
  const q = $('q').value.trim().toLowerCase().replace(/^#/, ''), t = $('type').value, g = $('gen').value;
  const out = DATA.filter(p => {
    if (t && !p.types.includes(t)) return false;
    if (g && String(p.gen) !== g) return false;
    if (q) {
      if (/^\d+$/.test(q)) return String(p.id).includes(q);
      return p.name.toLowerCase().includes(q);
    }
    return true;
  });
  $('count').textContent = `${out.length} Pokémon found`;
  $('list').innerHTML = out.slice(0, 400).map(p =>
    `<div class="row${p === cur ? ' on' : ''}" data-i="${DATA.indexOf(p)}"><b>#${pad(p.id)}</b>` +
    `<img loading="lazy" src="${esc(p.img)}" alt="" onerror="this.style.visibility='hidden'"><span>${esc(p.name)}</span></div>`
  ).join('') + (out.length > 400 ? '<p class="count">Showing first 400 — refine your search</p>' : '');
  if (!out.length) { cur = null; $('screen').innerHTML = '<div class="msg">No Pokémon match your filters.</div>'; }
  else if (!out.includes(cur)) show(out[0]);
}

function radar(s) {
  const cx = 130, cy = 120, R = 85, MAX = 255, n = STATS.length;
  const pt = (i, v) => { const a = -Math.PI / 2 + i * 2 * Math.PI / n; return [cx + Math.cos(a) * R * v, cy + Math.sin(a) * R * v]; };
  const poly = f => STATS.map((_, i) => pt(i, f(i)).join(',')).join(' ');
  let svg = '<svg viewBox="0 0 260 245" class="chart">';
  [.25, .5, .75, 1].forEach(l => svg += `<polygon points="${poly(() => l)}" fill="none" stroke="#166534" stroke-opacity=".35"/>`);
  STATS.forEach((_, i) => { const [x, y] = pt(i, 1); svg += `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#166534" stroke-opacity=".35"/>`; });
  svg += `<polygon points="${poly(i => Math.min(s[STATS[i][0]] / MAX, 1))}" fill="#dc2626" fill-opacity=".55" stroke="#8f1111" stroke-width="2.5"/>`;
  STATS.forEach(([k, l], i) => {
    const [x, y] = pt(i, 1.2);
    svg += `<text x="${x}" y="${y}" font-size="11" font-weight="800" text-anchor="middle" fill="#10231a">${l}</text>` +
           `<text x="${x}" y="${y + 12}" font-size="11" font-weight="800" text-anchor="middle" fill="#8f1111">${s[k]}</text>`;
  });
  return svg + '</svg>';
}

function show(p) {
  cur = p;
  $('screen').innerHTML = `
    <div class="top">
      <div class="art"><img src="${esc(p.img)}" alt="${esc(p.name)}" onerror="this.replaceWith(document.createTextNode('No image'))"></div>
      <div>
        <div class="id">No. ${pad(p.id)}</div>
        <div class="name">${esc(p.name)}</div>
        <div class="genus">${esc(p.genus || '—')}</div>
        <div>${p.types.map(t => `<span class="badge" style="background:${COLORS[t] || '#666'}">${esc(t)}</span>`).join('')}</div>
        ${p.gen ? `<div class="gen">GENERATION ${p.gen} · BASE TOTAL ${p.total}</div>` : ''}
        ${radar(p.stats)}
      </div>
    </div>
    <div class="desc"><small>▶ POKÉDEX ENTRY</small>${esc(p.desc || 'No entry recorded.')}</div>`;
  document.querySelectorAll('.row').forEach(r => r.classList.toggle('on', DATA[r.dataset.i] === p));
}

$('list').addEventListener('click', e => { const r = e.target.closest('.row'); if (r) show(DATA[r.dataset.i]); });
['q', 'type', 'gen'].forEach(id => $(id).addEventListener('input', apply));
