(() => {
  'use strict';
  const root = document.querySelector('.village-attendance-page');
  if (!root || !window.MV) return;
  const $ = (s) => document.querySelector(s);
  const esc = window.MV.escapeHtml;
  const form = $('#village-attendance-form');
  const village = $('#village-select');

  const cards = $('#committee-attendance-cards');
  const planNote = $('#village-plan-note');
  const error = $('#entry-error');
  const status = $('#draft-state');
  const send = $('#submit-village-attendance');
  const locationLabel = $('#location-label');
  const locationDetail = $('#location-detail');
  const locationButton = $('#retry-location');
  const preview = $('#photo-preview');
  const otherCancel = $('#other-village-cancel');
  const otherStatus = $('#other-village-status');
  const OTHER_VILLAGES = '__other_villages__';
  let selectedVillageId = '';
  const otherPanel = $('#other-village-panel');
  const otherQuery = $('#other-village-query');
  const otherResults = $('#other-village-results');
  const newMembersField = $('#village-new-members');
  let availableVillages = [];
  let selectedOutside = false;
  const params = new URLSearchParams(location.search);
  let submissionId = crypto.randomUUID();
  let allCommittees = [];
  let photo = null;
  let previewUrl = null;
  let requestId = 0;
  let coords = null;
  let busy = false;
  let visitSubmitted = false;
  // Browser-facing date is read-only; server clock remains authoritative.
  function refreshToday() {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric',
    }).formatToParts(new Date()).map(piece => [piece.type, piece.value]));
    $('#visit-date').value = `${parts.day} ${parts.month} ${parts.year}`;
  }
  refreshToday();
  window.setInterval(refreshToday, 60_000);
  send.disabled = true;

  const pending = () => allCommittees;
  const showError = (text) => { error.textContent = text; error.classList.remove('hidden'); error.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); };
  const clearError = () => { error.textContent = ''; error.classList.add('hidden'); };
  async function get(url) {
    const response = await window.MV.api(url);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Unable to load data.');
    return payload;
  }
  function validCoords(p) {
    if (p?.latitude == null || p?.longitude == null || String(p.latitude).trim() === '' || String(p.longitude).trim() === '') return false;
    const lat = Number(p?.latitude), lon = Number(p?.longitude);
    return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180 && (Math.abs(lat) > 0.000001 || Math.abs(lon) > 0.000001);
  }
  const locationUpdate = (ev) => {
    const point = ev.detail;
    if (validCoords(point)) {
      coords = { latitude: Number(point.latitude), longitude: Number(point.longitude), capturedAt: point.capturedAt || Date.now() };
      locationLabel.textContent = 'GPS captured';
      locationDetail.textContent = `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)} · ±${Math.round(point.accuracy || 0)} m`;
      locationButton.textContent = 'Refresh GPS';
    } else {
      coords = null;
      locationLabel.textContent = 'Location required';
      locationDetail.textContent = point?.message || 'Enable location services and allow access to this website.';
      locationButton.textContent = 'Enable location';
    }
  };
  window.addEventListener('mv:location', locationUpdate);
  locationButton.addEventListener('click', () => window.MVLocation?.capture(true));
  if (window.MVLocation?.last) locationUpdate({ detail: window.MVLocation.last });
  else window.MVLocation?.capture();

  const normalizedGender = (value) => String(value || '').trim().toLowerCase();
  const roleClass = (role) => {
    const key = String(role || '').trim().toLowerCase().replace(/[^a-z]+/g, '-');
    return ['president', 'vice-president', 'secretary'].includes(key) ? key : 'member';
  };
  // Individual name tiles retain member IDs and gender metadata for validated counts.
  // Gender is never printed on the card. All roles share the same simple grid.
  function roleGroups(members) {
    const order = ['President', 'Vice President', 'Secretary', 'Member'];
    const names = (members || []).map(member => {
      const raw = String(member.designation || 'Member').trim();
      const role = order.find(value => value.toLowerCase() === raw.toLowerCase()) || 'Member';
      return { ...member, role };
    });
    names.sort((a, b) => order.indexOf(a.role) - order.indexOf(b.role));
    if (!names.length) return '<p class="field-help">No active members in Master Data. Ask PC/Admin to check the member list.</p>';
    return `<div class="attendance-name-grid">${names.map(member => `
      <button type="button" class="attendee-chip attendee-role-${roleClass(member.role)}" data-visit-member="${Number(member.id)}" data-gender="${esc(normalizedGender(member.gender))}" aria-pressed="false" aria-label="${esc(member.name)}, ${esc(member.role)}, not selected">
        <span class="attendee-chip-name">${esc(member.name)}</span><span class="attendee-chip-role">${esc(member.role)}</span><span class="attendee-chip-check" aria-hidden="true">✓</span>
      </button>`).join('')}</div>`;
  }
  function selectedCounts(row) {
    const selected = [...row.querySelectorAll('[data-visit-member][aria-pressed="true"]')];
    return {
      male: selected.filter(node => node.dataset.gender === 'male').length,
      female: selected.filter(node => node.dataset.gender === 'female').length,
      unknown: selected.filter(node => !['male', 'female'].includes(node.dataset.gender)).length,
      ids: selected.map(node => Number(node.dataset.visitMember)),
    };
  }
  function setSubmitState() {
    send.disabled = busy || !selectedVillageId || village.value !== selectedVillageId || pending().length === 0 || visitSubmitted;
  }
  function updateCounts() {
    let male = 0, female = 0, active = 0;
    for (const item of pending()) {
      const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
      if (!row) continue;
      const count = selectedCounts(row);
      male += count.male; female += count.female;
      if (count.ids.length) active += 1;
      row.querySelector('[data-committee-total]').textContent = `${count.ids.length} / ${(item.members || []).length}`;
      const rowCounts = row.querySelector('[data-committee-counts]');
      if (rowCounts) rowCounts.textContent = `Male ${count.male} · Female ${count.female} · Total ${count.ids.length}`;
      row.classList.toggle('has-selection', count.ids.length > 0);
      row.querySelector('[data-gender-alert]').classList.toggle('hidden', count.unknown === 0);
    }
    $('#village-male').textContent = String(male);
    $('#village-female').textContent = String(female);
    $('#village-total').textContent = String(male + female);
    root.querySelector('.ref-progress').hidden = !pending().length;
    $('#committee-progress').textContent = `${active} of ${pending().length} recorded`;
    $('#committee-progress-bar').style.width = `${pending().length ? Math.round(100 * active / pending().length) : 0}%`;
  }
  function render() {
    const eligible = pending();
    $('#summary-committees').textContent = `${allCommittees.length} committees`;
    planNote.classList.toggle('form-alert', visitSubmitted);
    planNote.classList.toggle('hidden', !visitSubmitted);
    planNote.textContent = visitSubmitted ? 'This village already has an attendance entry this month. Choose another village.' : '';
    status.textContent = visitSubmitted ? 'Already recorded this month' : eligible.length ? 'Ready to record' : 'No committees in this village';
    setSubmitState();
    if (!allCommittees.length) {
      cards.innerHTML = '<div class="empty-state">No active committees in this village.</div>';
      updateCounts(); return;
    }
    cards.innerHTML = allCommittees.map((item, idx) => `
      <details class="mv-committee-card" data-committee-id="${item.id}" data-ready="true" >
        <summary><span class="ref-committee-icon">${window.BVUI.icon(/water/i.test(item.name)?'water':/health/i.test(item.name)?'heart':/youth/i.test(item.name)?'gear':/vdc/i.test(item.name)?'building':/environment|farm/i.test(item.name)?'leaf':'users')}</span><span class="mv-committee-number">${idx + 1}</span><span class="mv-committee-name"><strong>${esc(item.name)}</strong><small>${(item.members || []).length} registered members</small></span><span class="committee-selected-count" data-committee-total>0 present</span><span class="committee-chevron" aria-hidden="true">⌄</span></summary>
        <div class="mv-committee-details"><div class="attendee-help">Tap a name to mark present. Tap again to undo.</div><div class="mv-member-list">${roleGroups(item.members)}</div><div data-gender-alert class="form-alert hidden">A selected member is missing gender in Master Data. Ask Admin to correct it before submitting.</div><button type="button" class="button ghost next-committee" data-next-committee>Next committee ↓</button></div>
      </details>`).join('');
    cards.querySelectorAll('.mv-committee-card').forEach(row => {
      row.addEventListener('toggle', () => {
        if (row.open) cards.querySelectorAll('.mv-committee-card[open]').forEach(other => { if (other !== row) other.open = false; });
      });
    });
    updateCounts();
  }
  cards.addEventListener('click', event => {
    const chip = event.target.closest('[data-visit-member]');
    if (chip && cards.contains(chip)) {
      const checked = chip.getAttribute('aria-pressed') !== 'true';
      chip.setAttribute('aria-pressed', String(checked));
      chip.setAttribute('aria-label', `${chip.querySelector('.attendee-chip-name').textContent}, ${chip.querySelector('.attendee-chip-role').textContent}, ${checked ? 'selected' : 'not selected'}`);
      updateCounts(); return;
    }
    const next = event.target.closest('[data-next-committee]');
    if (!next || !cards.contains(next)) return;
    const row = next.closest('.mv-committee-card');
    row.open = false;
    const rows = [...cards.querySelectorAll('.mv-committee-card[data-ready="true"]')];
    const index = rows.indexOf(row);
    const following = rows[index + 1];
    if (following) { following.open = true; following.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
    else $('.village-final-section').scrollIntoView({ block: 'start', behavior: 'smooth' });
  });
  async function loadVillage(id) {
    const stamp = ++requestId;
    allCommittees = []; visitSubmitted = false;
    setSubmitState(); updateCounts();
    planNote.classList.add('hidden');
    $('#summary-committees').textContent = id ? 'Loading committees...' : 'Select a village to start';
    status.textContent = id ? 'Loading village...' : 'Select a village';
    cards.innerHTML = id ? '<div class="empty-state">Loading committees and members...</div>' : '<div class="empty-state">Choose a village to begin.</div>';
    if (!id) return;
    try {
      const data = await get(`/api/v1/attendance/villages/${encodeURIComponent(id)}/details`);
      if (stamp !== requestId) return;
      allCommittees = data.items || []; visitSubmitted = Boolean(data.submitted);
      render();
    } catch (e) {
      if (stamp !== requestId) return;
      cards.innerHTML = '<div class="empty-state">Unable to load committees. Choose the village again to retry.</div>';
      $('#summary-committees').textContent = 'Village details unavailable';
      status.textContent = 'Unable to load village';
      showError(e.message);
    }
  }
  // The sentinel opens the picker. It is never sent as a village ID.
  const assignedOptions = () => {
    const options = [new Option('Select assigned village', '')];
    for (const item of availableVillages.filter(v => v.assigned)) {
      options.push(new Option(item.name, String(item.id)));
    }
    if (selectedOutside) {
      const other = availableVillages.find(v => String(v.id) === selectedVillageId);
      if (other) options.push(new Option(`${other.name} (Other)`, String(other.id)));
    }
    options.push(new Option('Other Villages', OTHER_VILLAGES));
    village.replaceChildren(...options);
    village.value = selectedVillageId;
  };
  function renderOtherResults() {
    const query = otherQuery.value.trim().toLowerCase();
    const matched = availableVillages.filter(v => !v.assigned &&
      (!query || [v.name, v.mandal, v.district].filter(Boolean).join(' ').toLowerCase().includes(query)));
    otherStatus.textContent = `${matched.length} ${matched.length === 1 ? 'village' : 'villages'} found`;
    otherResults.innerHTML = matched.length ? matched.map(v =>
      `<button type="button" class="other-village-choice" data-other-id="${Number(v.id)}">${esc(v.name)} <small>${esc([v.mandal, v.district].filter(Boolean).join(' / '))}</small></button>`
    ).join('') : '<p class="field-help">No matching village. Try another name, mandal or district.</p>';
  }
  function openOtherPicker() {
    otherQuery.value = '';
    renderOtherResults();
    otherPanel.classList.remove('hidden');
    setSubmitState();
    otherQuery.focus();
  }
  function closeOtherPicker({ restoreSelection = true, focus = false } = {}) {
    otherPanel.classList.add('hidden');
    if (restoreSelection) village.value = selectedVillageId;
    setSubmitState();
    if (focus) village.focus();
  }
  function chooseVillage(id, focus = false) {
    const target = availableVillages.find(v => String(v.id) === String(id));
    if (id && !target) return;
    const nextId = target ? String(target.id) : '';
    const changed = nextId !== selectedVillageId;
    selectedVillageId = nextId;
    selectedOutside = Boolean(target && !target.assigned);
    assignedOptions();
    closeOtherPicker({ restoreSelection: false, focus });
    clearError();
    // Re-selecting the same village preserves entered attendance. A failed
    // details request can still be retried by choosing that village again.
    if (changed || (nextId && allCommittees.length === 0)) loadVillage(nextId);
  }
  otherCancel.addEventListener('click', () => closeOtherPicker({ focus: true }));
  otherPanel.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closeOtherPicker({ focus: true });
    }
  });
  otherQuery.addEventListener('input', renderOtherResults);
  otherQuery.addEventListener('keydown', event => {
    if (event.key === 'Enter') event.preventDefault();
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      otherResults.querySelector('[data-other-id]')?.focus();
    }
  });
  otherResults.addEventListener('click', event => {
    const option = event.target.closest('[data-other-id]');
    if (!option || !otherResults.contains(option)) return;
    chooseVillage(option.dataset.otherId, true);
  });
  village.addEventListener('change', () => {
    if (village.value === OTHER_VILLAGES) {
      openOtherPicker();
      return;
    }
    chooseVillage(village.value);
  });
  (async () => {
    try {
      const data = await get('/api/v1/attendance/villages');
      availableVillages = data.items || [];
      assignedOptions(); village.disabled = false;
      const selectedVillage = params.get('village');
      if (selectedVillage && availableVillages.some(v => String(v.id) === selectedVillage)) {
        chooseVillage(selectedVillage);
      }
    } catch (e) { showError(e.message); }
  })();

  async function compress(file) {
    if (!file.type.startsWith('image/')) throw new Error('Select a supported image.');
    if (file.size > 12 * 1024 * 1024) throw new Error('Image must be smaller than 12 MB.');
    const bitmap = 'createImageBitmap' in window ? await createImageBitmap(file) : await new Promise((resolve, reject) => {
      const img = new Image(), url = URL.createObjectURL(file);
      img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
      img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Unable to read image.')); }; img.src = url;
    });
    const ratio = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * ratio); canvas.height = Math.round(bitmap.height * ratio);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#f4f6f5'; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close?.();
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/webp', 0.82));
    if (!blob) throw new Error('Unable to compress image.');
    return new File([blob], `village-${submissionId}.webp`, { type: 'image/webp' });
  }
  const inputs = { camera: $('#camera-file'), album: $('#album-file'), files: $('#files-file') };
  document.querySelectorAll('[data-photo-picker]').forEach(btn => btn.addEventListener('click', () => inputs[btn.dataset.photoPicker]?.click()));
  for (const input of Object.values(inputs)) input.addEventListener('change', async () => {
    if (!input.files?.[0]) return;
    try {
      photo = await compress(input.files[0]);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = URL.createObjectURL(photo); preview.querySelector('img').src = previewUrl; preview.classList.remove('hidden');
      status.textContent = `${Math.round(photo.size / 1024)} KB photo ready`;
    } catch (e) { showError(e.message); }
  });
  $('#remove-photo').addEventListener('click', () => {
    photo = null; preview.classList.add('hidden');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; for (const input of Object.values(inputs)) input.value = '';
  });
  function body() {
    const eligible = pending();
    if (!eligible.length) throw new Error('This village has no active committees.');
    if (visitSubmitted) throw new Error('Attendance is already recorded for this village this month.');
    const sharedRemarks = $('#village-notes').value.trim();
    const newMembers = Number(newMembersField.value || 0);
    if (!Number.isInteger(newMembers) || newMembers < 0 || newMembers > 9999) throw new Error('Enter a valid village-wide new members number.');
    const entries = eligible.map(item => {
      const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
      const people = selectedCounts(row);
      if (people.unknown) throw new Error(`Selected members in ${item.name} have missing gender. Ask Admin to correct Master Data.`);
      return { committee_id: item.id, counts_mode: 'selected_members', visit_member_ids: people.ids };
    });
    if (!photo) throw new Error('Attach one evidence photo for the village.');
    if (!validCoords(coords)) { window.MVLocation?.capture(true); throw new Error('Current GPS location is required.'); }
    if (Date.now() - coords.capturedAt > 2 * 60 * 1000) { window.MVLocation?.capture(true); throw new Error('GPS fix is older than 2 minutes. Refreshing now.'); }
    const data = new FormData();
    data.append('client_submission_id', submissionId);
    data.append('village_id', village.value);
    // Entry date is assigned by the server; it cannot be altered from this form.
    data.append('other_village', selectedOutside ? '1' : '0');
    data.append('new_members_count', String(newMembers));
    data.append('latitude', coords.latitude.toFixed(6));
    data.append('longitude', coords.longitude.toFixed(6));
    data.append('remarks', sharedRemarks);
    data.append('committees', JSON.stringify(entries));
    data.append('photo', photo, photo.name);
    return data;
  }
  function reset() {
    submissionId = crypto.randomUUID(); form.reset();
    $('#village-notes').dispatchEvent(new Event('input'));
    otherPanel.classList.add('hidden');
    refreshToday();
    ++requestId;
    selectedVillageId = ''; selectedOutside = false; assignedOptions();
    allCommittees = []; visitSubmitted = false; busy = false; setSubmitState();
    planNote.classList.remove('form-alert'); planNote.classList.add('hidden');
    $('#summary-committees').textContent = '0 committees';
    cards.innerHTML = '<div class="empty-state">Select a village to begin.</div>';
    $('#village-male').textContent = '0'; $('#village-female').textContent = '0'; $('#village-total').textContent = '0';
    root.querySelector('.ref-progress').hidden = true;
    $('#committee-progress').textContent = '0 of 0 committees'; $('#committee-progress-bar').style.width = '0%';
    photo = null; preview.classList.add('hidden');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; status.textContent = 'Select a village';
  }
  form.addEventListener('submit', async event => {
    event.preventDefault(); clearError(); refreshToday();
    if (!selectedVillageId || village.value !== selectedVillageId) return showError('Choose a village from the list before submitting.');
    let data; try { data = body(); } catch (e) { return showError(e.message); }
    busy = true; setSubmitState(); status.textContent = navigator.onLine ? 'Submitting village visit…' : 'Saving visit offline…';
    try {
      if (!navigator.onLine) {
        if (!window.MVQueue) throw new Error('Offline queue unavailable on this device.');
        await window.MVQueue.enqueue({ id: submissionId, userId: window.MV.userId, url: '/api/v1/attendance/village', method: 'POST', formData: data, entryType: 'attendance' });
        window.dispatchEvent(new CustomEvent('mv:queued'));
        window.MV.toast('Village attendance saved offline for sync.', 'success');
      } else {
        const res = await window.MV.api('/api/v1/attendance/village', { method: 'POST', body: data });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Submission failed.');
        if (result.queued) window.MV.toast('Village attendance queued for sync.', 'success');
        else window.MV.toast(`${result.committee_count} committees submitted in one visit.`, 'success');
      }
      reset();
    } catch (e) { showError(e.message); status.textContent = 'Not submitted'; }
    finally { busy = false; setSubmitState(); }
  });
})();
