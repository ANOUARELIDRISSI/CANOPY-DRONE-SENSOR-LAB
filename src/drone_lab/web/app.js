import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { ColladaLoader } from './vendor/loaders/ColladaLoader.js';

const $ = id => document.getElementById(id);
const palette = { bluetooth: 0x51ccff, wifi: 0xffbe6b, proprietary: 0xb394ff };
const scene = new THREE.Scene();
scene.background = new THREE.Color('#17291f');
scene.fog = new THREE.Fog('#17291f', 350, 800);
const camera = new THREE.PerspectiveCamera(43, 1, 0.1, 1000);
camera.position.set(285, 235, 310);
let renderer;
try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
catch (error) { $('error').hidden = false; $('error').textContent = 'WebGL is unavailable in this browser. CSV collection remains available through the API.'; throw error; }
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
$('scene').appendChild(renderer.domElement);
const orbit = new OrbitControls(camera, renderer.domElement);
orbit.target.set(110, 0, 80); orbit.enableDamping = true; orbit.maxPolarAngle = Math.PI * .47;
orbit.minDistance = 20; orbit.maxDistance = 500;
scene.add(new THREE.HemisphereLight(0xd6f0e5, 0x384d25, 2.3));
const sun = new THREE.DirectionalLight(0xffe4b3, 3.2);
sun.position.set(80, 160, -40); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -260;
sun.shadow.camera.right = 260; sun.shadow.camera.top = 260; sun.shadow.camera.bottom = -260;
sun.shadow.camera.far = 500; sun.shadow.bias = -.001; scene.add(sun);
const ground = new THREE.Mesh(new THREE.BoxGeometry(260, 3, 200),
  new THREE.MeshStandardMaterial({ color: 0x355439, roughness: 1 }));
ground.position.set(110, -2, 80); ground.receiveShadow = true; scene.add(ground);
const grid = new THREE.GridHelper(240, 24, 0x69855b, 0x456447);
grid.position.set(110, -.4, 80); grid.material.transparent = true; grid.material.opacity = .22; scene.add(grid);

// Sparse illustrative forest. Seeded placement is visual only and does not affect link calculations.
let visualSeed = 19;
function random() { visualSeed = (visualSeed * 16807) % 2147483647; return visualSeed / 2147483647; }
const treeTrunk = new THREE.CylinderGeometry(.5, .8, 6, 5);
const treeCrown = new THREE.ConeGeometry(4, 13, 7);
for (let i = 0; i < 95; i++) {
  const x = random() * 235 - 8, z = random() * 175 - 8;
  const nearStation = [20, 80, 140, 200].some(a => [20, 80, 140].some(b => Math.hypot(x - a, z - b) < 14));
  if (nearStation) continue;
  const group = new THREE.Group(), height = .65 + random() * .65;
  const trunk = new THREE.Mesh(treeTrunk, new THREE.MeshStandardMaterial({ color: 0x62553c }));
  trunk.position.y = 3; group.add(trunk);
  const crown = new THREE.Mesh(treeCrown, new THREE.MeshStandardMaterial({ color: i % 2 ? 0x214a32 : 0x42653b }));
  crown.position.y = 10; crown.castShadow = true; group.add(crown);
  group.position.set(x, 0, z); group.scale.setScalar(height); scene.add(group);
}
function label(text, color = '#d9e8d4') {
  const canvas = document.createElement('canvas'); canvas.width = 128; canvas.height = 48;
  const ctx = canvas.getContext('2d'); ctx.fillStyle = '#10291ee6'; ctx.fillRect(0, 0, 128, 48);
  ctx.font = 'bold 24px Arial'; ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.fillText(text, 64, 32);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false }));
  sprite.scale.set(10, 3.75, 1); return sprite;
}
const stations = [];
for (let i = 0; i < 12; i++) {
  const protocol = Object.keys(palette)[i % 3], color = palette[protocol];
  const group = new THREE.Group(); group.position.set(20 + (i % 4) * 60, 0, 20 + Math.floor(i / 4) * 60);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, .7, 24), new THREE.MeshStandardMaterial({ color: 0x8d9d80 }));
  group.add(base);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(.3, .4, 6), new THREE.MeshStandardMaterial({ color: 0xa3b7a1 }));
  pole.position.y = 3; group.add(pole);
  const beacon = new THREE.Mesh(new THREE.BoxGeometry(2, 1.8, 2), new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: .35 }));
  beacon.position.y = 6; group.add(beacon);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(4, .12, 6, 50), new THREE.MeshBasicMaterial({ color }));
  ring.rotation.x = Math.PI / 2; ring.position.y = .4; group.add(ring);
  const text = label(`S${String(i).padStart(2, '0')}`); text.position.y = 10; group.add(text);
  scene.add(group); stations.push({ group, beacon, ring, protocol });
}
const drone = new THREE.Group(); drone.position.set(20, 14, 20); scene.add(drone);
const droneShadow = new THREE.Mesh(new THREE.RingGeometry(4, 4.3, 40), new THREE.MeshBasicMaterial({ color: 0xc5eea2, transparent: true, opacity: .6, side: THREE.DoubleSide }));
droneShadow.rotation.x = -Math.PI / 2; scene.add(droneShadow);
const droneLabel = label('DRONE 01', '#c5eea2'); droneLabel.position.y = 9; drone.add(droneLabel);
const rotorBlurs = [];
new ColladaLoader().load('/assets/cf2.dae', collada => {
  const mesh = collada.scene;
  const bounds = new THREE.Box3().setFromObject(mesh), size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const scale = 13 / Math.max(size.x, size.y, size.z);
  mesh.position.sub(center); const model = new THREE.Group(); model.add(mesh); model.scale.setScalar(scale);
  model.traverse(part => { if (part.isMesh) { part.castShadow = true; part.receiveShadow = true; } });
  drone.add(model);
  for (const x of [-4.8, 4.8]) for (const z of [-4.8, 4.8]) {
    const prop = new THREE.Mesh(new THREE.CircleGeometry(2.6, 24), new THREE.MeshBasicMaterial({ color: 0xc5e3de, transparent: true, opacity: .13, side: THREE.DoubleSide }));
    prop.rotation.x = -Math.PI / 2; prop.position.set(x, .6, z); drone.add(prop); rotorBlurs.push(prop);
  }
  $('model-status').textContent = 'Crazyflie 2.x · 3D mesh loaded';
}, undefined, error => { $('model-status').textContent = 'Drone mesh failed to load'; showError(String(error)); });
let routeLine = null, lastRouteKey = '', current = null, follow = false, shownSession = null;
const targetPosition = drone.position.clone(), packetLines = [], observedKeys = new Map();
function setRoute(points) {
  const key = `${points.length}`; if (key === lastRouteKey) return; lastRouteKey = key;
  if (routeLine) { scene.remove(routeLine); routeLine.geometry.dispose(); routeLine.material.dispose(); }
  routeLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(p[0], .6, p[1]))),
    new THREE.LineDashedMaterial({ color: 0xc5eea2, dashSize: 3, gapSize: 2, transparent: true, opacity: .7 }));
  routeLine.computeLineDistances(); scene.add(routeLine);
}
function packetFlash(station, point, color) {
  const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: .9 });
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([station.group.position.clone().add(new THREE.Vector3(0, 6, 0)), new THREE.Vector3(point[0], 14, point[1])]), material);
  scene.add(line); packetLines.push({ line, born: performance.now() });
}
const number = value => value == null ? '—' : Number(value).toFixed(1);
function showError(text) { $('error').textContent = text; $('error').hidden = !text; }
function applyState(state) {
  current = state; if (state.route) setRoute(state.route);
  if (state.status === 'idle') return;
  if (state.session !== shownSession) {
    shownSession = state.session;
    if (state.scenario_mode) $('scenario').value = state.scenario_mode;
    $('runs').value = state.runs; $('seed').value = state.seed;
    if (state.speed) $('speed').value = String(state.speed);
  }
  if (state.error) showError(state.error);
  targetPosition.set(state.position[0], 14, state.position[1]);
  drone.rotation.y = -state.heading;
  $('flight-state').textContent = state.status.toUpperCase();
  $('tour-label').textContent = `Tour ${String(state.run_id + 1).padStart(2, '0')} / ${state.runs}`;
  $('position-label').textContent = `${state.scenario.toUpperCase()} · x ${state.position[0].toFixed(0)} m / y ${state.position[1].toFixed(0)} m`;
  $('rows').textContent = state.counts.received.toLocaleString();
  $('clock').textContent = `${Math.floor(state.elapsed_s / 60)}:${String(Math.floor(state.elapsed_s % 60)).padStart(2, '0')}`;
  $('progress').textContent = `${Math.round(state.elapsed_s / state.total_s * 100)}% of ${state.runs} tour${state.runs > 1 ? 's' : ''}`;
  $('progress-bar').style.width = `${state.elapsed_s / state.total_s * 100}%`;
  $('session').textContent = `artifacts/live/${state.session}/readings.csv`;
  $('start').disabled = state.status === 'running'; $('stop').disabled = state.status !== 'running';
  $('download').classList.remove('disabled');
  const fresh = state.stations.filter(s => s.age_s != null && s.age_s <= 30);
  const alarms = state.stations.filter(s => s.decision === 'ALARM');
  const uncertain = state.stations.some(s => s.decision === 'WARNING');
  $('fresh').textContent = fresh.length; $('alarms').textContent = alarms.length;
  $('decision').textContent = alarms.length ? 'ALARM' : uncertain ? 'WARNING' : 'NO ALARM';
  document.querySelector('.decision-panel').className = `panel decision-panel ${alarms.length ? 'alarm' : uncertain ? '' : 'clear'}`;
  $('reason').textContent = alarms.length ? 'Fire-like measurements at fresh stations. Inspect the highlighted sensor readings.' : uncertain ? 'Some stations are unvisited, stale or missing a measurement. Continue collection.' : 'Fresh complete measurements are below the learned alarm cutoff.';
  $('link-stats').innerHTML = Object.entries(state.links).map(([name, counts]) => `<div class="link-row"><b style="color:#${palette[name].toString(16)}">${name === 'proprietary' ? 'Custom' : name === 'wifi' ? 'WiFi' : 'Bluetooth'}</b><small>${counts.received.toLocaleString()} received · ${counts.lost} lost</small></div>`).join('');
  $('readings').innerHTML = state.stations.map(s => {
    const r = s.reading;
    const key = r ? `${state.session}:${r.run_id}:${r.sequence}` : null;
    if (r && observedKeys.get(s.id) !== key) { observedKeys.set(s.id, key); if (state.status === 'running') packetFlash(stations[s.id], state.position, palette[s.protocol]); }
    const color = s.decision === 'ALARM' ? 0xf96b76 : palette[s.protocol];
    stations[s.id].beacon.material.color.setHex(color); stations[s.id].beacon.material.emissive.setHex(color);
    stations[s.id].ring.material.color.setHex(color);
    stations[s.id].beacon.material.emissiveIntensity = s.in_range ? .8 : .1;
    return `<tr><td>S${String(s.id).padStart(2, '0')}</td><td>${s.protocol}</td><td>${number(r?.temperature_c)}</td><td>${number(r?.humidity_pct)}</td><td>${number(r?.smoke_ppm)}</td><td>${number(r?.co_ppm)}</td><td>${s.age_s == null ? 'unvisited' : number(s.age_s) + ' s'}</td><td><span class="status ${s.decision}">${s.decision}</span></td></tr>`;
  }).join('');
}
const events = new EventSource('/api/events');
events.onmessage = event => { $('connection').textContent = '● STREAM CONNECTED'; $('connection').classList.remove('offline'); applyState(JSON.parse(event.data)); };
events.onerror = () => { $('connection').textContent = 'RECONNECTING…'; $('connection').classList.add('offline'); };
async function command(url, body) {
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });
  const result = await response.json(); if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the experiment settings.'); return result;
}
$('start').onclick = async () => {
  showError(''); $('start').disabled = true;
  try { await command('/api/start', { scenario: $('scenario').value, runs: Number($('runs').value), seed: Number($('seed').value), steps: 120, speed: Number($('speed').value) }); observedKeys.clear(); }
  catch (error) { showError(error.message); $('start').disabled = false; }
};
$('stop').onclick = async () => { try { await command('/api/stop'); } catch (error) { showError(error.message); } };
$('training-preset').onclick = () => { $('scenario').value = 'mixed'; $('runs').value = '15'; $('speed').value = '64'; };
$('follow').onclick = () => { follow = true; };
$('overview').onclick = () => { follow = false; camera.position.set(285, 235, 310); orbit.target.set(110, 0, 80); };
new ResizeObserver(() => { const { width, height } = $('scene').getBoundingClientRect(); renderer.setSize(width, height); camera.aspect = width / height; camera.updateProjectionMatrix(); }).observe($('scene'));
let lastFrame = performance.now();
function animate(now) {
  requestAnimationFrame(animate); const dt = Math.min((now - lastFrame) / 1000, .1); lastFrame = now;
  drone.position.lerp(targetPosition, 1 - Math.exp(-dt * 8));
  droneShadow.position.set(drone.position.x, .3, drone.position.z);
  if (follow) { camera.position.lerp(drone.position.clone().add(new THREE.Vector3(26, 22, 32)), .06); orbit.target.lerp(drone.position, .1); }
  for (let i = packetLines.length - 1; i >= 0; i--) { const age = now - packetLines[i].born; packetLines[i].line.material.opacity = Math.max(0, 1 - age / 650); if (age > 650) { scene.remove(packetLines[i].line); packetLines[i].line.geometry.dispose(); packetLines[i].line.material.dispose(); packetLines.splice(i, 1); } }
  rotorBlurs.forEach((prop, i) => { prop.material.opacity = current?.status === 'running' ? .12 + .04 * Math.sin(now / 40 + i) : .04; });
  orbit.update(); renderer.render(scene, camera);
}
requestAnimationFrame(animate);
