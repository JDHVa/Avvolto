function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    const target = document.getElementById(`screen-${name}`);
    if (target) target.classList.remove('hidden');
}

const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');

fileInput.addEventListener('change', e => {
    if (e.target.files[0]) uploadFile(e.target.files[0]);
});

dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
});

const API_URL = 'https://TU_USUARIO-avvolto.hf.space';

async function uploadFile(file) {
    if (!file.name.endsWith('.txt')) {
        showError('Onlu .txt files exported from whatsapp are supported sorry bro :)');
        return;
    }
    showScreen('loading');

    const form = new FormData();
    form.append('file', file);

    try {
        const res = await fetch(API_URL + '/analyze', { method: 'POST', body: form });
        const text = await res.text();
        
        let data;
        try {
            data = JSON.parse(text);
        } catch (parseErr) {
            showError('Server sent an invalid response. Check console.');
            console.error("Parse Error:", parseErr, text);
            return;
        }
    
        if (!res.ok) {
            showError(data.error || 'Analysis failed');
            return;
        }

        renderResults(data);
        showScreen('results');
    
    } catch (err) {
        showError('Could not connect to the server. Please try again');
        console.error("Fetch Error:", err);
    }
}

function renderResults(data) {
    document.getElementById('res-dates').innerHTML = `<strong>${data.fecha_inicio}</strong> → <strong>${data.fecha_fin}</strong>`;
    document.getElementById('res-type').textContent = data.tipo_chat === 'grupo' ? 'Group chat' : 'individual chat';
    document.getElementById('res-lang').textContent = data.idioma === 'es' ? 'language: spanish': 'language: english';

    const statsRow = document.getElementById('stats-row');
    const topStat = data.stats[0];
    statsRow.innerHTML = `
        ${statCard('Total Messages', fmt(data.total_mensajes), '', 0)}
        ${statCard('Participants',   data.participantes.length, data.tipo_chat === 'grupo' ? 'group chat' : '1-on-1', 1)}
        ${statCard('Most Active',    topStat ? topStat.autor.split(' ')[0] : '—', topStat ? fmt(topStat.total_mensajes) + ' messages' : '', 2)}
        ${statCard('Date Range',     daysBetween(data.fecha_inicio, data.fecha_fin), 'days of history', 3)}
    `;

    const pgrid = document.getElementById('personalities-grid');
    const glowColors = ['#E8936A','#C97B8A','#7BA99A','#7A9EBD','#C9A84C','#A07858'];
    
    pgrid.innerHTML = data.participantes.map((autor, i) => {
        const p = data.personalidades[autor] || {};
        const s = data.sentimientos?.[autor] || {};
        const tono = s.tono || 'neutral';
        return `
        <div class="personality-card" style="animation-delay:${i * 0.08}s">
          <div class="glow" style="background:${glowColors[i % glowColors.length]}"></div>
          <div class="p-author">${autor}</div>
          <div class="p-name">${p.etiqueta || '—'}</div>
          <span class="p-tone tone-${tono}">${capitalize(tono)} vibes</span>
        </div>`;
    }).join('');

    const graficas = data.graficas;
    const opts = { responsive: true, displayModeBar: false };
    
    const chartMap = {
        'chart-participacion': 'participacion',
        'chart-timeline':      'timeline',
        'chart-horas':         'horas',
        'chart-semana':        'semana',
        'chart-respuesta':     'respuesta',
        'chart-longitud':      'longitud',
        'chart-sentimiento':   'sentimiento',
        'chart-emojis':        'emojis',
        'chart-palabras':      'palabras',
    };

    for (const [elId, key] of Object.entries(chartMap)) {
        if (graficas[key]) {
            const parsed = JSON.parse(graficas[key]);
            Plotly.react(elId, parsed.data, parsed.layout, opts);
        }
    }

    const authorGrid = document.getElementById('author-words-grid');
    authorGrid.innerHTML = '';
    data.participantes.forEach((autor, i) => {
        const clave = `palabras_${autor.toLowerCase().replace(/\s+/g, '_')}`;
        if (graficas[clave]) {
            const div = document.createElement('div');
            div.className = 'chart-card';
            div.style.animationDelay = `${i * 0.1}s`;
            const inner = document.createElement('div');
            inner.id = `chart-author-${i}`;
            div.appendChild(inner);
            authorGrid.appendChild(div);
            const parsed = JSON.parse(graficas[clave]);
            Plotly.react(`chart-author-${i}`, parsed.data, parsed.layout, opts);
        }
    });
}

function statCard(label, value, sub, delay) {
    return `
      <div class="stat-card delay-${delay + 1}">
        <div class="label">${label}</div>
        <div class="value">${value}</div>
        ${sub ? `<div class="sub">${sub}</div>` : ''}
      </div>`;
}

function fmt(n) {
    return Number(n).toLocaleString();
}

function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function daysBetween(a, b) {
    const d1 = new Date(a), d2 = new Date(b);
    return Math.round(Math.abs(d2 - d1) / (1000 * 60 * 60 * 24));
}

function showError(msg) {
    const errEl = document.getElementById('error-message');
    if (errEl) errEl.textContent = msg;
    showScreen('error');
}