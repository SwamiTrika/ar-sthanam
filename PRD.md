# PRD: AR Sthanam — Web-Based AR Placement Experience

## 1. Overview
A no-app-install web AR experience. A user scans a QR code, which opens a mobile web page. The page activates the phone camera, the user points it at a printed marker card placed on the floor, and a 3D model (v1: a 5-ft-tall square/box placeholder) appears anchored to that exact spot in AR.

## 2. Goals
- Zero-install AR via mobile browser (iOS Safari + Android Chrome), reached directly from a QR code.
- Precise, repeatable placement tied to a physical card via image tracking (not generic floor-tap placement).
- v1 ships with a placeholder box model; architecture supports swapping in a final `.glb` model later without rework.
- A second variant (future/parallel build) allows pinch-to-scale; v1 keeps the model fixed-size. Build the scaling hook now so variant 2 is a config flip, not a rewrite.

## 3. Out of Scope (v1)
- Branded UI chrome (logo, styled overlays) — bare minimal viewer only.
- Multi-model libraries, model animation, or persistence across sessions.
- Native app / App Clip / Instant App.
- Analytics, accounts, or content management.
- QR code generation and hosting/deployment — handled by the user separately.

## 4. User Flow
1. User scans QR code with phone camera → opens URL in default mobile browser.
2. Page loads, requests camera permission, shows a live camera feed with a short instruction ("Point your camera at the card").
3. User places the physical marker card on the floor and points the phone at it.
4. App recognizes the marker image, computes its position/orientation.
5. A 5-ft-tall square/box appears anchored to the card's position, upright, scaled correctly relative to real-world space.
6. User can walk around the object and view it from any angle (camera moves, object stays anchored). Object does not rotate/scale via touch in v1.
7. If the marker moves out of frame, tracking pauses; when it's back in frame, the object reappears in the same anchored spot.

## 5. Technical Approach

### 5.1 Core stack
- **Three.js** for 3D rendering.
- **MindAR (image-tracking)** for marker detection and camera pose estimation — chosen over WebXR because WebXR hit-test/plane-detection has weak-to-no support in iOS Safari, and the requirement is "both platforms, consistent behavior." MindAR runs on any modern mobile browser via WebGL + `getUserMedia`, no native AR APIs required.
- Static site: plain HTML/JS (or a minimal Vite build) — no backend needed since hosting/deployment is out of scope for this build.

### 5.2 Marker / card
- I generate a placeholder high-contrast marker image (feature-rich, asymmetric, good for tracking) for you to print onto the physical card.
- The marker image is compiled offline into a `.mind` target file (MindAR's compiled tracking data) that the app loads at runtime.
- Marker artwork and `.mind` file are swappable — replacing them with final branded card art is a config change, not a code change.

### 5.3 3D model
- v1: procedurally generated box geometry in Three.js — 5 ft tall (converted to meters: ~1.524 m), square footprint, simple material/color. No external asset dependency.
- Model source is abstracted behind a small loader/config so a future `.glb` file can be dropped in and referenced by path/config instead of code changes.

### 5.4 Placement & anchoring
- On marker detection, MindAR provides a continuously-updated anchor transform; the box is parented to that anchor, positioned so its base sits at the card's plane (floor level) and it stands upright (5 ft in the vertical/world-up axis regardless of card orientation on the floor).
- Fixed scale/position in v1 (no user gesture control).
- Architecture note for variant 2: scale will be exposed as a single reactive value (e.g., `modelScale`) driving the object's transform, so adding pinch-to-scale later means wiring a gesture handler to that existing value — not restructuring placement logic.

### 5.5 Browser/device support
- Target: iOS Safari (16+) and Android Chrome (recent versions), consistent behavior on both.
- Requires HTTPS (camera access) — flagged for whoever hosts the page.
- No fallback UI needed for unsupported browsers in v1 (can add a "camera/AR not supported" message later if needed).

## 6. Deliverables
1. Self-contained web AR page (HTML/JS/Three.js/MindAR) in this folder, runnable via any static server.
2. Placeholder marker image (PNG) for printing on the card, plus its compiled `.mind` tracking file.
3. Brief README covering: how to test locally over HTTPS on a phone, how to swap the marker image, how to swap in a final `.glb` model.

## 7. Open Items / Assumptions
- Card size: ~7" square. Marker image will be generated/exported sized for a 7" square print at 300 DPI (2100×2100px).
- "5 feet tall" assumed to mean the model's real-world height when rendered; will convert internally to meters (Three.js/MindAR default unit).
- You'll handle deployment to HTTPS hosting and QR code generation once the page is ready to test on-device.

## 8. Revision: v2 — real-world persistence (post on-device testing)

On-device testing of v1 surfaced a requirement not captured above:
**the object must stay in place even after the camera loses sight of the
card**, not just while the card is in frame. Section 5.1's original
architecture (MindAR image tracking, no WebXR) cannot do this — MindAR
has no persistent world tracking, only frame-by-frame marker
re-detection, which was a known trade-off at the time but not one we'd
explicitly weighed against "walk fully around/behind the object."

Confirmed live (mid-2026) that iOS Safari still has no WebXR AR support,
ruling out the straightforward WebXR fix. Revised approach, agreed with
stakeholder:

- Replace in-page rendering with a **hand-off to each platform's native
  AR viewer** — Apple AR Quick Look (iOS) / Google Scene Viewer
  (Android) — both use the phone's real ARKit/ARCore SLAM, giving actual
  persistent world-lock. Still zero app-install (system-level viewers
  launched from a normal link).
- iOS keeps card-based placement via USDZ image-anchoring metadata
  (unverified on real hardware as of this writing — see `README.md`).
- Android loses card-guided placement (Scene Viewer only supports
  tap-to-place on a detected plane) in exchange for the same real
  persistence. This is a platform capability gap, not a choice — flagged
  as an open risk if precise Android placement turns out to matter as
  much as iOS.
- The original in-page MindAR build is preserved in `legacy/` rather
  than deleted, since it may still be useful (e.g. if iOS Safari ever
  ships WebXR AR, or as a base for the future scale variant).

See `README.md` for full technical detail and the specific verification
step needed before go-live (the USDZ anchoring block).
