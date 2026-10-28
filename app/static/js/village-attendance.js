(() => {
  'use strict';
  const root = document.querySelector('.village-attendance-page');
  if (!root || !window.MV) return;
  const $ = (s) => document.querySelector(s);
  const esc = window.MV.escapeHtml;
  const form = $('#village-attendance-form');
  const village = $('#village-select');
  const date = $('#visit-date');
  const cards = $('#committee-attendance-cards');
  const planNote = $('#village-plan-note');
  const error = $('#entry-error');
  const status = $('#draft-state');
  const send = $('#submit-village-attendance');
  const locationLabel = $('#location-label');
  const locationDetail = $('#location-detail');
  const locationButton = $('#retry-location');
  const preview = $('#photo-preview');
  const month = root.dataset.currentMonth;
  const params = new URLSearchParams(location.search);
  let submissionId = crypto.randomUUID();
  let allCommittees = [];
  let photo = null;
  let previewUrl = null;
  let requestId = 0;
  let coords = null;
  let busy = false;
  send.disabled = true;

  const pending = () => allCommittees.filter(i => i.plan && !i.plan.attendance_entry_id && !i.plan.has_recycled_attendance);
  const missing = () => allCommittees.filter(i => !i.plan || i.plan.has_recycled_attendance);
  const showError = (text) => { error.textContent = text; error.classList.remove('hidden'); error.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); };
  const clearError = () => { error.textContent = ''; error.classList.add('hidden'); };
  async function get(url) {
    const response = await window.MV.api(url);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Unable to load data.');
    return payload;
  }
  function validCoords(p) {
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
  function setSubmitState() { send.disabled = busy || !village.value || missing().length > 0 || pending().length === 0; }
  function updateCounts() {
    let male = 0, female = 0, active = 0;
    for (const item of pending()) {
      const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
      if (!row) continue;
      const count = selectedCounts(row);
      male += count.male; female += count.female;
      if (count.ids.length) active += 1;
      row.querySelector('[data-committee-total]').textContent = count.ids.length ? `${count.ids.length} present` : '';
      const rowCounts = row.querySelector('[data-committee-counts]');
      if (rowCounts) rowCounts.textContent = `Male ${count.male} · Female ${count.female} · Total ${count.ids.length}`;
      row.classList.toggle('has-selection', count.ids.length > 0);
      row.querySelector('[data-gender-alert]').classList.toggle('hidden', count.unknown === 0);
    }
    $('#village-male').textContent = String(male);
    $('#village-female').textContent = String(female);
    $('#village-total').textContent = String(male + female);
    $('#committee-progress').textContent = `${active} of ${pending().length} committees with attendance`;
    $('#committee-progress-bar').style.width = `${pending().length ? Math.round(100 * active / pending().length) : 0}%`;
  }
  function dateStatus() {
    const needsReason = pending().some(item => date.value && item.plan?.assigned_date && date.value !== item.plan.assigned_date);
    $('#shared-date-reason-wrap').classList.toggle('hidden', !needsReason);
    $('#shared-date-reason').required = needsReason;
  }
  function render() {
    const eligible = pending(), unavailable = missing();
    const completed = allCommittees.filter(item => item.plan?.attendance_entry_id);
    const needsScheduling = unavailable.length > 0;
    $('#summary-committees').textContent = `${allCommittees.length} committees`;
    $('#summary-pending').textContent = `${eligible.length} to record`;
    $('#summary-submitted').textContent = `${completed.length} submitted`;
    planNote.classList.toggle('form-alert', needsScheduling);
    planNote.classList.toggle('hidden', !needsScheduling);
    planNote.textContent = needsScheduling
      ? `${unavailable.length} committee(s) need PC scheduling or Admin restoration. ${eligible.length} scheduled · ${completed.length} completed.`
      : `${allCommittees.length} committees · ${eligible.length} to record · ${completed.length} already submitted`;
    status.textContent = needsScheduling ? 'Scheduling required' : eligible.length ? 'Ready to record' : 'No pending committees';
    setSubmitState();
    if (!allCommittees.length) {
      cards.innerHTML = '<div class="empty-state">No committees available in this village.</div>';
      $('#new-members-entries').innerHTML = '';
      updateCounts(); return;
    }
    const firstReady = allCommittees.find(item => eligible.includes(item))?.id;
    cards.innerHTML = allCommittees.map((item, idx) => {
      const plan = item.plan;
      const done = Boolean(plan?.attendance_entry_id);
      const recycled = Boolean(plan?.has_recycled_attendance);
      const ready = Boolean(plan) && !done && !recycled;
      const label = ready ? `Scheduled ${esc(plan.assigned_date)}` : done ? 'Attendance already submitted' : recycled ? 'Restore from Recycle Bin' : 'PC scheduling required';
      return `<details class="mv-committee-card" data-committee-id="${item.id}" data-ready="${ready}" ${ready && item.id === firstReady ? 'open' : ''}>
        <summary><span class="mv-committee-number">${idx + 1}</span><span class="mv-committee-name"><strong>${esc(item.name)}</strong><small>${label}</small></span><span class="committee-selected-count" data-committee-total>${ready ? '0 present' : done ? 'Done' : 'Waiting'}</span><span class="committee-chevron" aria-hidden="true">⌄</span></summary>
        ${ready ? `<div class="mv-committee-details"><div class="attendee-help">Tap a name to mark present. Tap again to undo.</div><div class="mv-member-list">${roleGroups(item.members)}</div><div data-gender-alert class="form-alert hidden">One or more selected members have missing gender in Master Data. Ask Admin/PC to correct it before submission.</div><button type="button" class="button ghost next-committee" data-next-committee>Next committee ↓</button></div>` : ''}
      </details>`;
    }).join('');
    $('#new-members-entries').innerHTML = eligible.map(item => `<label class="new-member-row"><span>${esc(item.name)}</span><input type="number" inputmode="numeric" min="0" max="9999" value="0" data-new-count="${item.id}" aria-label="New member count for ${esc(item.name)}"></label>`).join('') || '<small>No pending committees.</small>';
    cards.querySelectorAll('.mv-committee-card').forEach(row => {
      row.addEventListener('toggle', () => {
        if (!row.open) return;
        cards.querySelectorAll('.mv-committee-card[open]').forEach(other => { if (other !== row) other.open = false; });
      });
    });
    updateCounts(); dateStatus();
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
  date.addEventListener('change', dateStatus);
  async function loadVillage(id) {
    const stamp = ++requestId;
    cards.innerHTML = '<div class="empty-state">Loading committee members…</div>';
    allCommittees = []; setSubmitState();
    if (!id) { cards.innerHTML = '<div class="empty-state">Select a village.</div>'; return; }
    try {
      const base = await get(`/api/v1/villages/${encodeURIComponent(id)}/committees`);
      const batches = await Promise.all((base.items || []).map(async committee => {
        const [plans, members] = await Promise.all([
          get(`/api/v1/committees/${committee.id}/action-plans?type=Attendance&executable=1&month=${encodeURIComponent(month)}`),
          get(`/api/v1/committees/${committee.id}/members`),
        ]);
        const plan = (plans.items || []).find(p => !p.attendance_entry_id) || (plans.items || [])[0] || null;
        return { ...committee, plan, members: members.items || [] };
      }));
      if (stamp !== requestId) return;
      allCommittees = batches; render();
    } catch (e) { if (stamp === requestId) showError(e.message); }
  }
  village.addEventListener('change', () => { clearError(); loadVillage(village.value); });
  (async () => {
    try {
      const data = await get('/api/v1/villages');
      village.innerHTML = '<option value="">Select village</option>' + (data.items || []).map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
      const selectedVillage = params.get('village');
      if (selectedVillage && [...village.options].some(opt => opt.value === selectedVillage)) { village.value = selectedVillage; loadVillage(village.value); }
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
    const eligible = pending(), unavailable = missing();
    if (!eligible.length) throw new Error('There are no pending scheduled Attendance committees for this village.');
    if (unavailable.length) throw new Error(`Ask your PC to schedule these committees or ask Admin to restore recycled records: ${unavailable.map(c => c.name).join(', ')}.`);
    const sharedReason = $('#shared-date-reason').value.trim();
    const sharedRemarks = $('#village-notes').value.trim();
    const reasonRequired = eligible.some(item => date.value !== item.plan.assigned_date);
    if (reasonRequired && !sharedReason) throw new Error('Enter one Early/Postponed reason for the village visit.');
    const entries = eligible.map(item => {
      const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
      const people = selectedCounts(row);
      if (people.unknown) throw new Error(`Gender is missing in Master Data for a selected member of ${item.name}. Please ask Admin/PC to correct it.`);
      const countInput = $(`[data-new-count="${item.id}"]`);
      const newMembers = Number(countInput?.value || 0);
      if (!Number.isInteger(newMembers) || newMembers < 0) throw new Error(`Enter a valid new members count for ${item.name}.`);
      return {
        committee_id: item.id, counts_mode: 'selected_members',
        male_count: people.male, female_count: people.female,
        new_members_count: newMembers, visit_member_ids: people.ids,
        reason: date.value !== item.plan.assigned_date ? sharedReason : '', remarks: sharedRemarks,
      };
    });
    if (!photo) throw new Error('Attach one evidence photo for the village.');
    if (!validCoords(coords)) { window.MVLocation?.capture(true); throw new Error('Current device location is required. Enable location and try again.'); }
    if (Date.now() - coords.capturedAt > 2 * 60 * 1000) { window.MVLocation?.capture(true); throw new Error('GPS fix is older than 2 minutes. It is refreshing; submit again once captured.'); }
    const data = new FormData();
    data.append('client_submission_id', submissionId);
    data.append('village_id', village.value);
    data.append('visit_date', date.value);
    data.append('latitude', coords.latitude.toFixed(6));
    data.append('longitude', coords.longitude.toFixed(6));
    data.append('remarks', sharedRemarks);
    data.append('committees', JSON.stringify(entries));
    data.append('photo', photo, photo.name);
    return data;
  }
  function reset() {
    submissionId = crypto.randomUUID(); form.reset(); date.value = root.dataset.today;
    village.value = ''; allCommittees = []; busy = false; setSubmitState();
    planNote.classList.remove('form-alert'); planNote.classList.remove('hidden');
    $('#summary-committees').textContent = '0 committees';
    $('#summary-pending').textContent = '0 to record';
    $('#summary-submitted').textContent = '0 submitted';
    cards.innerHTML = '<div class="empty-state">Select a village to begin.</div>';
    planNote.textContent = 'Select a village to begin.';
    $('#new-members-entries').innerHTML = ''; $('#shared-date-reason-wrap').classList.add('hidden');
    $('#village-male').textContent = '0'; $('#village-female').textContent = '0'; $('#village-total').textContent = '0';
    $('#committee-progress').textContent = '0 of 0 committees'; $('#committee-progress-bar').style.width = '0%';
    photo = null; preview.classList.add('hidden');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null; status.textContent = 'Select a village';
  }
  form.addEventListener('submit', async event => {
    event.preventDefault(); clearError();
    if (!village.value || !date.value) return showError('Choose a village and visit date.');
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
