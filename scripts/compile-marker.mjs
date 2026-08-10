import { OfflineCompiler } from 'mind-ar/src/image-target/offline-compiler.js';
import { loadImage } from 'mind-ar/node_modules/canvas/index.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

const markerPath = path.join(root, 'assets', 'marker.png');
const outPath = path.join(root, 'assets', 'marker.mind');

const img = await loadImage(markerPath);
console.log('loaded image', img.width, img.height);

const compiler = new OfflineCompiler();
await compiler.compileImageTargets([img], (percent) => {
  process.stdout.write(`\rcompiling... ${percent.toFixed(1)}%`);
});
console.log('\ndone compiling');

const buffer = compiler.exportData();
fs.writeFileSync(outPath, Buffer.from(buffer));
console.log('wrote', outPath, buffer.byteLength, 'bytes');
