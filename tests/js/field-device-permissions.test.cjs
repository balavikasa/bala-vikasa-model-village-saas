// Run the production field controller against browser/device boundary doubles.
// No network or third-party test dependencies are required.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const { File } = require('node:buffer');
const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'app/static/js/field.js'), 'utf8');
const template = fs.readFileSync(path.join(root, 'app/templates/field.html'), 'utf8');

class Element {
  constructor() {
    this.value = ''; this.textContent = ''; this.dataset = {}; this.files = [];
    this.disabled = false; this.events = {}; this.attributes = {}; this.clicked = 0;
    const classes = new Set(['hidden']);
    this.classList = {
      add: (s) => classes.add(s), remove: (s) => classes.delete(s),
      contains: (s) => classes.has(s),
      toggle: (s, yes) => yes ? classes.add(s) : classes.delete(s),
    };
  }
  addEventListener(name, callback) { (this.events[name] ||= []).push(callback); }
  async fire(name, target = this) {
    for (const callback of this.events[name] || []) await callback({ target, preventDefault() {} });
  }
  click() { this.clicked++; return this.fire('click'); }
  focus() { this.focused = true; }
  closest() { return this; }
  querySelectorAll() { return []; }
  querySelector() { return this.image; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; if (name === 'src') delete this.src; }
  reportValidity() { return true; }
}

function setup({ offline = false, secure = true, supported = true, entryType = 'specials' } = {}) {
  const elements = new Map([...template.matchAll(/id="([\w-]+)"/g)].map(m => [m[1], new Element()]));
  const get = id => elements.get(id);
  const pageRoot = new Element();
  pageRoot.dataset = { entryType, today: '2026-09-09', currentMonth: '2026-09' };
  const buttons = [...template.matchAll(/data-photo-source="([\w-]+)"/g)].map(m => {
    const e = new Element(); e.dataset.photoSource = m[1]; return e;
  });
  get('photo-preview').image = new Element();
  get('committee-select').selectedOptions = [];
  get('entry-form').reset = () => { for (const e of elements.values()) e.value = ''; };
  const requests = [], queued = [], revoked = [];
  let bitmap = async () => ({ width: 40, height: 30, close() {} });
  const navigator = { onLine: !offline };
  if (supported) navigator.geolocation = { getCurrentPosition: (success, error, options) => requests.push({ success, error, options }) };
  class BrowserFormData extends FormData {
    constructor() {
      super();
      for (const name of ['latitude', 'longitude']) this.append(name, get(name).value);
      this.append('client_submission_id', get('client-submission-id').value);
      this.append('action_plan_id', get('action-plan-select').value);
    }
  }
  const window = {
    isSecureContext: secure, location: { search: '', href: 'https://example.test/field/specials' },
    MV: { userId: '7', escapeHtml: String, api: async () => ({ ok: true, json: async () => ({ items: [] }) }), toast() {} },
    MVQueue: { enqueue: async value => queued.push(value) },
    dispatchEvent() {}, addEventListener() {}, createImageBitmap: (...args) => bitmap(...args),
  };
  const document = {
    getElementById: get,
    querySelector: selector => selector === '.field-page' ? pageRoot : selector === '[data-photo-source]' ? buttons[0] : null,
    querySelectorAll: selector => selector === '[data-photo-source]' ? buttons : [],
    createElement: () => ({
      getContext: () => ({ fillRect() {}, drawImage() {} }),
      toBlob: callback => callback(new Blob(['compressed'], { type: 'image/webp' })),
    }),
  };
  class BrowserURL extends URL {}
  BrowserURL.createObjectURL = () => 'blob:evidence';
  BrowserURL.revokeObjectURL = value => revoked.push(value);
  vm.runInNewContext(source, {
    window, document, navigator, crypto: webcrypto, URLSearchParams, URL: BrowserURL,
    File, Blob, FormData: BrowserFormData, CustomEvent: class {},
    createImageBitmap: (...args) => bitmap(...args), console, setTimeout, clearTimeout,
  });
  return { get, buttons, requests, queued, revoked, window, setBitmap: fn => { bitmap = fn; } };
}
const validPosition = { coords: { latitude: 17.385044, longitude: 78.486671, accuracy: 12 }, timestamp: Date.now() };
const photo = () => new File(['image'], 'evidence.jpg', { type: 'image/jpeg' });
const choose = async (app, id, file = photo()) => {
  assert.ok(app.get(id), `${id} must be available`);
  app.get(id).files = [file];
  await app.get(id).fire('change');
};

// Removing the explicit user-action gate would prompt on every page open.
test('location waits for the DA to request access, including offline', async () => {
  for (const offline of [false, true]) {
    const app = setup({ offline });
    assert.equal(app.requests.length, 0);
    await app.get('retry-location').click();
    assert.equal(app.requests.length, 1);
    app.requests[0].success(validPosition);
    assert.equal(app.get('latitude').value, '17.385044');
    assert.equal(app.get('longitude').value, '78.486671');
    assert.match(app.get('location-label').textContent, /captured/i);
  }
});

test('duplicate requests are suppressed while GPS is pending', async () => {
  const app = setup({ offline: true });
  await app.get('retry-location').click();
  await app.get('retry-location').click();
  assert.equal(app.requests.length, 1);
  assert.equal(app.get('retry-location').disabled, true);
  assert.equal(app.requests[0].options.maximumAge, 0);
  assert.equal(app.requests[0].options.enableHighAccuracy, true);
  app.requests[0].error({ code: 3 });
  assert.equal(app.get('retry-location').disabled, false);
  assert.match(app.get('location-detail').textContent, /open area/i);
});

test('denied permission explains how to enable it and a retry can recover', async () => {
  const app = setup();
  await app.get('retry-location').click();
  app.requests.at(-1).error({ code: 1 });
  assert.equal(app.get('latitude').value, '');
  assert.match(app.get('location-detail').textContent, /settings/i);
  await app.get('retry-location').click();
  app.requests.at(-1).success(validPosition);
  assert.equal(app.get('latitude').value, '17.385044');
});

test('GPS unavailable explains phone location settings', async () => {
  const app = setup({ offline: true });
  await app.get('retry-location').click();
  app.requests.at(-1).error({ code: 2 });
  assert.match(app.get('location-detail').textContent, /location.*settings|settings.*location/i);
  assert.equal(app.get('longitude').value, '');
});

test('insecure origin cannot start a location request', async () => {
  const app = setup({ secure: false });
  await app.get('retry-location').click();
  assert.equal(app.requests.length, 0);
  assert.match(app.get('location-detail').textContent, /HTTPS/i);
});

test('unsupported geolocation and invalid coordinates stay blocked', async () => {
  const unsupported = setup({ supported: false });
  await unsupported.get('retry-location').click();
  assert.match(unsupported.get('location-label').textContent, /unavailable/i);
  for (const latitude of [NaN, 100]) {
    const app = setup();
    await app.get('retry-location').click();
    app.requests.at(-1).success({ coords: { latitude, longitude: 78, accuracy: 1 } });
    assert.equal(app.get('latitude').value, '');
  }
});

test('each evidence source opens its own picker without network access', async () => {
  const app = setup({ offline: true });
  assert.equal(app.buttons.length, 3);
  for (const button of app.buttons) {
    await button.click();
    assert.equal(app.get(button.dataset.photoSource).clicked, 1);
  }
});

for (const id of ['photo-input', 'album-input', 'file-input']) {
  test(`${id} compresses and includes the selected image and GPS in the offline entry`, async () => {
    const app = setup({ offline: true });
    await choose(app, id);
    assert.equal(app.get('photo-preview').classList.contains('hidden'), false);
    await app.get('retry-location').click();
    app.requests.at(-1).success(validPosition);
    app.get('action-plan-select').value = '1';
    await app.get('entry-form').fire('submit');
    assert.equal(app.queued.length, 1);
    const entry = app.queued[0];
    assert.equal(entry.userId, '7');
    assert.equal(entry.formData.get('latitude'), '17.385044');
    assert.equal(entry.formData.get('longitude'), '78.486671');
    assert.equal(entry.formData.get('photo').type, 'image/webp');
    assert.equal(entry.formData.get('client_submission_id'), entry.id);
    assert.equal(app.get('latitude').value, '');
    assert.equal(app.requests.length, 1, 'Reset must not trigger a new permission request');
    assert.equal(app.get('photo-preview').image.src, undefined);
  });
}

test('removing a photo during compression cannot resurrect it', async () => {
  const app = setup();
  let finish;
  app.setBitmap(() => new Promise(resolve => { finish = resolve; }));
  const selection = choose(app, 'photo-input');
  await app.get('remove-photo').click();
  finish({ width: 20, height: 20, close() {} });
  await selection;
  assert.equal(app.get('photo-preview').classList.contains('hidden'), true);
});

test('invalid replacement clears the previous preview and blocks submission', async () => {
  const app = setup({ offline: true });
  await choose(app, 'photo-input');
  await choose(app, 'photo-input', new File(['text'], 'wrong.txt', { type: 'text/plain' }));
  assert.equal(app.get('photo-preview').classList.contains('hidden'), true);
  app.get('action-plan-select').value = '1';
  await app.get('entry-form').fire('submit');
  assert.equal(app.queued.length, 0);
  assert.match(app.get('entry-error').textContent, /photo.*required/i);
});

test('newest photo wins when conversions finish out of order', async () => {
  const app = setup({ offline: true });
  let failFirst;
  app.setBitmap(() => new Promise((_, reject) => { failFirst = reject; }));
  const first = choose(app, 'photo-input');
  app.setBitmap(async () => ({ width: 20, height: 20, close() {} }));
  await choose(app, 'photo-input');
  failFirst(new Error('Old image unreadable'));
  await first;
  assert.equal(app.get('photo-preview').classList.contains('hidden'), false);
  assert.doesNotMatch(app.get('entry-error').textContent, /Old image/);
});

test('a location refresh pending across submission cannot populate the next entry', async () => {
  const app = setup();
  await choose(app, 'photo-input');
  await app.get('retry-location').click();
  app.requests.at(-1).success(validPosition);
  app.get('action-plan-select').value = '1';
  let finishPost;
  app.window.MV.api = () => new Promise(resolve => { finishPost = resolve; });
  const submission = app.get('entry-form').fire('submit');
  await app.get('retry-location').click();
  const obsolete = app.requests.at(-1);
  finishPost({ ok: true, json: async () => ({}) });
  await submission;
  assert.equal(app.get('retry-location').disabled, false);
  obsolete.success(validPosition);
  assert.equal(app.get('latitude').value, '');
  await app.get('retry-location').click();
  app.requests.at(-1).success(validPosition);
  obsolete.error({ code: 1 });
  assert.equal(app.get('latitude').value, '17.385044');
});

test('Attendance keeps the member requirement and accepts album evidence offline', async () => {
  const app = setup({ offline: true, entryType: 'attendance' });
  app.window.MV.api = async url => ({ ok: true, json: async () => ({ items: url.endsWith('/members')
    ? [{ id: 11, name: 'Test Member', designation: 'President', gender: 'Male' }]
    : [{ id: 1, assigned_date: '2026-09-09', status: 'Pending', plan_month: '2026-09-01' }] }) });
  app.get('committee-select').value = '1';
  await app.get('committee-select').fire('change');
  app.get('action-plan-select').value = '1';
  await choose(app, 'album-input');
  await app.get('retry-location').click();
  app.requests.at(-1).success(validPosition);
  await app.get('entry-form').fire('submit');
  assert.equal(app.queued.length, 0);
  assert.match(app.get('entry-error').textContent, /designation/i);
  const designation = new Element();
  designation.dataset.designation = 'President';
  await app.get('designation-grid').fire('click', designation);
  assert.equal(app.get('visit-member-ids').value, '[11]');
  await app.get('entry-form').fire('submit');
  assert.equal(app.queued.length, 1);
  assert.equal(app.queued[0].url, '/api/v1/attendance');
  assert.equal(app.queued[0].formData.get('photo').type, 'image/webp');
});
