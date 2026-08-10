// Central config for the AR experience. Swap values here rather than
// touching app.js when the final model or marker artwork is ready.
window.AR_STHANAM_CONFIG = {
  // Path to the compiled MindAR tracking file for the printed card.
  markerTargetSrc: '../assets/marker.mind',

  // Physical width of the printed marker card, in inches. Used to convert
  // MindAR's marker-relative units into real-world feet.
  markerWidthInches: 7,

  // Real-world height of the placed object, in feet.
  modelHeightFeet: 5,

  // Real-world footprint (width & depth) of the placeholder box, in feet.
  modelFootprintFeet: 1.5,

  // Model source. type: 'box' uses a procedural placeholder.
  // Switch to type: 'gltf' + url: '../assets/model.glb' once the final
  // asset is ready — the loader in app.js handles both without other changes.
  model: {
    type: 'box',
    color: 0x2e86de,
  },

  // Fixed in v1 per the PRD. The scale variant (variant 2) flips this to
  // true and wires pinch gestures to state.modelScale in app.js.
  allowUserScale: false,

  // Explicit camera device to use (from navigator.mediaDevices.enumerateDevices).
  // Leave null to let the browser pick — fine on phones, but a desktop with
  // multiple cameras (e.g. built-in + USB) may need this set. Can also be
  // overridden per-load via ?deviceId=<id> in the URL.
  cameraDeviceId: null,

  // How many consecutive frames the marker can be lost/blurry before the
  // object is hidden. MindAR's default (5, ~1/6s at 30fps) hides it the
  // instant the card is even briefly out of frame or motion-blurred, which
  // reads as "you must keep staring at the card." Raised here to ~2s of
  // grace. This does NOT let you walk fully out of view of the card and
  // back — MindAR has no persistent world tracking, only marker
  // re-detection — it just tolerates brief glances away / blur / partial
  // occlusion without flickering the object out.
  trackingMissTolerance: 60,

  // Consecutive frames required to confirm a fresh detection before
  // showing the object. MindAR default is 5 (~1/6s); left as-is here since
  // slower warmup makes initial placement feel laggy without much benefit.
  trackingWarmupTolerance: 5,
};
