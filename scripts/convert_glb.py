"""
Converts a user-supplied glTF binary (.glb) — single mesh, single
PBR material, up to 3 baked textures (baseColor / normal /
metallicRoughness) — into the two files the app actually ships:

  assets/model.glb   Rescaled copy of the source, for Android Scene Viewer.
  assets/model.usdz   Same geometry/materials rebuilt in USD, plus Apple's
                      image-anchoring metadata, for iOS Quick Look.

Both are rescaled uniformly so the model is exactly TARGET_HEIGHT_M tall
with its base at y=0 — matching how the placeholder box was sized, so the
swap is drop-in.

Assumes: single mesh/primitive, TRIANGLES mode, tightly-packed accessors
(no byteStride), POSITION/NORMAL/TEXCOORD_0 sharing one index buffer —
true for straightforward single-mesh Blender glTF exports like this one.
A more complex source (multiple meshes/nodes, skinning, Draco/KTX2
compression) would need a fancier converter — this one intentionally
doesn't try to handle those.
"""
import json
import os
import struct
import numpy as np
from pxr import Usd, UsdGeom, UsdShade, Sdf, Vt

ROOT = "/Volumes/DT022/coding-space/Claude Code/AR Sthanam"
ASSETS = os.path.join(ROOT, "assets")
SRC_GLB = os.path.join(ASSETS, "source", "sthanam.glb")
WORK = os.path.join(ROOT, ".usdz-build-model")

FEET_TO_M = 0.3048
TARGET_HEIGHT_M = 5 * FEET_TO_M
MARKER_WIDTH_M = 7 * 0.0254

COMPONENT_DTYPES = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", "not a .glb file"
    offset = 12
    chunks = {}
    while offset < length:
        chunk_len, chunk_type = struct.unpack_from("<I4s", data, offset)
        chunk_data = data[offset + 8: offset + 8 + chunk_len]
        chunks[chunk_type] = chunk_data
        offset += 8 + chunk_len
    gltf = json.loads(chunks[b"JSON"])
    bin_data = chunks.get(b"BIN\x00", b"")
    return gltf, bin_data


def read_accessor(gltf, bin_data, accessor_index):
    acc = gltf["accessors"][accessor_index]
    bv = gltf["bufferViews"][acc["bufferView"]]
    assert "byteStride" not in bv, "strided buffer views not supported by this converter"
    dtype = COMPONENT_DTYPES[acc["componentType"]]
    n_comp = TYPE_COUNTS[acc["type"]]
    count = acc["count"]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    arr = np.frombuffer(bin_data, dtype=dtype, count=count * n_comp, offset=start)
    return arr.reshape(count, n_comp) if n_comp > 1 else arr.reshape(count)


def main():
    gltf, bin_data = read_glb(SRC_GLB)
    prim = gltf["meshes"][0]["primitives"][0]
    assert prim.get("mode", 4) == 4, "expected TRIANGLES primitive"

    positions = read_accessor(gltf, bin_data, prim["attributes"]["POSITION"]).astype(np.float32)
    normals = read_accessor(gltf, bin_data, prim["attributes"]["NORMAL"]).astype(np.float32)
    uvs = read_accessor(gltf, bin_data, prim["attributes"]["TEXCOORD_0"]).astype(np.float32)
    indices = read_accessor(gltf, bin_data, prim["indices"]).astype(np.uint32)

    min_y, max_y = positions[:, 1].min(), positions[:, 1].max()
    scale = TARGET_HEIGHT_M / (max_y - min_y)
    positions_scaled = positions * scale
    positions_scaled[:, 1] -= positions_scaled[:, 1].min()  # base at y=0

    print(f"source: {len(positions):,} verts, {len(indices)//3:,} triangles")
    print(f"source height: {(max_y - min_y):.4f} units -> scale factor {scale:.5f} -> {TARGET_HEIGHT_M:.4f} m")

    # --- 1. Android: rescaled copy of the original glb, textures untouched ---
    write_rescaled_glb(gltf, bin_data, prim, positions_scaled)

    # --- 2. iOS: rebuilt as USD with image-anchoring ---
    write_usdz(gltf, bin_data, positions_scaled, normals, uvs, indices)


def write_rescaled_glb(gltf, bin_data, prim, positions_scaled):
    pos_acc_idx = prim["attributes"]["POSITION"]
    acc = gltf["accessors"][pos_acc_idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    n_floats = acc["count"] * 3

    new_bin = bytearray(bin_data)
    new_bin[start:start + n_floats * 4] = positions_scaled.astype(np.float32).tobytes()

    acc["min"] = [float(v) for v in positions_scaled.min(axis=0)]
    acc["max"] = [float(v) for v in positions_scaled.max(axis=0)]

    json_bytes = json.dumps(gltf).encode("utf-8")
    json_pad = (-len(json_bytes)) % 4
    json_bytes += b" " * json_pad

    bin_bytes = bytes(new_bin)
    bin_pad = (-len(bin_bytes)) % 4
    bin_bytes += b"\x00" * bin_pad

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    out_path = os.path.join(ASSETS, "model.glb")
    with open(out_path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        f.write(json_bytes)
        f.write(struct.pack("<I4s", len(bin_bytes), b"BIN\x00"))
        f.write(bin_bytes)
    print("wrote", out_path, os.path.getsize(out_path), "bytes")


def extract_image(gltf, bin_data, image_index, out_path):
    img = gltf["images"][image_index]
    bv = gltf["bufferViews"][img["bufferView"]]
    start = bv.get("byteOffset", 0)
    length = bv["byteLength"]
    with open(out_path, "wb") as f:
        f.write(bin_data[start:start + length])


def write_usdz(gltf, bin_data, positions, normals, uvs, indices):
    if os.path.exists(WORK):
        import shutil
        shutil.rmtree(WORK)
    os.makedirs(os.path.join(WORK, "textures"))
    os.makedirs(os.path.join(WORK, "markers"))

    material = gltf["materials"][0]
    textures = gltf["textures"]

    def image_path_for(tex_ref, filename):
        tex = textures[tex_ref["index"]]
        image_index = tex["source"]
        out = os.path.join(WORK, "textures", filename)
        extract_image(gltf, bin_data, image_index, out)
        return f"textures/{filename}"

    diffuse_rel = image_path_for(material["pbrMetallicRoughness"]["baseColorTexture"], "diffuse.png")
    normal_rel = image_path_for(material["normalTexture"], "normal.png")
    mr_rel = image_path_for(material["pbrMetallicRoughness"]["metallicRoughnessTexture"], "metallicRoughness.png")

    import shutil as _sh
    _sh.copy(os.path.join(ASSETS, "marker.png"), os.path.join(WORK, "markers", "marker.png"))

    usda_path = os.path.join(WORK, "sthanam.usda")
    stage = Usd.Stage.CreateNew(usda_path)
    stage.SetMetadata("metersPerUnit", 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    root = stage.DefinePrim("/Sthanam", "Xform")
    root.SetMetadata("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["Preliminary_AnchoringAPI"]))
    root.CreateAttribute("preliminary:anchoring:type", Sdf.ValueTypeNames.Token, custom=False).Set("image")
    ref_img = stage.DefinePrim("/Sthanam/ReferenceImage", "Preliminary_ReferenceImage")
    ref_img.CreateAttribute("image", Sdf.ValueTypeNames.Asset, custom=False).Set("markers/marker.png")
    ref_img.CreateAttribute("physicalWidth", Sdf.ValueTypeNames.Double, custom=False).Set(MARKER_WIDTH_M)
    root.CreateRelationship("preliminary:anchoring:referenceImage", custom=False).SetTargets(["/Sthanam/ReferenceImage"])
    root.CreateRelationship("preliminary:imageAnchoring:referenceImage", custom=False).SetTargets(["/Sthanam/ReferenceImage"])

    mesh = UsdGeom.Mesh.Define(stage, "/Sthanam/Model")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(positions))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(indices.astype(np.int32)))
    n_tris = len(indices) // 3
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(n_tris, 3, dtype=np.int32)))
    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(normals))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(False)

    uvs_flipped = uvs.copy()
    uvs_flipped[:, 1] = 1.0 - uvs_flipped[:, 1]  # glTF V-down -> USD V-up
    st_primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex
    )
    st_primvar.Set(Vt.Vec2fArray.FromNumpy(uvs_flipped))

    mat = UsdShade.Material.Define(stage, "/Sthanam/Materials/ModelMaterial")
    surface = UsdShade.Shader.Define(stage, "/Sthanam/Materials/ModelMaterial/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float)
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float)
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
    surface.CreateInput("normal", Sdf.ValueTypeNames.Normal3f)
    mat.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")

    st_reader = UsdShade.Shader.Define(stage, "/Sthanam/Materials/ModelMaterial/StReader")
    st_reader.CreateIdAttr("UsdPrimvarReader_float2")
    st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    st_out = st_reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    def make_tex(name, rel_path, out_channels, colorspace):
        tex = UsdShade.Shader.Define(stage, f"/Sthanam/Materials/ModelMaterial/{name}")
        tex.CreateIdAttr("UsdUVTexture")
        tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(rel_path)
        tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(colorspace)
        tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st_out)
        outputs = {}
        for ch in out_channels:
            outputs[ch] = tex.CreateOutput(ch, Sdf.ValueTypeNames.Float if ch != "rgb" else Sdf.ValueTypeNames.Float3)
        return tex, outputs

    diffuse_tex, diffuse_out = make_tex("DiffuseTexture", diffuse_rel, ["rgb"], "sRGB")
    surface.GetInput("diffuseColor").ConnectToSource(diffuse_tex.ConnectableAPI(), "rgb")

    mr_tex, mr_out = make_tex("MetallicRoughnessTexture", mr_rel, ["g", "b"], "raw")
    surface.GetInput("roughness").ConnectToSource(mr_tex.ConnectableAPI(), "g")
    surface.GetInput("metallic").ConnectToSource(mr_tex.ConnectableAPI(), "b")

    normal_tex, normal_out = make_tex("NormalTexture", normal_rel, ["rgb"], "raw")
    normal_tex.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set((2.0, 2.0, 2.0, 1.0))
    normal_tex.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set((-1.0, -1.0, -1.0, 0.0))
    surface.GetInput("normal").ConnectToSource(normal_tex.ConnectableAPI(), "rgb")

    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat)

    stage.SetDefaultPrim(root)
    stage.GetRootLayer().Save()

    from pxr import UsdUtils
    out_path = os.path.join(ASSETS, "model.usdz")
    if os.path.exists(out_path):
        os.remove(out_path)
    ok = UsdUtils.CreateNewARKitUsdzPackage(usda_path, out_path)
    if not ok:
        raise SystemExit("CreateNewARKitUsdzPackage reported failure")
    print("wrote", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    main()
