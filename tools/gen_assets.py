"""
gen_assets.py — 樱庭·离宫 程序化资产批量生成器（主入口）

用法：
    python tools/gen_assets.py [--outdir assets]

遍历各资产模块的 ASSETS 注册表，逐个构建并写出 glTF 2.0 Binary (.glb)，
所有资产共享同一张调色板纹理（内嵌于各 GLB），并输出 MANIFEST.sha256。

纯标准库，离线，确定性（同输入产出字节一致）。
规格来源：03_ArtAssetSpec_Procedural.md
"""

import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theseed_geo import (  # noqa: E402
    GltfDoc, Rng, derive_seed, build_palette_png, build_petal_alpha_png,
    count_triangles,
)
import theseed_flora   # noqa: E402
import theseed_props   # noqa: E402
import theseed_fx      # noqa: E402
import theseed_arch    # noqa: E402
import theseed_char    # noqa: E402

GENERATOR = "TheSeed gen_assets.py 0.1.0-alpha"

# 资产模块（顺序固定，保证可复现）
MODULES = [theseed_flora, theseed_props, theseed_fx, theseed_arch, theseed_char]


# --------------------------------------------------------------------------
# 材质定义（03_ArtAssetSpec_Procedural.md §3.2）
# --------------------------------------------------------------------------
# tex: "palette" | "petal"
MATERIAL_DEFS = {
    "M_Palette_Opaque":  {"tex": "palette", "metallic": 0.0,  "roughness": 0.85,
                          "alpha": "OPAQUE", "double": False},
    "M_Palette_Stone":   {"tex": "palette", "metallic": 0.0,  "roughness": 0.92,
                          "alpha": "OPAQUE", "double": False},
    "M_Palette_Wood":    {"tex": "palette", "metallic": 0.0,  "roughness": 0.78,
                          "alpha": "OPAQUE", "double": False},
    "M_Palette_Metal":   {"tex": "palette", "metallic": 0.65, "roughness": 0.42,
                          "alpha": "OPAQUE", "double": False},
    "M_Water":           {"tex": "palette", "metallic": 0.0,  "roughness": 0.12,
                          "alpha": "OPAQUE", "double": False},
    "M_Petal":           {"tex": "petal",   "metallic": 0.0,  "roughness": 0.70,
                          "alpha": "BLEND", "double": True},
    "M_Foliage_Cutout":  {"tex": "palette", "metallic": 0.0,  "roughness": 0.88,
                          "alpha": "OPAQUE", "double": True},
    "M_Lantern_Glow":    {"tex": "palette", "metallic": 0.0,  "roughness": 1.0,
                          "alpha": "OPAQUE", "double": False,
                          "emissive": (0.96, 0.85, 0.66), "emissive_strength": 2.0},
    "M_Crystal_Glow":    {"tex": "palette", "metallic": 0.0,  "roughness": 0.20,
                          "alpha": "OPAQUE", "double": True,
                          "emissive": (0.56, 0.83, 0.91), "emissive_strength": 2.5},
    "M_Fog":             {"tex": "palette", "metallic": 0.0,  "roughness": 1.0,
                          "alpha": "BLEND", "double": True},
    "M_Sky":             {"tex": "palette", "metallic": 0.0,  "roughness": 1.0,
                          "alpha": "OPAQUE", "double": True},
}


def collect_assets():
    """汇总所有模块的 ASSETS，检查 ID 唯一。返回 {aid: (spec, module_name)}。"""
    all_assets = {}
    for mod in MODULES:
        for aid, spec in mod.ASSETS.items():
            if aid in all_assets:
                raise ValueError("重复资产 ID: %s (in %s)" % (aid, mod.__name__))
            all_assets[aid] = (spec, mod.__name__)
    return all_assets


def make_matfn(doc, pal_tex, petal_holder, petal_png):
    """返回 matfn(name) -> material index。按需 lazy 内嵌花瓣纹理。"""
    cache = {}

    def matfn(name):
        if name in cache:
            return cache[name]
        defn = MATERIAL_DEFS.get(name)
        if defn is None:
            raise ValueError("未定义材质: %s" % name)
        if defn["tex"] == "petal":
            if petal_holder[0] is None:
                img = doc.add_image(petal_png, "T_Petal_Alpha.png")
                petal_holder[0] = doc.add_texture(img, "T_Petal_Alpha")
            tex = petal_holder[0]
        else:
            tex = pal_tex
        emissive = defn.get("emissive", (0.0, 0.0, 0.0))
        idx = doc.add_material(
            name, base_tex=tex, metallic=defn["metallic"], roughness=defn["roughness"],
            emissive=emissive, emissive_strength=1.0,  # factor 保持 0-1 合规
            alpha_mode=defn["alpha"], double_sided=defn["double"],
        )
        # 发光强度意图存入 extras，供引擎导入脚本读取（标准 emissiveFactor 已 clamp）
        if emissive and defn.get("emissive_strength", 1.0) != 1.0:
            doc.materials[idx]["extras"] = {
                "emissive_strength": defn["emissive_strength"],
                "emissive_color": list(emissive),
            }
        cache[name] = idx
        return idx
    return matfn


def _reload_doc(glb):
    """从 GLB 字节回读 gltf dict（用于统计面数，确保统计的是写出内容）。"""
    import json
    import struct
    off = 12
    js = None
    while off + 8 <= len(glb):
        clen, ctype = struct.unpack("<II", glb[off:off + 8])
        if ctype == 0x4E4F534A:
            js = json.loads(glb[off + 8:off + 8 + clen].decode("utf-8"))
            break
        off += 8 + clen
    return js


def main(argv):
    outdir = "assets"
    if "--outdir" in argv:
        outdir = argv[argv.index("--outdir") + 1]
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(root_dir, outdir, "models")
    tex_dir = os.path.join(root_dir, outdir, "textures")
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(tex_dir, exist_ok=True)

    pal_png = build_palette_png()
    petal_png = build_petal_alpha_png(64)

    # 独立输出两张纹理 PNG，供引擎侧直接引用
    with open(os.path.join(tex_dir, "T_Palette.png"), "wb") as f:
        f.write(pal_png)
    with open(os.path.join(tex_dir, "T_Petal_Alpha.png"), "wb") as f:
        f.write(petal_png)

    all_assets = collect_assets()
    manifest = []
    total_tris = 0
    total_bytes = 0
    over_budget = []

    print("生成 %d 个资产 -> %s" % (len(all_assets), models_dir))
    print("%-26s %-28s %8s %8s %8s" % ("资产ID", "文件", "面数", "预算", "字节"))
    for aid in sorted(all_assets):
        spec, mod = all_assets[aid]
        glb = build_one_glb_bytes(aid, spec, pal_png, petal_png)
        d = _reload_doc(glb)
        tris = count_triangles(d)
        total_tris += tris
        total_bytes += len(glb)
        budget = spec["tri_budget"]
        flag = ""
        if tris > budget:
            over_budget.append((aid, tris, budget))
            flag = "  <-- 超预算!"
        path = os.path.join(models_dir, spec["file"])
        with open(path, "wb") as f:
            f.write(glb)
        sha = hashlib.sha256(glb).hexdigest()
        manifest.append("%s  %s  %d" % (sha, spec["file"], len(glb)))
        print("%-26s %-28s %8d %8d %8d%s" % (
            aid, spec["file"], tris, budget, len(glb), flag))

    # 写 MANIFEST（排序保证可复现）
    manifest.sort(key=lambda x: x.split("  ")[1])
    man_path = os.path.join(root_dir, outdir, "MANIFEST.sha256")
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# TheSeed 樱庭·离宫 资产清单 (sha256  文件名  字节数)\n")
        f.write("# generator: %s\n" % GENERATOR)
        for line in manifest:
            f.write(line + "\n")

    print("-" * 82)
    print("资产数: %d | 面数合计: %d | 字节合计: %d (%.1f KB)" % (
        len(all_assets), total_tris, total_bytes, total_bytes / 1024))
    print("MANIFEST: %s" % man_path)
    if over_budget:
        print("!! 超面数预算 %d 项:" % len(over_budget))
        for aid, t, b in over_budget:
            print("   %s: %d > %d" % (aid, t, b))
        return 1
    print("全部资产在面数预算内。")
    return 0


def build_one_glb_bytes(aid, spec, pal_png, petal_png):
    """构建单个资产 GLB 字节（独立函数，供 main 调用）。"""
    doc = GltfDoc()
    pal_img = doc.add_image(pal_png, "T_Palette.png")
    pal_tex = doc.add_texture(pal_img, "T_Palette")
    petal_holder = [None]
    matfn = make_matfn(doc, pal_tex, petal_holder, petal_png)
    ctx = {"rng": Rng(derive_seed(aid)), "asset_id": aid}
    if spec.get("skinned"):
        root = spec["assemble"](doc, ctx, pal_tex, matfn)
    else:
        parts = spec["build"](ctx)
        prims = [(mesh, matfn(matname)) for mesh, matname in parts if not mesh.is_empty()]
        mesh_idx = doc.add_mesh(spec["file"].replace(".glb", ""), prims)
        root = doc.add_node(aid, mesh=mesh_idx)
    doc.scene_nodes.append(root)
    return doc.build(generator=GENERATOR)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
