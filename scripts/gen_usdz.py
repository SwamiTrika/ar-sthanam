"""
Builds a placeholder box as a USDZ with Apple's image-anchoring metadata
(Preliminary_AnchoringAPI), so AR Quick Look on iOS recognizes the same
printed marker card and anchors the box to it — then holds the box in
place via ARKit's own device tracking (real world-lock), independent of
whether the card stays in frame.

NOTE: Preliminary_AnchoringAPI is not part of the open-source USD spec —
it's an Apple/Pixar extension undocumented outside Reality Composer's
output and scattered WWDC sessions. This script authors the raw USD text
using the best publicly-documented syntax available. It has NOT been
verified against a real Quick Look session (no way to do that outside
iOS). Test this on an actual iPhone before relying on it — if the
placement gesture doesn't trigger, rebuilding the anchoring block with
Apple's free Reality Composer app (drag in a box, set Image anchor,
export) is the reliable fallback.
"""
import os
import shutil
import zipfile
from pxr import UsdUtils

ROOT = "/Volumes/DT022/coding-space/Claude Code/AR Sthanam"
ASSETS = os.path.join(ROOT, "assets")
WORK = os.path.join(ROOT, ".usdz-build")

FEET_TO_M = 0.3048
HEIGHT_M = 5 * FEET_TO_M            # 1.524
FOOTPRINT_M = 1.5 * FEET_TO_M       # 0.4572
HALF = FOOTPRINT_M / 2
MARKER_WIDTH_M = 7 * 0.0254         # 0.1778 (7in card)

# 8 box corners, Y-up, base at y=0.
P = {
    "lbb": (-HALF, 0, -HALF), "rbb": (HALF, 0, -HALF),
    "rbt": (HALF, 0, HALF),   "lbt": (-HALF, 0, HALF),
    "ltb": (-HALF, HEIGHT_M, -HALF), "rtb": (HALF, HEIGHT_M, -HALF),
    "rtt": (HALF, HEIGHT_M, HALF),   "ltt": (-HALF, HEIGHT_M, HALF),
}

def v(name):
    x, y, z = P[name]
    return f"({x:.6f}, {y:.6f}, {z:.6f})"

points = ", ".join(v(n) for n in ["lbb", "rbb", "rbt", "lbt", "ltb", "rtb", "rtt", "ltt"])

# 6 quad faces, outward winding (CCW viewed from outside, Y-up right-handed).
faces = [
    [0, 1, 2, 3],  # bottom
    [4, 7, 6, 5],  # top
    [0, 4, 5, 1],  # -Z side
    [1, 5, 6, 2],  # +X side
    [2, 6, 7, 3],  # +Z side
    [3, 7, 4, 0],  # -X side
]
normals_by_face = [
    (0, -1, 0), (0, 1, 0), (0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0),
]

face_vertex_indices = ", ".join(str(i) for f in faces for i in f)
face_vertex_counts = ", ".join("4" for _ in faces)
normals = ", ".join(f"({nx}, {ny}, {nz})" for (nx, ny, nz) in normals_by_face for _ in range(4))

usda = f'''#usda 1.0
(
    defaultPrim = "Sthanam"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "Sthanam" (
    prepend apiSchemas = ["Preliminary_AnchoringAPI"]
)
{{
    uniform token preliminary:anchoring:type = "image"
    rel preliminary:anchoring:referenceImage = <ReferenceImage>
    rel preliminary:imageAnchoring:referenceImage = <ReferenceImage>

    def Preliminary_ReferenceImage "ReferenceImage"
    {{
        uniform asset image = @markers/marker.png@
        uniform double physicalWidth = {MARKER_WIDTH_M:.6f}
    }}

    def Mesh "Box"
    {{
        uniform bool doubleSided = false
        int[] faceVertexCounts = [{face_vertex_counts}]
        int[] faceVertexIndices = [{face_vertex_indices}]
        point3f[] points = [{points}]
        normal3f[] primvars:normals = [{normals}] (
            interpolation = "faceVarying"
        )
        color3f[] primvars:displayColor = [(0.18, 0.53, 0.91)]
        uniform token subdivisionScheme = "none"
    }}
}}
'''

def main():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(os.path.join(WORK, "markers"))

    usda_path = os.path.join(WORK, "sthanam.usda")
    with open(usda_path, "w") as f:
        f.write(usda)

    shutil.copy(os.path.join(ASSETS, "marker.png"), os.path.join(WORK, "markers", "marker.png"))

    out_path = os.path.join(ASSETS, "model.usdz")
    if os.path.exists(out_path):
        os.remove(out_path)

    ok = UsdUtils.CreateNewARKitUsdzPackage(usda_path, out_path)
    if not ok:
        raise SystemExit("CreateNewARKitUsdzPackage reported failure")

    print("wrote", out_path, os.path.getsize(out_path), "bytes")

    with zipfile.ZipFile(out_path) as z:
        print("contents:", z.namelist())

if __name__ == "__main__":
    main()
