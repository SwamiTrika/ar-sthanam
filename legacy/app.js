import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
import { MindARThree } from 'https://cdn.jsdelivr.net/npm/mind-ar@1.2.5/dist/mindar-image-three.prod.js';

const config = window.AR_STHANAM_CONFIG;
const statusEl = document.getElementById('status');

function setStatus(text) {
  statusEl.textContent = text;
}

// MindAR's target-local coordinate system: origin at the marker's center,
// marker width spans 1 unit, Z points out of the card (i.e. straight up,
// once the card is lying flat on the floor). Converting real-world feet
// into that unit system means dividing by the physical marker width.
const markerWidthFeet = config.markerWidthInches / 12;
function feetToUnits(feet) {
  return feet / markerWidthFeet;
}

// Single reactive scale value. v1 keeps it fixed at 1; the scale variant
// wires a pinch-gesture handler to mutate this and re-apply it to the model.
const state = {
  modelScale: 1,
};

async function buildModel() {
  const heightUnits = feetToUnits(config.modelHeightFeet);
  const footprintUnits = feetToUnits(config.modelFootprintFeet);

  if (config.model.type === 'gltf') {
    const { GLTFLoader } = await import('https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/GLTFLoader.js');
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(config.model.url);
    const model = gltf.scene;
    // Assumes the source asset is authored with Y-up and unit height;
    // rotate onto the marker's Z-up local space and scale to real height.
    model.rotation.x = Math.PI / 2;
    const box = new THREE.Box3().setFromObject(model);
    const sourceHeight = box.max.y - box.min.y || 1;
    const scaleFactor = heightUnits / sourceHeight;
    model.scale.setScalar(scaleFactor);
    return model;
  }

  // Placeholder: a simple upright square box, base resting on the card.
  const geometry = new THREE.BoxGeometry(footprintUnits, footprintUnits, heightUnits);
  const material = new THREE.MeshStandardMaterial({ color: config.model.color });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.z = heightUnits / 2;
  return mesh;
}

async function main() {
  setStatus('Requesting camera access…');

  // Desktop machines with multiple cameras (e.g. a built-in webcam plus a
  // USB one) may need a specific device picked explicitly — the browser
  // has no "environment-facing" camera to prefer automatically like a
  // phone does. Override via config.cameraDeviceId, or append
  // ?deviceId=<id> to the URL. Available device IDs are logged below once
  // permission is granted.
  const params = new URLSearchParams(window.location.search);
  const cameraDeviceId = params.get('deviceId') || config.cameraDeviceId || null;

  const mindarThree = new MindARThree({
    container: document.getElementById('ar-container'),
    imageTargetSrc: config.markerTargetSrc,
    uiScanning: false,
    uiLoading: false,
    environmentDeviceId: cameraDeviceId,
    missTolerance: config.trackingMissTolerance,
    warmupTolerance: config.trackingWarmupTolerance,
  });

  const { renderer, scene, camera } = mindarThree;

  scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.2));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(0.5, 1, 0.5);
  scene.add(dirLight);

  const anchor = mindarThree.addAnchor(0);
  const modelGroup = new THREE.Group();
  modelGroup.scale.setScalar(state.modelScale);
  anchor.group.add(modelGroup);

  const model = await buildModel();
  modelGroup.add(model);

  anchor.onTargetFound = () => setStatus('');
  anchor.onTargetLost = () => setStatus('Point your camera at the card');

  try {
    await mindarThree.start();
  } catch (err) {
    setStatus('Camera access failed — check permissions and reload.');
    console.error(err);
    return;
  }

  navigator.mediaDevices.enumerateDevices().then((devices) => {
    const cams = devices.filter((d) => d.kind === 'videoinput');
    console.log('Available cameras (use ?deviceId=<id> to pick one):', cams);
  });

  setStatus('Point your camera at the card');

  renderer.setAnimationLoop(() => {
    renderer.render(scene, camera);
  });
}

main();
