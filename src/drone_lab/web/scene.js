import * as THREE from 'three';
import { ColladaLoader } from './vendor/loaders/ColladaLoader.js';
import { SmoothCamera } from './camera.js';

export const palette = { bluetooth: 0x51ccff, wifi: 0xffbe6b, proprietary: 0xb394ff };
const fleetColors = [0xc5eea2, 0x68dcff, 0xffce7a, 0xd2a0ff, 0xff8cae, 0x80ffd2, 0xfff3ab, 0xa8b9ff];
const themes = {
  forest: { ground: 0x355439, sky: 0x17291f, crown: 0x214a32, density: 1 },
  meadow: { ground: 0x708646, sky: 0x3d5e65, crown: 0x5a7833, density: .24 },
  desert: { ground: 0xc59c65, sky: 0x80745f, crown: 0x65724a, density: .12 },
};

function label(text, color = '#d9e8d4') {
  const canvas = document.createElement('canvas'); canvas.width = 160; canvas.height = 48;
  const ctx = canvas.getContext('2d'); ctx.fillStyle = '#10291ed9'; ctx.fillRect(0, 0, 160, 48);
  ctx.font = 'bold 22px Arial'; ctx.fillStyle = color; ctx.textAlign = 'center'; ctx.fillText(text, 80, 31);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false }));
  sprite.scale.set(10, 3, 1); return sprite;
}

function dispose(group) {
  group.traverse(object => {
    object.geometry?.dispose();
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) { material?.map?.dispose(); material?.dispose(); }
  });
  group.removeFromParent();
}

export class FieldScene {
  constructor(element, onModel, onError) {
    this.element = element;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(43, 1, .1, 4000);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    element.appendChild(this.renderer.domElement);
    this.cameraControl = new SmoothCamera(this.camera, this.renderer.domElement);
    this.scene.add(new THREE.HemisphereLight(0xd6f0e5, 0x384d25, 2.3));
    this.sun = new THREE.DirectionalLight(0xffe4b3, 3.2);
    this.sun.castShadow = true; this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -.001; this.scene.add(this.sun, this.sun.target);
    this.world = null; this.stations = []; this.drones = []; this.flashes = [];
    this.geometryKey = ''; this.config = null; this.meshTemplate = null;
    this.selected = 0; this.running = false; this.lastFrame = performance.now();
    new ColladaLoader().load('/assets/cf2.dae', collada => {
      const mesh = collada.scene;
      const box = new THREE.Box3().setFromObject(mesh), size = box.getSize(new THREE.Vector3());
      mesh.position.sub(box.getCenter(new THREE.Vector3()));
      this.meshTemplate = new THREE.Group(); this.meshTemplate.add(mesh);
      this.meshTemplate.scale.setScalar(13 / Math.max(size.x, size.y, size.z));
      this.meshTemplate.traverse(part => { if (part.isMesh) { part.castShadow = true; part.receiveShadow = true; } });
      for (const drone of this.drones) this.attachModel(drone);
      onModel('Crazyflie 2.x · fleet model loaded');
    }, undefined, error => onError('Could not load the 3D drone mesh: ' + error));
    new ResizeObserver(() => {
      const { width, height } = element.getBoundingClientRect();
      this.renderer.setSize(width, height); this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    }).observe(element);
    requestAnimationFrame(now => this.animate(now));
  }

  configure(environment, stationData, path, count, seed = 42) {
    const key = JSON.stringify([environment, stationData.map(s => [s.x, s.y]), path, count, seed]);
    if (key === this.geometryKey) return false;
    this.geometryKey = key; this.config = environment;
    if (this.world) dispose(this.world);
    for (const drone of this.drones) {
      // Cloned drone meshes share resources with the retained template.
      drone.model?.removeFromParent(); dispose(drone.group); dispose(drone.shadow);
    }
    for (const flash of this.flashes) dispose(flash.line);
    this.flashes = []; this.drones = []; this.stations = [];
    this.world = new THREE.Group(); this.scene.add(this.world);
    const { width_m: width, height_m: height, preset, vegetation } = environment;
    const theme = themes[preset];
    this.scene.background = new THREE.Color(theme.sky);
    this.scene.fog = new THREE.Fog(theme.sky, width * 2, width * 5);
    this.sun.position.set(width * .4, width, -height * .3);
    this.sun.target.position.set(width / 2, 0, height / 2);
    Object.assign(this.sun.shadow.camera, { left: -width, right: width, top: width, bottom: -width, far: width * 4 });
    this.sun.shadow.camera.updateProjectionMatrix();
    const ground = new THREE.Mesh(new THREE.BoxGeometry(width + 40, 3, height + 40), new THREE.MeshStandardMaterial({ color: theme.ground, roughness: 1 }));
    ground.position.set(width / 2, -2, height / 2); ground.receiveShadow = true; this.world.add(ground);
    const grid = new THREE.GridHelper(width, Math.round(width / 10), 0x8b9c77, 0x718460);
    grid.position.set(width / 2, -.4, height / 2); grid.material.transparent = true; grid.material.opacity = .2; this.world.add(grid);
    let visualSeed = (seed % 2147483646) + 1;
    const random = () => { visualSeed = visualSeed * 16807 % 2147483647; return visualSeed / 2147483647; };
    const treeCount = Math.round(vegetation * 2 * theme.density);
    for (let i = 0; i < treeCount; i++) {
      const x = random() * width, y = random() * height;
      if (stationData.some(s => Math.hypot(x - s.x, y - s.y) < 13)) continue;
      const tree = new THREE.Group();
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(.5, .8, 6, 5), new THREE.MeshStandardMaterial({ color: 0x62553c }));
      trunk.position.y = 3; tree.add(trunk);
      const crown = new THREE.Mesh(preset === 'desert' ? new THREE.IcosahedronGeometry(3, 0) : new THREE.ConeGeometry(4, 13, 7), new THREE.MeshStandardMaterial({ color: theme.crown }));
      crown.position.y = preset === 'desert' ? 4 : 10; crown.castShadow = true; tree.add(crown);
      tree.position.set(x, 0, y); tree.scale.setScalar(.65 + random() * .65); this.world.add(tree);
    }
    for (const data of stationData) {
      const protocol = data.protocol || Object.keys(palette)[data.id % 3], color = palette[protocol];
      const group = new THREE.Group(); group.position.set(data.x, 0, data.y);
      const base = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, .7, 20), new THREE.MeshStandardMaterial({ color: 0x8d9d80 })); group.add(base);
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(.3, .4, 6), new THREE.MeshStandardMaterial({ color: 0xa3b7a1 })); pole.position.y = 3; group.add(pole);
      const beacon = new THREE.Mesh(new THREE.BoxGeometry(2, 1.8, 2), new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: .35 })); beacon.position.y = 6; group.add(beacon);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(4, .12, 6, 40), new THREE.MeshBasicMaterial({ color })); ring.rotation.x = Math.PI / 2; ring.position.y = .4; group.add(ring);
      const text = label(`S${String(data.id).padStart(2, '0')}`); text.position.y = 10; group.add(text);
      this.world.add(group); this.stations.push({ group, beacon, ring });
    }
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(path.map(p => new THREE.Vector3(p[0], .6, p[1]))), new THREE.LineDashedMaterial({ color: 0xc5eea2, dashSize: 3, gapSize: 2, transparent: true, opacity: .7 }));
    line.computeLineDistances(); this.world.add(line); this.routeLine = line; this.grid = grid;
    for (let i = 0; i < count; i++) {
      const group = new THREE.Group(); const color = fleetColors[i];
      const marker = label(`DRONE ${i + 1}`, '#' + color.toString(16)); marker.position.y = 9; group.add(marker);
      const shadow = new THREE.Mesh(new THREE.RingGeometry(4, 4.3, 40), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .6, side: THREE.DoubleSide })); shadow.rotation.x = -Math.PI / 2;
      const point = path[Math.floor(i * (path.length - 1) / count)];
      group.position.set(point[0], 14 + i * 2, point[1]); this.scene.add(group, shadow);
      const drone = { group, shadow, target: group.position.clone(), heading: 0, model: null, rotors: [] };
      for (const x of [-4.8, 4.8]) for (const z of [-4.8, 4.8]) {
        const rotor = new THREE.Mesh(new THREE.CircleGeometry(2.6, 24), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .13, side: THREE.DoubleSide }));
        rotor.rotation.x = -Math.PI / 2; rotor.position.set(x, .6, z); group.add(rotor); drone.rotors.push(rotor);
      }
      this.drones.push(drone); this.attachModel(drone);
    }
    this.selected = Math.min(this.selected, count - 1);
    this.cameraControl.overview(width, height, this.configured !== true);
    this.configured = true;
    return true;
  }

  attachModel(drone) {
    if (this.meshTemplate && !drone.model) { drone.model = this.meshTemplate.clone(true); drone.group.add(drone.model); }
  }

  update(state, snap = false) {
    this.visibleEvents = state.visible_events || [];
    this.running = state.status === 'running';
    for (const data of state.drones) {
      const drone = this.drones[data.id]; if (!drone) continue;
      drone.target.set(data.position[0], data.altitude_m, data.position[1]);
      drone.heading = -data.heading;
      if (snap) { drone.group.position.copy(drone.target); drone.group.rotation.y = drone.heading; }
    }
    for (const data of state.stations) {
      const station = this.stations[data.id];
      const color = data.decision === 'ALARM' ? 0xf96b76 : palette[data.protocol];
      station.beacon.material.color.setHex(color); station.beacon.material.emissive.setHex(color);
      station.ring.material.color.setHex(color); station.beacon.material.emissiveIntensity = data.in_range ? .8 : .1;
    }
  }

  async captureDroneFrame() {
    const vehicle = this.drones[this.selected];
    if (!vehicle) throw new Error('Select an available drone.');
    // Render a separate clean perspective. No station labels, alarms, route or packet flashes.
    const camera = new THREE.PerspectiveCamera(72, this.camera.aspect, 0.1, 2000);
    camera.position.copy(vehicle.group.position);
    const yaw = vehicle.group.rotation.y;
    camera.lookAt(camera.position.clone().add(new THREE.Vector3(Math.cos(yaw), -.8, -Math.sin(yaw))));
    const hidden = [this.grid, this.routeLine, ...this.stations.map(s=>s.group),
                    ...this.drones.flatMap(d=>[d.group,d.shadow]), ...this.flashes.map(f=>f.line)];
    const events = new THREE.Group();
    for (const event of this.visibleEvents || []) {
      const plume = new THREE.Mesh(new THREE.IcosahedronGeometry(2 + event.strength * 3, 1),
        new THREE.MeshStandardMaterial({color:0x858585, transparent:true, opacity:.65}));
      plume.position.set(event.x, 5 + event.strength * 4, event.y); events.add(plume);
      if (event.kind === 'fire') {
        const flame = new THREE.Mesh(new THREE.ConeGeometry(2 + event.strength, 5 + event.strength * 5, 8),
          new THREE.MeshBasicMaterial({color:0xff7427}));
        flame.position.set(event.x, 3, event.y); events.add(flame);
      }
    }
    this.scene.add(events);
    const capture = document.createElement('canvas');
    const scale = 640 / Math.max(this.element.clientWidth, this.element.clientHeight, 1);
    capture.width = Math.max(1, Math.round(this.element.clientWidth * scale));
    capture.height = Math.max(1, Math.round(this.element.clientHeight * scale));
    const previous = hidden.map(object=>object.visible);
    try {
      hidden.forEach(object=>object.visible=false);
      this.renderer.render(this.scene,camera);
      capture.getContext('2d').drawImage(this.renderer.domElement,0,0,capture.width,capture.height);
    } finally {
      hidden.forEach((object,index)=>object.visible=previous[index]);
      dispose(events);
      this.renderer.render(this.scene,this.camera);
    }
    return new Promise((resolve,reject)=>capture.toBlob(blob=>blob ? resolve(blob) :
        reject(new Error('Frame capture failed.')), 'image/jpeg', .84));
  }

  flash(sensor, droneId) {
    const station = this.stations[sensor], drone = this.drones[droneId];
    if (!station || !drone) return;
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([station.group.position.clone().add(new THREE.Vector3(0, 6, 0)), drone.group.position.clone()]), new THREE.LineBasicMaterial({ color: fleetColors[droneId], transparent: true, opacity: .9 }));
    this.scene.add(line); this.flashes.push({ line, born: performance.now() });
  }

  follow() { this.cameraControl.follow(() => this.drones[this.selected]?.group.position); }
  overview() { this.cameraControl.overview(this.config.width_m, this.config.height_m); }

  animate(now) {
    requestAnimationFrame(time => this.animate(time));
    const dt = Math.min((now - this.lastFrame) / 1000, .1); this.lastFrame = now;
    for (const drone of this.drones) {
      const damping = 1 - Math.exp(-dt * 12);
      drone.group.position.lerp(drone.target, damping);
      const angle = Math.atan2(Math.sin(drone.heading - drone.group.rotation.y), Math.cos(drone.heading - drone.group.rotation.y));
      drone.group.rotation.y += angle * damping;
      drone.shadow.position.set(drone.group.position.x, .3, drone.group.position.z);
      drone.rotors.forEach((rotor, i) => { rotor.material.opacity = this.running ? .12 + .04 * Math.sin(now / 40 + i) : .04; });
    }
    for (let i = this.flashes.length - 1; i >= 0; i--) {
      const age = now - this.flashes[i].born;
      this.flashes[i].line.material.opacity = Math.max(0, 1 - age / 650);
      if (age > 650) { dispose(this.flashes[i].line); this.flashes.splice(i, 1); }
    }
    this.cameraControl.update(dt); this.renderer.render(this.scene, this.camera);
  }
}
