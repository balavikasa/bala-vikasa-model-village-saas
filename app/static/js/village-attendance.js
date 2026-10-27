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
  send.disabled = true;
  const locationLabel = $('#location-label');
  const locationDetail = $('#location-detail');
  const locationButton = $('#retry-location');
  const preview = $('#photo-preview');
  const month = root.dataset.currentMonth;
  const params = new URLSearchParams(location.search);
  let submissionId = crypto.randomUUID();
  let selected = [];
  let allCommittees = [];
  let photo = null;
  let previewUrl = null;
  let requestId = 0;
  let coords = null;

  function showError(text) { error.textContent = text; error.classList.remove('hidden'); }
  function clearError() { error.textContent = ''; error.classList.add('hidden'); }
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
      locationLabel.textContent = 'Current location captured';
      locationDetail.textContent = `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)} · ±${Math.round(point.accuracy || 0)} m`;
      locationButton.textContent = 'Refresh GPS';
    } else {
      coords = null;
      locationLabel.textContent = 'Location required';
      locationDetail.textContent = point?.message || 'Enable Location Services and allow this site access in your device/browser settings.';
      locationButton.textContent = 'Enable location';
    }
  };
  window.addEventListener('mv:location', locationUpdate);
  locationButton.addEventListener('click', () => window.MVLocation?.capture(true));
  if (window.MVLocation?.last) locationUpdate({ detail: window.MVLocation.last });
  else window.MVLocation?.capture();

  const value = (row, selector) => row.querySelector(selector)?.value || '';
  const sum = (row) => {
    const male = Number(value(row, '[data-male]') || 0), female = Number(value(row, '[data-female]') || 0);
    row.querySelector('[data-live-total]').textContent = String(male + female);
  };
  function render() {
    if (!allCommittees.length) {
      cards.innerHTML = '<div class="empty-state">No committees in this village.</div>';
      return;
    }
    const eligible = allCommittees.filter(item => item.plan && !item.plan.attendance_entry_id && !item.plan.has_recycled_attendance);
    const missing = allCommittees.filter(item => !item.plan || item.plan.has_recycled_attendance);
    const completed = allCommittees.filter(item => item.plan?.attendance_entry_id);
    const hasUnscheduled = missing.length > 0;
    send.disabled = hasUnscheduled || eligible.length === 0;
    planNote.classList.toggle('form-alert', hasUnscheduled);
    planNote.textContent = hasUnscheduled
      ? `${missing.length} committee(s) have no executable Attendance plan. Your PC must assign their dates before this village can be submitted. ${eligible.length} scheduled, ${completed.length} completed.`
      : `${allCommittees.length} committees · ${eligible.length} pending · ${completed.length} completed · one village submission`;
    status.textContent = hasUnscheduled ? 'PC scheduling required' : eligible.length ? 'Ready for one village visit' : 'No pending attendance';
    cards.innerHTML = allCommittees.map((item, idx) => {
      const plan = item.plan;
      const done = Boolean(plan?.attendance_entry_id);
      const recycled = Boolean(plan?.has_recycled_attendance);
      const ready = Boolean(plan) && !done && !recycled;
      return `<details class="mv-committee-card" ${ready && idx === 0 ? 'open' : ''} data-committee-id="${item.id}" data-ready="${ready}">
        <summary><span class="mv-committee-number">${idx + 1}</span><span class="mv-committee-name"><strong>${esc(item.name)}</strong><small>${ready ? `Assigned ${esc(plan.assigned_date)} · ${esc(plan.status)}` : done ? 'Attendance already submitted' : recycled ? 'Recycle Bin: ask Admin to restore' : 'PC assignment required'}</small></span><span class="badge ${ready ? 'neutral' : 'warning'}">${ready ? 'Enter' : done ? 'Done' : recycled ? 'Restore' : 'Unscheduled'}</span></summary>
        ${ready ? `<div class="mv-committee-details">
          <div class="attendance-count-grid">
            <label class="attendance-count-card"><span>Male *</span><div><input data-male type="number" min="0" inputmode="numeric" required placeholder="0"><strong>/ ${item.male_master || 0}</strong></div><small>Live / master</small></label>
            <label class="attendance-count-card"><span>Female *</span><div><input data-female type="number" min="0" inputmode="numeric" required placeholder="0"><strong>/ ${item.female_master || 0}</strong></div><small>Live / master</small></label>
            <div class="attendance-count-card total"><span>Total</span><div><output data-live-total>0</output><strong>/ ${item.member_total || 0}</strong></div><small>Live / master</small></div>
          </div>
          <div class="form-grid"><label class="field"><span>New members</span><input data-new type="number" min="0" inputmode="numeric" value="0"></label><label class="field"><span data-computed-status>Visit status</span><small>Status is based on visit date vs assigned date.</small></label></div>
          <fieldset class="mv-member-field"><legend>Visit designation / Member names</legend><small>Select the people who attended the visit.</small><div data-members class="mv-member-list"><small>Loading members…</small></div></fieldset>
          <label class="field hidden" data-reason-wrap><span>Early / Postponed reason *</span><textarea data-reason rows="2" placeholder="Explain date difference"></textarea></label>
          <label class="field"><span>Committee remarks (optional)</span><textarea data-remarks rows="2"></textarea></label>
        </div>` : ''}
      </details>`;
    }).join('');
    cards.querySelectorAll('input[data-male],input[data-female]').forEach(el => el.addEventListener('input', () => sum(el.closest('[data-committee-id]'))));
    dateStatus();
  }
  function dateStatus() {
    for (const item of allCommittees) {
      const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
      if (!item.plan || !row || row.dataset.ready !== 'true') continue;
      const assigned = item.plan.assigned_date;
      const state = date.value < assigned ? 'Early' : date.value > assigned ? 'Postponed' : 'On-time';
      row.querySelector('[data-computed-status]').textContent = `Status: ${state}`;
      const reason = row.querySelector('[data-reason-wrap]');
      reason.classList.toggle('hidden', state === 'On-time');
      reason.querySelector('textarea').required = state !== 'On-time';
    }
  }
  date.addEventListener('change', dateStatus);
  async function loadVillage(id) {
    const stamp = ++requestId;
    cards.innerHTML = '<div class="empty-state">Loading committees and action plans…</div>';
    allCommittees = [];
    send.disabled = true;
    if (!id) { cards.innerHTML = '<div class="empty-state">Select village.</div>'; return; }
    try {
      const base = await get(`/api/v1/villages/${encodeURIComponent(id)}/committees`);
      const committees = base.items || [];
      const batches = await Promise.all(committees.map(async (committee) => {
        const [plans, members] = await Promise.all([
          get(`/api/v1/committees/${committee.id}/action-plans?type=Attendance&executable=1&month=${encodeURIComponent(month)}`),
          get(`/api/v1/committees/${committee.id}/members`),
        ]);
        const plan = (plans.items || []).find(p => !p.attendance_entry_id) || (plans.items || [])[0] || null;
        return { ...committee, plan, members: members.items || [] };
      }));
      if (stamp !== requestId) return;
      allCommittees = batches;
      render();
      for (const item of allCommittees) {
        const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
        if (!row || row.dataset.ready !== 'true') continue;
        const byRole = new Map();
        for (const member of item.members) {
          const key = member.designation || 'Member';
          if (!byRole.has(key)) byRole.set(key, []);
          byRole.get(key).push(member);
        }
        row.querySelector('[data-members]').innerHTML = [...byRole.entries()].map(([role, members]) => `
          <div class="mv-members-group"><strong>${esc(role)}</strong>${members.map(m => `<label><input type="checkbox" value="${m.id}" data-visit-member><span>${esc(m.name)}${m.gender ? ` · ${esc(m.gender)}` : ''}</span></label>`).join('')}</div>`).join('') || '<small>No active members in master data.</small>';
      }
    } catch (e) { if (stamp === requestId) showError(e.message); }
  }
  village.addEventListener('change', () => { clearError(); loadVillage(village.value); });
  (async () => {
    try {
      const data = await get('/api/v1/villages');
      village.innerHTML = '<option value="">Select village</option>' + (data.items || []).map(v => `<option value="${v.id}">${esc(v.name)}</option>`).join('');
      const selectedVillage = params.get('village');
      if (selectedVillage && [...village.options].some(opt => opt.value === selectedVillage)) {
        village.value = selectedVillage;
        loadVillage(village.value);
      }
    } catch (e) { showError(e.message); }
  })();

  async function compress(file) {
    if (!file.type.startsWith('image/')) throw new Error('Select a supported image.');
    if (file.size > 12 * 1024 * 1024) throw new Error('Image must be smaller than 12 MB.');
    const bitmap = 'createImageBitmap' in window ? await createImageBitmap(file) : await new Promise((resolve, reject) => {
      const img = new Image(); const url = URL.createObjectURL(file);
      img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
      img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Unable to read image.')); };
      img.src = url;
    });
    const ratio = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * ratio);
    canvas.height = Math.round(bitmap.height * ratio);
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#f4f6f5'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close?.();
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
      previewUrl = URL.createObjectURL(photo);
      preview.querySelector('img').src = previewUrl;
      preview.classList.remove('hidden');
      status.textContent = `${Math.round(photo.size / 1024)} KB photo ready`;
    } catch (e) { showError(e.message); }
  });
  $('#remove-photo').addEventListener('click', () => {
    photo = null; preview.classList.add('hidden');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    for (const input of Object.values(inputs)) input.value = '';
  });
  function body() {
    const pending = allCommittees.filter(i => i.plan && !i.plan.attendance_entry_id && !i.plan.has_recycled_attendance);
    if (!pending.length) throw new Error('There are no pending scheduled Attendance committees for this village.');
    const unscheduled = allCommittees.filter(i => !i.plan || i.plan.has_recycled_attendance);
    if (unscheduled.length) throw new Error(`Ask your PC to schedule missing Attendance plans or ask Admin to restore recycled records for: ${unscheduled.map(c => c.name).join(', ')}.`);
    const entries = pending.map(item => {
      const row = cards.querySelector(`[data-committee-id="${item.id}"]`);
      const read = (selector) => row.querySelector(selector)?.value || '';
      if (read('[data-male]') === '' || read('[data-female]') === '') throw new Error(`Enter male and female attendance for ${item.name}.`);
      const state = date.value < item.plan.assigned_date ? 'Early' : date.value > item.plan.assigned_date ? 'Postponed' : 'On-time';
      if (state !== 'On-time' && !read('[data-reason]').trim()) throw new Error(`Enter ${state} reason for ${item.name}.`);
      const checked = [...row.querySelectorAll('[data-visit-member]:checked')].map(el => Number(el.value));
      return { committee_id: item.id, male_count: read('[data-male]'), female_count: read('[data-female]'), new_members_count: read('[data-new]') || '0', visit_member_ids: checked, reason: read('[data-reason]'), remarks: read('[data-remarks]') };
    });
    if (!photo) throw new Error('One evidence photo is required.');
    if (!validCoords(coords)) { window.MVLocation?.capture(true); throw new Error('Current device location is required. Enable location and try again.'); }
    if (Date.now() - coords.capturedAt > 2 * 60 * 1000) { window.MVLocation?.capture(true); throw new Error('Your GPS fix is older than 2 minutes. Refreshing; please submit again after capture.'); }
    const data = new FormData();
    data.append('client_submission_id', submissionId);
    data.append('village_id', village.value);
    data.append('visit_date', date.value);
    data.append('latitude', coords.latitude.toFixed(6));
    data.append('longitude', coords.longitude.toFixed(6));
    data.append('remarks', $('#village-notes').value || '');
    data.append('committees', JSON.stringify(entries));
    data.append('photo', photo, photo.name);
    return data;
  }
  function reset() {
    submissionId = crypto.randomUUID();
    form.reset(); date.value = root.dataset.today;
    village.value = '';
    allCommittees = [];
    send.disabled = true;
    planNote.classList.remove('form-alert');
    cards.innerHTML = '<div class="empty-state">Select a village to begin.</div>';
    planNote.textContent = 'Choose a village to load all its committees.';
    photo = null; preview.classList.add('hidden');
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    status.textContent = 'Ready';
  }
  form.addEventListener('submit', async (event) => {
    event.preventDefault(); clearError();
    if (!village.value || !date.value) return showError('Choose a village and visit date.');
    let data;
    try { data = body(); } catch (e) { return showError(e.message); }
    send.disabled = true; status.textContent = navigator.onLine ? 'Submitting village visit…' : 'Saving visit offline…';
    try {
      if (!navigator.onLine) {
        if (!window.MVQueue) throw new Error('Offline queue unavailable on this device.');
        await window.MVQueue.enqueue({ id: submissionId, userId: window.MV.userId, url: '/api/v1/attendance/village', method: 'POST', formData: data, entryType: 'attendance' });
        window.dispatchEvent(new CustomEvent('mv:queued'));
        window.MV.toast('Entire village attendance saved offline for sync.', 'success');
      } else {
        const res = await window.MV.api('/api/v1/attendance/village', { method: 'POST', body: data });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Submission failed.');
        if (result.queued) window.MV.toast('Entire village attendance queued for sync.', 'success');
        else window.MV.toast(`${result.committee_count} committees submitted in one village visit.`, 'success');
      }
      reset();
    } catch (e) { showError(e.message); status.textContent = 'Not submitted'; }
    finally { send.disabled = false; }
  });
})();
