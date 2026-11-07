import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

export class SmoothCamera {
  constructor(camera, element) {
    this.camera = camera;
    this.controls = new OrbitControls(camera, element);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = .08;
    this.controls.maxPolarAngle = Math.PI * .48;
    this.controls.minDistance = 12;
    this.controls.maxDistance = 2000;
    // Wheel deltas drive a target radius instead of snapping the camera radius.
    this.controls.enableZoom = false;
    this.distance = 350;
    this.following = false;
    this.transition = null;
    this.targetProvider = () => null;
    this.pointers = new Map();
    this.pinchDistance = null;
    element.addEventListener('wheel', event => {
      event.preventDefault();
      const pixels = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 300 : 1);
      this.zoom(Math.exp(THREE.MathUtils.clamp(pixels, -150, 150) * .002));
    }, { passive: false });
    element.addEventListener('pointerdown', event => {
      this.transition = null;
      this.pointers.set(event.pointerId, new THREE.Vector2(event.clientX, event.clientY));
    });
    element.addEventListener('pointermove', event => {
      if (!this.pointers.has(event.pointerId)) return;
      this.pointers.set(event.pointerId, new THREE.Vector2(event.clientX, event.clientY));
      if (this.pointers.size === 2) {
        const [a, b] = [...this.pointers.values()];
        const separation = a.distanceTo(b);
        if (this.pinchDistance && separation > 0) this.zoom(this.pinchDistance / separation);
        this.pinchDistance = separation;
      }
    });
    const release = event => { this.pointers.delete(event.pointerId); this.pinchDistance = null; };
    element.addEventListener('pointerup', release);
    element.addEventListener('pointercancel', release);
  }

  zoom(factor) {
    this.transition = null;
    this.distance = THREE.MathUtils.clamp(this.distance * factor, 12, 2000);
  }

  follow(provider) {
    this.following = true;
    this.transition = null;
    this.targetProvider = provider;
    this.controls.enablePan = false;
    this.distance = 48;
  }

  overview(width, height, immediate = false) {
    this.following = false;
    this.controls.enablePan = true;
    const span = Math.max(width, height);
    const target = new THREE.Vector3(width / 2, 0, height / 2);
    const position = target.clone().add(new THREE.Vector3(span * .8, span * .9, span));
    this.distance = position.distanceTo(target);
    this.transition = { target, position };
    if (immediate) {
      this.camera.position.copy(position);
      this.controls.target.copy(target);
      this.transition = null;
    }
  }

  update(dt) {
    const amount = 1 - Math.exp(-6 * dt);
    if (this.transition) {
      this.controls.target.lerp(this.transition.target, amount);
      this.camera.position.lerp(this.transition.position, amount);
      if (this.camera.position.distanceTo(this.transition.position) < .05) this.transition = null;
    } else {
      if (this.following) {
        const selected = this.targetProvider();
        if (selected) {
          const delta = selected.clone().sub(this.controls.target).multiplyScalar(amount);
          this.controls.target.add(delta);
          this.camera.position.add(delta);
        }
      }
      const offset = this.camera.position.clone().sub(this.controls.target);
      const radius = THREE.MathUtils.lerp(offset.length(), this.distance, 1 - Math.exp(-10 * dt));
      this.camera.position.copy(this.controls.target).add(offset.setLength(radius));
    }
    this.controls.update();
  }
}
