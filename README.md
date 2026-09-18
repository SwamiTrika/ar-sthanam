# AR Sthanam

Web-based AR: scan a QR code → tap "View in your space" → point your
phone at a printed marker card on the floor → a life-size 3D object
appears anchored to that spot **and stays there even after you look
away from the card**.

v1 is a placeholder: a 5ft-tall, 1.5ft-square box.

## Architecture (v2 — native AR viewer hand-off)

The first version of this used [MindAR](https://github.com/hiukim/mind-ar-js)
image tracking running entirely in-page. That gave precise card-based
placement, but **no persistence** — MindAR has no memory of the object's
position; it re-derives it from the card every frame, so the object
vanishes the instant the card leaves the camera's view. Real "place it
once, walk anywhere" behavior needs the phone's own SLAM (ARKit/ARCore),
which in-page JavaScript can only get via WebXR — and iOS Safari still
does not support WebXR AR sessions (confirmed live, mid-2026; it's
VR-only, Vision Pro-only).

So v2 hands off to each platform's **native AR viewer** instead of
rendering in-page:

- **iOS**: [AR Quick Look](https://developer.apple.com/augmented-reality/quick-look/),
  triggered via `<a rel="ar">` / `model-viewer`'s `ios-src`, loading
  `assets/model.usdz`. This file has Apple's image-anchoring metadata
  baked in, so Quick Look recognizes the same printed card as the
  placement trigger — then holds the object in place with real ARKit
  world tracking, independent of the card.
- **Android**: [Scene Viewer](https://developers.google.com/ar/develop/java/scene-viewer),
  triggered via `model-viewer`'s default `src`, loading `assets/model.glb`.
  Scene Viewer does full ARCore world tracking, but **does not support
  our custom card-image placement** — the user taps to place it on a
  detected floor plane instead. Full persistence, different placement
  gesture than iOS.
- Both are wired through [`<model-viewer>`](https://modelviewer.dev/)
  (`index.html`), Google's web component that auto-generates the correct
  platform-specific link/intent and falls back to WebXR or a plain 3D
  viewer where neither native path is available (e.g. desktop).

No app install either way — both are system-level viewers launched from
a normal web link.

**The old in-page MindAR experience still exists in [`legacy/`](legacy/)** —
useful if you ever want in-page camera + card tracking again (e.g. if
iOS Safari ships WebXR AR, or for the future pinch-to-scale variant),
but it has the disappearing-object limitation described above.

## ⚠️ Needs on-device verification: the .usdz image anchoring

`Preliminary_AnchoringAPI` (the schema that makes Quick Look recognize a
reference image) is an Apple/Pixar extension with **no full public spec**
— it's known only from Reality Composer's output and scattered WWDC
sessions/forum posts. `scripts/gen_usdz.py` hand-authors this based on
the best-documented syntax I could find, and there's no way to test an
actual Quick Look session outside a real iPhone, so this is unverified
in practice.

**First thing to test on-device.** If tapping "View in your space" on
iOS opens Quick Look but it does plane-detection (tap-to-place) instead
of recognizing the card, the anchoring block didn't take. Fallback: open
`assets/model.usdz` in Apple's free **Reality Composer** app (Mac App
Store), which has a proper GUI for setting an image anchor — rebuild the
box there and export, replacing `assets/model.usdz`. Everything else
(the `.glb` for Android, the `model-viewer` page) is unaffected by this.

## Files

| File | Purpose |
|---|---|
| `index.html` | Primary page — `model-viewer` + AR button |
| `assets/model.usdz` | iOS Quick Look model, image-anchored to `marker.png` |
| `assets/model.glb` | Android Scene Viewer model |
| `assets/marker.png` | Card artwork (cropped/resized from `assets/source/marker-source.jpg`) — **print this at exactly 7in × 7in** |
| `assets/marker.mind` | Compiled MindAR tracking data (used only by `legacy/`) |
| `scripts/gen_marker.py` | Regenerates `marker.png` |
| `assets/source/sthanam.glb` | Original supplied model — source of truth for the conversion below |
| `scripts/convert_glb.py` | Rescales `source/sthanam.glb` to 5ft and builds both `model.glb` and `model.usdz` (needs `pip install usd-core`) |
| `scripts/gen_usdz.py` | Original box-only usdz builder — reference/fallback, superseded by `convert_glb.py` |
| `scripts/gen_glb.mjs` | Original box-only glb builder — reference/fallback, superseded by `convert_glb.py` |
| `scripts/compile-marker.mjs` | Compiles a marker PNG into a `.mind` file (legacy only) |
| `scripts/prepare_marker_from_source.py` | Center-crops + resizes `assets/source/marker-source.jpg` to the 7in @ 300dpi spec |
| `assets/source/marker-source.jpg` | Original supplied card artwork before crop/resize |
| `legacy/` | The original in-page MindAR camera experience |

## Printing the card

Print `assets/marker.png` at **exactly 7in × 7in** (300 DPI, no
scale-to-fit) — full color, this is now the branded gold-on-maroon card
art (was a generated placeholder in earlier versions). Note: it's fairly
vertically symmetric with soft gradients rather than sharp edges, which
can track a little less robustly than a high-contrast asymmetric marker
— worth keeping an eye on during testing. The iOS anchoring in
`model.usdz` references this same file and its physical width (set in
`convert_glb.py`'s `MARKER_WIDTH_M`), so if you print at a different
size, update that and regenerate via `scripts/convert_glb.py`.

## Testing locally

```bash
npx http-server "AR Sthanam" -p 8935 -c-1
```

`http://localhost:8935` on this machine sanity-checks that the page
loads and the 3D preview renders (desktop browsers show `model-viewer`'s
plain 3D view since no AR mode is available there — that's expected, not
a bug). The AR button only appears where a real AR mode exists.

**To actually test AR**, you need a phone reaching an HTTPS URL — deploy
the folder to any static HTTPS host (Vercel, Netlify, GitHub Pages), or
use a tunnel (`npx localtunnel --port 8935`) for a quick check. This is
what you'll eventually point the QR code at.

On iOS Safari: tap "View in your space" → Quick Look opens → point at
the card → object should appear on the card and stay there as you walk
around, even out of the card's view. On Android Chrome: tap the button →
Scene Viewer opens → tap the floor to place → same persistence, but no
card recognition.

## Swapping in the final 3D model

Done for the current model (`assets/source/sthanam.glb`, from Blender's
glTF exporter) via `scripts/convert_glb.py` — it rescales the mesh to
exactly 5ft tall with the base at y=0 and writes both output files in one
pass, sharing the same scale calculation so Android and iOS match:

```bash
python3 -m pip install usd-core   # first time only
python3 scripts/convert_glb.py
```

- `assets/model.glb` — the source glb with vertex positions rescaled in
  place; textures/materials copied through byte-for-byte, untouched.
- `assets/model.usdz` — geometry, UVs, normals, and all three PBR
  textures (baseColor/normal/metallicRoughness) rebuilt as a proper USD
  `UsdPreviewSurface` material network, wrapped in the same
  image-anchoring metadata as before.

To swap in a **different** model later, replace
`assets/source/sthanam.glb` and re-run the script. It currently assumes
a single mesh/primitive, triangles, no Draco/KTX2 compression, and
POSITION/NORMAL/TEXCOORD_0 sharing one index buffer — true for a
straightforward single-mesh Blender export like this one. A more complex
source (multiple meshes, skinning, compressed textures) would need the
script extended, or exporting to `.glb`+`.usdz` from a tool that handles
both (Reality Composer, an online converter) instead.

**Note on size/performance**: the current model is ~500K triangles and
~42MB. That's on the heavy side for real-time mobile AR — Quick
Look/Scene Viewer will likely still load it, but possibly slowly on
older devices. If it feels sluggish on-device, the fix is decimating the
mesh (e.g. in Blender) before conversion, not something this script does
automatically.

## Swapping in final card artwork

1. Replace `assets/marker.png` with your branded design — high-contrast,
   detail-rich, and non-symmetric (a marker that looks the same rotated
   180° confuses recognition either way).
2. Update the physical width in `scripts/gen_usdz.py`
   (`MARKER_WIDTH_M`) if the new card isn't 7in, and re-run it.
3. If you still use `legacy/`, also recompile its tracking file:
   `node scripts/compile-marker.mjs`.

## Building the scale variant

Both Quick Look and Scene Viewer already support pinch-to-scale
natively in their own UI — nothing to build for that variant with this
architecture. (If you instead go back to the in-page `legacy/`
experience for some reason, see the scale-variant notes in
`legacy/config.js` / `legacy/app.js`.)

## Known limitations (v2)

- iOS card-anchored placement is unverified on real hardware (see
  warning above) — verify before relying on it.
- Android has no card-guided placement — floor tap only. If exact
  Android placement matters as much as it does on iOS, that likely
  means a paid WebAR SDK (e.g. 8th Wall) instead of this native-viewer
  approach — flagging as a possible future revisit.
- No fallback UI for very old browsers with neither AR mode nor WebGL.
