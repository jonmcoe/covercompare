/* CoverCompare frontend */

let allPapers = [];   // [{key, name, format}]
let allConfigs = {};  // {name: [keys]}
let defaultPapers = [];
let selectedPapers = [];  // ordered list of paper keys

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function init() {
  const data = await fetch('/api/papers').then(r => r.json());
  allPapers = data.papers;
  allConfigs = data.configs || {};
  defaultPapers = data.default || [];

  buildPresets();
  buildDropdown();
  bindDropdown();
  bindSubTabs();
  bindSubscribeForm();
  bindUnsubscribeForm();

  // Load national as default
  const firstConfig = Object.keys(allConfigs)[0];
  const startKey = allConfigs['national'] ? 'national' : firstConfig;
  setSelectedPapers(allConfigs[startKey] || [], startKey);
}

// ---------------------------------------------------------------------------
// Presets
// ---------------------------------------------------------------------------

function buildPresets() {
  const container = document.getElementById('presets');
  container.innerHTML = '';

  for (const [name, keys] of Object.entries(allConfigs)) {
    const label = name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' ');
    container.appendChild(makePresetBtn(label, name, keys));
  }
}

function makePresetBtn(label, id, keys) {
  const btn = document.createElement('button');
  btn.className = 'preset-btn';
  btn.dataset.presetId = id;
  btn.textContent = label;
  btn.addEventListener('click', () => setSelectedPapers(keys, id));
  return btn;
}

function setActivePreset(presetId) {
  document.querySelectorAll('.preset-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.presetId === presetId);
  });
}

// ---------------------------------------------------------------------------
// Dropdown paper picker
// ---------------------------------------------------------------------------

function buildDropdown() {
  const dropdown = document.getElementById('paper-dropdown');
  dropdown.innerHTML = '';

  const filter = document.createElement('input');
  filter.type = 'text';
  filter.id = 'paper-filter';
  filter.placeholder = 'Filter papers…';
  dropdown.appendChild(filter);

  const sorted = [...allPapers].sort((a, b) => a.name.localeCompare(b.name));
  sorted.forEach(paper => {
    const item = document.createElement('label');
    item.className = 'paper-check-item';
    item.dataset.name = paper.name.toLowerCase();

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = paper.key;
    cb.addEventListener('change', () => onCheckboxChange());

    item.appendChild(cb);
    item.appendChild(document.createTextNode(paper.name));
    dropdown.appendChild(item);
  });

  filter.addEventListener('input', () => {
    const q = filter.value.toLowerCase();
    dropdown.querySelectorAll('.paper-check-item').forEach(item => {
      item.style.display = item.dataset.name.includes(q) ? '' : 'none';
    });
  });
}

function bindDropdown() {
  const btn = document.getElementById('paper-dropdown-btn');
  const dropdown = document.getElementById('paper-dropdown');

  btn.addEventListener('click', e => {
    e.stopPropagation();
    const opening = !dropdown.classList.contains('open');
    dropdown.classList.toggle('open');
    if (opening) {
      const filter = document.getElementById('paper-filter');
      filter.value = '';
      dropdown.querySelectorAll('.paper-check-item').forEach(i => i.style.display = '');
      filter.focus();
    }
  });

  document.addEventListener('click', () => dropdown.classList.remove('open'));
  dropdown.addEventListener('click', e => e.stopPropagation());
}

function syncCheckboxes() {
  document.querySelectorAll('#paper-dropdown input[type=checkbox]').forEach(cb => {
    cb.checked = selectedPapers.includes(cb.value);
  });
}

function onCheckboxChange() {
  const checked = [];
  document.querySelectorAll('#paper-dropdown input[type=checkbox]').forEach(cb => {
    if (cb.checked) checked.push(cb.value);
  });
  setSelectedPapers(checked, null);
}

// ---------------------------------------------------------------------------
// Selected papers state
// ---------------------------------------------------------------------------

function setSelectedPapers(keys, presetId) {
  selectedPapers = keys.filter(k => allPapers.find(p => p.key === k));
  syncCheckboxes();
  renderChips();
  setActivePreset(presetId);
  renderViewer();
  updateSubPapersNote();
}

// ---------------------------------------------------------------------------
// Chips
// ---------------------------------------------------------------------------

function renderChips() {
  const container = document.getElementById('selected-chips');
  container.innerHTML = '';
  selectedPapers.forEach(key => {
    const paper = allPapers.find(p => p.key === key);
    if (!paper) return;
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = paper.name;
    const rm = document.createElement('span');
    rm.className = 'chip-remove';
    rm.textContent = '×';
    rm.title = 'Remove';
    rm.addEventListener('click', () => {
      setSelectedPapers(selectedPapers.filter(k => k !== key), null);
    });
    chip.appendChild(rm);
    container.appendChild(chip);
  });
}

// ---------------------------------------------------------------------------
// Viewer
// ---------------------------------------------------------------------------

function renderViewer() {
  const viewer = document.getElementById('viewer');
  const empty = document.getElementById('empty-state');

  viewer.querySelectorAll('.paper-col').forEach(col => col.remove());

  if (selectedPapers.length === 0) {
    empty.style.display = '';
    return;
  }

  empty.style.display = 'none';

  selectedPapers.forEach(key => {
    const paper = allPapers.find(p => p.key === key);
    if (!paper) return;
    const col = buildColumn(paper);
    viewer.appendChild(col);
    loadColumnImage(col, key);
  });
}

function buildColumn(paper) {
  const col = document.createElement('div');
  col.className = 'paper-col';
  col.dataset.key = paper.key;

  const nameEl = document.createElement('div');
  nameEl.className = 'paper-col-name';
  nameEl.textContent = paper.name;
  col.appendChild(nameEl);

  const loading = document.createElement('div');
  loading.className = 'loading';
  loading.textContent = 'Loading…';
  col.appendChild(loading);

  return col;
}

function loadColumnImage(col, key) {
  const d = new Date();
  const today = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  const img = new Image();
  img.loading = 'eager';

  img.onload = () => {
    const placeholder = col.querySelector('.loading, .error');
    if (placeholder) placeholder.replaceWith(img);
    img.addEventListener('click', () => openZoom(img.src));
  };

  img.onerror = () => {
    const err = document.createElement('div');
    err.className = 'error';
    err.textContent = 'Failed to load';
    const placeholder = col.querySelector('.loading, .error, img');
    if (placeholder) placeholder.replaceWith(err);
  };

  img.src = `/api/paper/${encodeURIComponent(key)}?date=${today}`;
}

// ---------------------------------------------------------------------------
// Subscription section
// ---------------------------------------------------------------------------

function bindSubTabs() {
  document.querySelectorAll('.sub-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.sub-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`panel-${tab.dataset.panel}`).classList.add('active');
    });
  });
}

function updateSubPapersNote() {
  const note = document.getElementById('sub-papers-note');
  if (selectedPapers.length === 0) {
    note.textContent = 'No papers selected — select some above first.';
    note.style.color = '#f0a050';
  } else {
    const names = selectedPapers.map(k => {
      const p = allPapers.find(x => x.key === k);
      return p ? p.name : k;
    });
    note.textContent = names.join(', ');
    note.style.color = '#666';
  }
}

function bindSubscribeForm() {
  const btn = document.getElementById('sub-btn');
  const msg = document.getElementById('sub-msg');

  btn.addEventListener('click', async () => {
    msg.textContent = '';
    msg.className = '';

    const webhook_url = document.getElementById('sub-webhook').value.trim();
    const label = document.getElementById('sub-label').value.trim() || null;
    const papers = [...selectedPapers];

    if (!webhook_url) {
      msg.textContent = 'Please enter a Discord webhook URL.';
      msg.className = 'err';
      return;
    }
    if (papers.length === 0) {
      msg.textContent = 'Select at least one paper above.';
      msg.className = 'err';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Sending test…';

    try {
      const res = await fetch('/api/subscriptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url, papers, label }),
      });
      const data = await res.json();
      if (!res.ok) {
        msg.textContent = data.error || 'Error creating subscription.';
        msg.className = 'err';
        return;
      }

      document.getElementById('sub-id-display').textContent = data.id;
      document.getElementById('token-result').style.display = 'block';
      msg.textContent = 'Subscribed! Test image delivered to your Discord.';
      msg.className = 'ok';
    } catch (e) {
      msg.textContent = 'Network error — please try again.';
      msg.className = 'err';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Subscribe & Send Test';
    }
  });

}

function bindUnsubscribeForm() {
  const btn = document.getElementById('unsub-btn');
  const msg = document.getElementById('unsub-msg');

  btn.addEventListener('click', async () => {
    msg.textContent = '';
    msg.className = '';

    const id = document.getElementById('unsub-id').value.trim();
    const token = document.getElementById('unsub-token').value.trim();

    if (!id || !token) {
      msg.textContent = 'Please enter your subscription ID and webhook URL.';
      msg.className = 'err';
      return;
    }

    btn.disabled = true;

    try {
      const res = await fetch(`/api/subscriptions/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { 'X-Webhook-Url': token },
      });
      if (res.status === 204) {
        msg.textContent = 'Unsubscribed successfully.';
        msg.className = 'ok';
      } else if (res.status === 403) {
        msg.textContent = 'Invalid ID or webhook URL.';
        msg.className = 'err';
      } else {
        msg.textContent = `Error: HTTP ${res.status}`;
        msg.className = 'err';
      }
    } catch (e) {
      msg.textContent = 'Network error — please try again.';
      msg.className = 'err';
    } finally {
      btn.disabled = false;
    }
  });
}

// ---------------------------------------------------------------------------
// Zoom modal
// ---------------------------------------------------------------------------

function openZoom(src) {
  const modal = document.getElementById('zoom-modal');
  document.getElementById('zoom-img').src = src;
  modal.classList.add('open');
}

function closeZoom() {
  document.getElementById('zoom-modal').classList.remove('open');
}

function bindZoomModal() {
  const modal = document.getElementById('zoom-modal');
  modal.addEventListener('click', closeZoom);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeZoom(); });
}

// ---------------------------------------------------------------------------
// Discord section toggle
// ---------------------------------------------------------------------------

function bindSubToggle() {
  const toggle = document.getElementById('sub-toggle');
  const content = document.getElementById('sub-content');
  toggle.addEventListener('click', () => {
    const open = toggle.classList.toggle('open');
    content.style.display = open ? 'block' : 'none';
  });
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

init().catch(console.error);
bindSubToggle();
bindZoomModal();
