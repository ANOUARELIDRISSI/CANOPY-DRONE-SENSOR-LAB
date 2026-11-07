import { FieldScene, palette } from './scene.js?v=vision1';

const $ = id => document.getElementById(id);
const settingIds = ['scenario', 'runs', 'seed', 'speed', 'drones', 'environment', 'field-width', 'sensors', 'vegetation', 'steps'];
let current = null, shownSession = null, previewing = false, previewSerial = 0;
const observedKeys = new Map();
function showError(text) { $('error').textContent = text; $('error').hidden = !text; }
let field;
try { field = new FieldScene($('scene'), text => $('model-status').textContent = text, showError); }
catch (error) { showError('3D rendering is unavailable: ' + error.message); throw error; }

function settings() {
  return { scenario: $('scenario').value, runs: Number($('runs').value), seed: Number($('seed').value),
    steps: Number($('steps').value), speed: Number($('speed').value), drones: Number($('drones').value),
    environment: $('environment').value, field_width: Number($('field-width').value),
    sensors: Number($('sensors').value), vegetation: Number($('vegetation').value) };
}
function syncSettings(state) {
  const values = {scenario: state.scenario_mode, runs: state.runs, seed: state.seed, steps: state.steps,
    speed: state.speed, drones: state.drone_count, environment: state.environment.preset,
    'field-width': state.environment.width_m, sensors: state.environment.sensor_count,
    vegetation: state.environment.vegetation};
  for (const [id, value] of Object.entries(values)) $(id).value = value;
}
const number = value => value == null ? '—' : Number(value).toFixed(1);
function cameraLabel() {
  $('follow').setAttribute('aria-pressed', String(field.cameraControl.following));
  $('camera-mode').textContent = field.cameraControl.following
    ? `Following drone ${field.selected + 1} · drag / zoom stays yours`
    : 'Free orbit · wheel/pinch to zoom';
}
function applyState(state, isPreview = false) {
  if (previewing && !isPreview && state.status !== 'running') return;
  if (state.status === 'running') { previewing = false; previewSerial++; }
  const newSession = state.session !== shownSession;
  if (newSession && state.session) { shownSession = state.session; syncSettings(state); observedKeys.clear(); }
  current = state;
  if (state.error) showError(state.error);
  const changed = field.configure(state.environment, state.stations, state.route, state.drone_count, state.seed);
  if (changed) {
    $('follow-select').replaceChildren(...state.drones.map(d => new Option(`Drone ${d.id + 1}`, String(d.id))));
    $('follow-select').value = String(field.selected);
    observedKeys.clear();
  }
  field.update(state, changed || newSession);
  cameraLabel();
  const running = state.status === 'running', preview = !state.session;
  settingIds.forEach(id => $(id).disabled = running);
  $('preview').disabled = running; $('training-preset').disabled = running;
  $('start').disabled = running; $('stop').disabled = !running;
  $('download').classList.toggle('disabled', preview);
  $('flight-state').textContent = state.status.toUpperCase();
  $('tour-label').textContent = `${state.drone_count} drone${state.drone_count > 1 ? 's' : ''} · tour ${state.run_id + 1} / ${state.runs}`;
  $('position-label').textContent = `${state.environment.preset.toUpperCase()} · ${state.scenario.toUpperCase()} · ${state.stations.length} stations`;
  $('field-size').textContent = `/ ${state.environment.width_m} × ${Math.round(state.environment.height_m)} m`;
  $('scene').setAttribute('aria-label', `Interactive 3D ${state.environment.preset} with ${state.drone_count} drones and ${state.stations.length} sensors`);
  $('rows').textContent = state.counts.received.toLocaleString();
  $('clock').textContent = `${Math.floor(state.elapsed_s / 60)}:${String(Math.floor(state.elapsed_s % 60)).padStart(2, '0')}`;
  $('progress').textContent = preview ? 'Preview · start to collect' : `${Math.round(state.elapsed_s / state.total_s * 100)}% · ${state.runs} tours per drone`;
  $('progress-bar').style.width = `${state.elapsed_s / state.total_s * 100}%`;
  $('session').textContent = preview ? 'A new dataset is created when collection starts.' : `artifacts/live/${state.session}/readings.csv`;
  const fresh = state.stations.filter(s => s.age_s != null && s.age_s <= 30);
  const alarms = state.stations.filter(s => s.decision === 'ALARM');
  const uncertain = state.stations.some(s => s.decision === 'WARNING');
  $('fresh').textContent = fresh.length; $('alarms').textContent = alarms.length;
  $('decision').textContent = preview ? 'AWAITING DATA' : alarms.length ? 'ALARM' : uncertain ? 'WARNING' : 'NO ALARM';
  document.querySelector('.decision-panel').className = `panel decision-panel ${alarms.length ? 'alarm' : uncertain ? '' : 'clear'}`;
  $('reason').textContent = preview ? 'Preview your environment, then start the fleet.' : alarms.length
    ? 'Fire-like measurements at fresh stations. Inspect the highlighted readings.' : uncertain
    ? 'Some stations are unvisited, stale or missing a measurement. Continue collection.'
    : 'Fresh complete measurements are below the learned alarm cutoff.';
  $('link-stats').innerHTML = Object.entries(state.links).map(([name, counts]) => `<div class="link-row"><b style="color:#${palette[name].toString(16)}">${name === 'proprietary' ? 'Custom' : name === 'wifi' ? 'WiFi' : 'Bluetooth'}</b><small>${counts.received.toLocaleString()} received · ${counts.lost} lost</small></div>`).join('');
  $('readings').innerHTML = state.stations.map(s => {
    const r = s.reading, key = r ? `${state.session}:${r.run_id}:${r.sequence}:${r.drone_id}` : null;
    if (r && observedKeys.get(s.id) !== key) { observedKeys.set(s.id, key); if (running) field.flash(s.id, r.drone_id); }
    return `<tr><td>S${String(s.id).padStart(2, '0')}</td><td>${r ? 'Drone ' + (r.drone_id + 1) : '—'}</td><td>${s.protocol}</td><td>${number(r?.temperature_c)}</td><td>${number(r?.humidity_pct)}</td><td>${number(r?.smoke_ppm)}</td><td>${number(r?.co_ppm)}</td><td>${s.age_s == null ? 'unvisited' : number(s.age_s) + ' s'}</td><td><span class="status ${s.decision}">${s.decision}</span></td></tr>`;
  }).join('');
}
const events = new EventSource('/api/events');
events.onmessage = event => {
  $('connection').textContent = '● STREAM CONNECTED'; $('connection').classList.remove('offline');
  applyState(JSON.parse(event.data));
};
events.onerror = () => { $('connection').textContent = 'RECONNECTING…'; $('connection').classList.add('offline'); };
async function command(url, body = {}) {
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the setting ranges.');
  return result;
}
async function preview() {
  if (current?.status === 'running') return;
  const serial = ++previewSerial; previewing = true;
  try { const result = await command('/api/preview', settings()); if (serial === previewSerial) { showError(''); applyState(result, true); } }
  catch (error) { if (serial === previewSerial) showError(error.message); }
}
$('preview').onclick = preview;
for (const id of settingIds) $(id).addEventListener('change', preview);
$('start').onclick = async () => {
  showError(''); $('start').disabled = true; previewSerial++;
  try { if ($('random-seed').checked) $('seed').value = crypto.getRandomValues(new Uint32Array(1))[0]; await command('/api/start', settings()); previewing = false; observedKeys.clear(); }
  catch (error) { showError(error.message); $('start').disabled = false; }
};
$('stop').onclick = async () => { try { await command('/api/stop'); } catch (error) { showError(error.message); } };
$('training-preset').onclick = () => { $('scenario').value = 'mixed'; $('runs').value = '15'; $('speed').value = '64'; preview(); };
$('follow').onclick = () => { field.follow(); cameraLabel(); };
$('follow-select').onchange = () => { field.selected = Number($('follow-select').value); cameraLabel(); };
$('overview').onclick = () => { field.overview(); cameraLabel(); };
$('free').onclick = () => { field.cameraControl.following = false; field.cameraControl.controls.enablePan = true; cameraLabel(); };
$('zoom-in').onclick = () => field.cameraControl.zoom(.8);
$('zoom-out').onclick = () => field.cameraControl.zoom(1.25);
$('fullscreen').onclick = async () => {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.querySelector('.scene-card').requestFullscreen(); }
  catch (error) { showError('Full screen is unavailable in this browser. You can still orbit and zoom in the scene.'); }
};
document.addEventListener('fullscreenchange', () => $('fullscreen').textContent = document.fullscreenElement ? 'Exit full screen' : 'Full screen');

let cameraWindow = null;
let cameraOrigin;
$('open-camera').onclick = async () => {
  cameraOrigin = location.protocol + '//' + location.hostname + ':' + (current?.camera_port || 8766);
  const dialog = $('camera-panel');
  dialog.showModal();
  $('camera-help').textContent = 'Connecting to the CPU camera…';
  try {
    await fetch(cameraOrigin + '/health', {mode:'no-cors', signal:AbortSignal.timeout(4000)});
    if (!dialog.open) return;
    $('camera-frame').src = cameraOrigin + '/?viewer=' + encodeURIComponent(location.origin) + (current?.session ? '&source=drone' : '');
    cameraWindow = $('camera-frame').contentWindow;
    $('camera-help').textContent = 'Select a source below to inspect frames.';
  } catch {
    $('camera-help').textContent = 'Camera is offline. Run docker compose --profile camera up -d camera, then reopen this view.';
  }
};
$('close-camera').onclick = () => $('camera-panel').close();
$('camera-panel').onclose = () => { cameraWindow = null; $('camera-frame').src = 'about:blank'; };
window.addEventListener('message', async event => {
  if (!cameraWindow || event.source !== cameraWindow || event.origin !== cameraOrigin ||
      event.data?.type !== 'drone-frame') return;
  const id = event.data.id;
  try {
    if (!current?.session) throw new Error('Start a collection to use the drone camera.');
    const drone = field.selected, run = current.run_id, time = current.time_s;
    const blob = await field.captureDroneFrame();
    cameraWindow.postMessage({id, blob, drone, run, time}, cameraOrigin);
  } catch (error) { cameraWindow.postMessage({id, error:error.message}, cameraOrigin); }
});
