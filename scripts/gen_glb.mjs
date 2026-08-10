import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// GLTFExporter's binary path uses FileReader to turn its output Blob into
// an ArrayBuffer, which Node doesn't provide. Node's Blob already supports
// arrayBuffer() directly, so this shim is enough for that one call site.
globalThis.FileReader = class {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((buf) => {
      this.result = buf;
      this.onloadend && this.onloadend();
    });
  }
};

const THREE = await import('three');
const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

const FEET_TO_M = 0.3048;
const heightM = 5 * FEET_TO_M;
const footprintM = 1.5 * FEET_TO_M;

const geometry = new THREE.BoxGeometry(footprintM, heightM, footprintM);
const material = new THREE.MeshStandardMaterial({ color: 0x2e86de });
const mesh = new THREE.Mesh(geometry, material);
mesh.position.y = heightM / 2; // base rests at y=0, matching Scene Viewer's floor placement
mesh.name = 'Box';

const scene = new THREE.Scene();
scene.add(mesh);

const exporter = new GLTFExporter();
exporter.parse(
  scene,
  (result) => {
    const outPath = path.join(root, 'assets', 'model.glb');
    fs.writeFileSync(outPath, Buffer.from(result));
    console.log('wrote', outPath, result.byteLength, 'bytes');
  },
  (err) => {
    console.error('export failed', err);
    process.exit(1);
  },
  { binary: true }
);
