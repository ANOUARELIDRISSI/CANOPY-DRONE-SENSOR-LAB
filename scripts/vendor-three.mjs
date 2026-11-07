import { mkdir, copyFile } from 'node:fs/promises';
const target = 'src/drone_lab/web/vendor';
await mkdir(target, { recursive: true });
await mkdir(`${target}/loaders`, { recursive: true });
for (const [source, name] of [
  ['build/three.module.js', 'three.module.js'],
  ['build/three.core.js', 'three.core.js'],
  ['examples/jsm/controls/OrbitControls.js', 'OrbitControls.js'],
  ['examples/jsm/loaders/ColladaLoader.js', 'loaders/ColladaLoader.js'],
  ['examples/jsm/loaders/TGALoader.js', 'loaders/TGALoader.js'],
  ['LICENSE', 'LICENSE.three'],
]) await copyFile(`node_modules/three/${source}`, `${target}/${name}`);
