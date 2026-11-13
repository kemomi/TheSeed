"""
validate_assets.py — 樱庭·离宫 交叉校验器（α 阶段质量门）

交叉核对三个独立来源，防止文档、数据表与产物脱节：
  A 资产层：GLB 存在/结构合法/面数≤预算/确定性/skinned 蒙皮合法/MANIFEST 一致
  B 场景层：SceneLayout 引用有效/字段合规/ID 唯一/坐标合法
  C 数据表层：CSV 编码合规(UTF-8 无 BOM,LF)/表头逐字匹配/外键
  D 一致性层：DT_NPC/DT_Enemy ↔ SceneLayout ↔ 资产清单 三方交叉

任一 FAIL 则 exit 1（构建失败）。用法：
    python tools/validate_assets.py
"""

import os
import sys
import json
import csv
import hashlib
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from theseed_geo import read_glb, count_triangles            # noqa: E402
from theseed_char import BONES                               # noqa: E402
from gen_assets import (collect_assets, build_one_glb_bytes, # noqa: E402
                        build_palette_png, build_petal_alpha_png)

SAKURA = os.path.join(ROOT, "The-Seed-Link-Future", "SAO_GameDesign", "SakuraTeien")
ASSETS_DIR = os.path.join(ROOT, "assets")
MODELS_DIR = os.path.join(ASSETS_DIR, "models")
DT_DIR = os.path.join(SAKURA, "DataTables")
SCENE_JSON = os.path.join(SAKURA, "SceneLayout_SakuraTeien.json")
MANIFEST = os.path.join(ASSETS_DIR, "MANIFEST.sha256")

EXPECT_VERSION = "0.1.0-alpha"

# 期望表头（逐字，来自 04 §7 / 07 §8 / 00 §3.3）
EXPECT_HEADERS = {
    "DT_NPC_SakuraTeien.csv": [
        "npc_id", "name_cn", "name_romaji", "role", "zone_id", "hostile",
        "asset_variant", "prop_asset", "anim_set", "interact_radius_m",
        "greet_radius_m", "default_affinity", "shop_id", "service_id", "dialogue_root"],
    "DT_Enemy_SakuraTeien.csv": [
        "enemy_id", "name_cn", "type", "zone_id", "hp", "attack", "defense",
        "move_speed", "attack_range_m", "aggro_radius_m", "hit_stop_s",
        "exp_reward", "asset_mesh", "anim_set", "behavior_tree", "can_dodge", "drops"],
    "DT_EnemyAttacks_SakuraTeien.csv": [
        "attack_id", "enemy_id", "name_cn", "phase", "windup_s", "damage",
        "range_m", "shape", "interruptible", "cooldown_s", "anim_ref", "notes"],
}

RESULTS = []


def check(group, ok, msg):
    RESULTS.append((group, bool(ok), msg))
    return bool(ok)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


# ==========================================================================
# A 资产层
# ==========================================================================

def validate_assets(all_assets, pal_png, petal_png):
    g = "A 资产"
    # MANIFEST 解析
    man = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("  ")
                if len(parts) == 3:
                    man[parts[1]] = (parts[0], int(parts[2]))
    else:
        check(g, False, "MANIFEST.sha256 不存在")

    n_ok = 0
    for aid in sorted(all_assets):
        spec, _mod = all_assets[aid]
        fname = spec["file"]
        path = os.path.join(MODELS_DIR, fname)
        if not os.path.exists(path):
            check(g, False, "缺文件: %s" % fname)
            continue
        with open(path, "rb") as f:
            glb = f.read()
        # 结构合法
        try:
            doc, binlen, total = read_glb(path)
        except Exception as e:
            check(g, False, "%s 结构非法: %s" % (fname, e))
            continue
        # 面数 ≤ 预算
        tris = count_triangles(doc)
        if tris > spec["tri_budget"]:
            check(g, False, "%s 超面数 %d>%d" % (fname, tris, spec["tri_budget"]))
            continue
        # 确定性：重新 build 比对 sha256
        regen = build_one_glb_bytes(aid, spec, pal_png, petal_png)
        if sha256_bytes(regen) != sha256_bytes(glb):
            check(g, False, "%s 非确定性（重新生成 sha 不一致）" % fname)
            continue
        # MANIFEST 一致
        if fname in man:
            m_sha, m_bytes = man[fname]
            if m_sha != sha256_bytes(glb) or m_bytes != len(glb):
                check(g, False, "%s 与 MANIFEST 不符" % fname)
                continue
        else:
            check(g, False, "%s 不在 MANIFEST" % fname)
            continue
        # skinned 蒙皮合法性
        if spec.get("skinned"):
            if not _validate_skin(doc, path, fname):
                continue
        n_ok += 1
    check(g, n_ok == len(all_assets),
          "资产完整 %d/%d（结构/面数/确定性/MANIFEST/蒙皮）" % (n_ok, len(all_assets)))


def _validate_skin(doc, path, fname):
    g = "A 资产"
    nbone = len(BONES)
    if not doc.get("skins"):
        return check(g, False, "%s skinned 但无 skin" % fname)
    skin = doc["skins"][0]
    if len(skin.get("joints", [])) != nbone:
        return check(g, False, "%s 骨骼数 %d≠%d" % (fname, len(skin.get("joints", [])), nbone))
    ibm_idx = skin.get("inverseBindMatrices", -1)
    if ibm_idx < 0 or doc["accessors"][ibm_idx]["count"] != nbone:
        return check(g, False, "%s IBM 数≠%d" % (fname, nbone))
    # 读 bin 校验权重和 + 计数一致
    with open(path, "rb") as f:
        blob = f.read()
    binbytes = _extract_bin(blob)
    for prim in doc["meshes"][0]["primitives"]:
        at = prim["attributes"]
        if "POSITION" not in at:
            return check(g, False, "%s primitive 无 POSITION" % fname)
        pc = doc["accessors"][at["POSITION"]]["count"]
        for key in ("JOINTS_0", "WEIGHTS_0"):
            if key not in at:
                return check(g, False, "%s 缺 %s" % (fname, key))
            if doc["accessors"][at[key]]["count"] != pc:
                return check(g, False, "%s %s 计数≠POSITION" % (fname, key))
        wacc = doc["accessors"][at["WEIGHTS_0"]]
        bv = doc["bufferViews"][wacc["bufferView"]]
        bo = bv["byteOffset"] + wacc.get("byteOffset", 0)
        for vi in range(wacc["count"]):
            w = struct.unpack("<ffff", binbytes[bo + vi * 16: bo + vi * 16 + 16])
            if abs(sum(w) - 1.0) > 0.02:
                return check(g, False, "%s 顶点 %d 权重和=%.3f≠1" % (fname, vi, sum(w)))
    # 动画 target 节点有效
    for an in doc.get("animations", []):
        for ch in an["channels"]:
            if ch["target"]["node"] >= len(doc["nodes"]):
                return check(g, False, "%s 动画 target 越界" % fname)
    return True


def _extract_bin(blob):
    off = 12
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        if ctype == 0x004E4942:
            return blob[off + 8: off + 8 + clen]
        off += 8 + clen
    return b""


# ==========================================================================
# B 场景层
# ==========================================================================

def validate_scene(all_assets, zones_expect=8):
    g = "B 场景"
    if not os.path.exists(SCENE_JSON):
        return check(g, False, "SceneLayout JSON 不存在"), None
    with open(SCENE_JSON, "r", encoding="utf-8") as f:
        doc = json.load(f)
    known_assets = set(all_assets.keys())
    ok = True
    ok &= check(g, doc.get("meta", {}).get("version") == EXPECT_VERSION,
                "meta.version == %s" % EXPECT_VERSION)
    zones = doc.get("zones", [])
    zone_ids = {z["id"] for z in zones}
    ok &= check(g, len(zones) == zones_expect, "分区数 == %d（实际 %d）" % (zones_expect, len(zones)))

    insts = doc.get("instances", [])
    req = {"id", "asset", "zone", "position", "rotation_deg", "scale", "collision", "destructible", "tags"}
    ids = []
    bad_field = bad_asset = bad_zone = bad_pos = 0
    for i in insts:
        ids.append(i.get("id"))
        if set(i.keys()) != req:
            bad_field += 1
        if i.get("asset") not in known_assets:
            bad_asset += 1
        if i.get("zone") not in zone_ids and i.get("zone") is not None:
            bad_zone += 1
        p = i.get("position")
        if not (isinstance(p, list) and len(p) == 3 and all(isinstance(x, (int, float)) for x in p)):
            bad_pos += 1
    ok &= check(g, bad_field == 0, "实例字段完整（异常 %d）" % bad_field)
    ok &= check(g, bad_asset == 0, "实例 asset 引用有效（无效 %d）" % bad_asset)
    ok &= check(g, bad_zone == 0, "实例 zone 引用有效（无效 %d）" % bad_zone)
    ok &= check(g, bad_pos == 0, "实例 position 三元合规（异常 %d）" % bad_pos)
    ok &= check(g, len(ids) == len(set(ids)), "实例 ID 唯一（%d/%d）" % (len(set(ids)), len(ids)))

    # npc_placements / spawners 引用
    for np in doc.get("npc_placements", []):
        if np.get("asset") not in known_assets:
            ok &= check(g, False, "npc_placement %s asset 无效" % np.get("id"))
        if np.get("zone") not in zone_ids:
            ok &= check(g, False, "npc_placement %s zone 无效" % np.get("id"))
    for sp in doc.get("spawners", []):
        if sp.get("zone") not in zone_ids:
            ok &= check(g, False, "spawner %s zone 无效" % sp.get("id"))
    check(g, ok, "SceneLayout 结构合规（实例 %d）" % len(insts))
    return ok, doc


# ==========================================================================
# C 数据表层
# ==========================================================================

def _read_csv_bytes(fname):
    path = os.path.join(DT_DIR, fname)
    with open(path, "rb") as f:
        return f.read()


def validate_datatables():
    g = "C 数据表"
    tables = {}
    for fname, expect in EXPECT_HEADERS.items():
        path = os.path.join(DT_DIR, fname)
        if not os.path.exists(path):
            check(g, False, "缺数据表: %s" % fname)
            continue
        raw = _read_csv_bytes(fname)
        # 编码：UTF-8 无 BOM
        no_bom = not raw.startswith(b"\xef\xbb\xbf")
        # 行尾：LF，无 CR
        no_cr = b"\r" not in raw
        # 可 UTF-8 解码
        try:
            text = raw.decode("utf-8")
            decodable = True
        except UnicodeDecodeError:
            decodable = False
            text = ""
        ok = no_bom and no_cr and decodable
        check(g, ok, "%s 编码合规（无BOM=%s LF=%s 可解码=%s）" % (fname, no_bom, no_cr, decodable))
        if not decodable:
            continue
        rows = list(csv.reader(text.splitlines()))
        if not rows:
            check(g, False, "%s 空表" % fname)
            continue
        header = rows[0]
        check(g, header == expect, "%s 表头逐字匹配（%d 列）" % (fname, len(expect)))
        # 列数一致
        bad_cols = [i for i, r in enumerate(rows[1:], 2) if len(r) != len(expect)]
        check(g, not bad_cols, "%s 各行列数一致（异常行 %s）" % (fname, bad_cols[:5]))
        tables[fname] = [dict(zip(header, r)) for r in rows[1:]]
    return tables


# ==========================================================================
# D 一致性层
# ==========================================================================

def validate_consistency(all_assets, scene_doc, tables):
    g = "D 一致性"
    if scene_doc is None or not tables:
        return check(g, False, "缺少场景或数据表，跳过一致性校验")
    known_assets = set(all_assets.keys())
    zone_ids = {z["id"] for z in scene_doc.get("zones", [])}
    ok = True

    npc_rows = tables.get("DT_NPC_SakuraTeien.csv", [])
    enemy_rows = tables.get("DT_Enemy_SakuraTeien.csv", [])
    atk_rows = tables.get("DT_EnemyAttacks_SakuraTeien.csv", [])

    # 1. DT_NPC.npc_id 集合 == SceneLayout.npc_placements.id 集合
    dt_npc_ids = {r["npc_id"] for r in npc_rows}
    sl_npc_ids = {np["id"] for np in scene_doc.get("npc_placements", [])}
    ok &= check(g, dt_npc_ids == sl_npc_ids,
                "DT_NPC ↔ SceneLayout NPC ID 一致（%d）" % len(dt_npc_ids))

    # 2. DT_NPC.zone_id 都在 zones
    bad = [r["npc_id"] for r in npc_rows if r["zone_id"] not in zone_ids]
    ok &= check(g, not bad, "DT_NPC.zone_id 全部有效（异常 %s）" % bad)

    # 3. DT_NPC.prop_asset（非空）在资产清单
    bad = [r["npc_id"] for r in npc_rows if r["prop_asset"] and r["prop_asset"] not in known_assets]
    ok &= check(g, not bad, "DT_NPC.prop_asset 全部有效（异常 %s）" % bad)

    # 4. SceneLayout.npc_placements.variant ⊆ DT_NPC.asset_variant
    dt_variants = {r["asset_variant"] for r in npc_rows}
    sl_variants = {np.get("variant") for np in scene_doc.get("npc_placements", [])}
    ok &= check(g, sl_variants <= dt_variants,
                "SceneLayout variant ⊆ DT_NPC（缺 %s）" % (sl_variants - dt_variants))

    # 5. SceneLayout.npc_placements.asset 在资产清单
    bad = [np["id"] for np in scene_doc.get("npc_placements", []) if np.get("asset") not in known_assets]
    ok &= check(g, not bad, "npc_placements.asset 全部有效（异常 %s）" % bad)

    # 6. hostile 一致（DT_NPC.hostile vs SceneLayout）
    dt_hostile = {r["npc_id"]: r["hostile"] == "true" for r in npc_rows}
    for np in scene_doc.get("npc_placements", []):
        sl_h = bool(np.get("hostile", False))
        if dt_hostile.get(np["id"]) != sl_h:
            ok &= check(g, False, "hostile 不一致: %s" % np["id"])

    # 7. DT_Enemy.enemy_id ⊇ SceneLayout.spawners.enemy
    dt_enemy_ids = {r["enemy_id"] for r in enemy_rows}
    sl_spawn_enemies = {sp["enemy"] for sp in scene_doc.get("spawners", [])}
    ok &= check(g, sl_spawn_enemies <= dt_enemy_ids,
                "spawner.enemy ⊆ DT_Enemy（缺 %s）" % (sl_spawn_enemies - dt_enemy_ids))

    # 8. DT_Enemy.asset_mesh 在资产清单
    bad = [r["enemy_id"] for r in enemy_rows if r["asset_mesh"] not in known_assets]
    ok &= check(g, not bad, "DT_Enemy.asset_mesh 全部有效（异常 %s）" % bad)

    # 9. DT_Enemy.zone_id 都在 zones
    bad = [r["enemy_id"] for r in enemy_rows if r["zone_id"] not in zone_ids]
    ok &= check(g, not bad, "DT_Enemy.zone_id 全部有效（异常 %s）" % bad)

    # 10. DT_EnemyAttacks.enemy_id 都在 DT_Enemy
    bad = [r["attack_id"] for r in atk_rows if r["enemy_id"] not in dt_enemy_ids]
    ok &= check(g, not bad, "DT_EnemyAttacks.enemy_id 外键有效（异常 %s）" % bad)

    # 11. SceneLayout.spawners.zone 都在 zones
    bad = [sp["id"] for sp in scene_doc.get("spawners", []) if sp.get("zone") not in zone_ids]
    ok &= check(g, not bad, "spawner.zone 全部有效（异常 %s）" % bad)

    check(g, ok, "跨源一致性（NPC %d / Enemy %d / Attack %d）" % (
        len(npc_rows), len(enemy_rows), len(atk_rows)))
    return ok


# ==========================================================================
# 主流程
# ==========================================================================

def main():
    print("=" * 66)
    print("樱庭·离宫 交叉校验器  v%s" % EXPECT_VERSION)
    print("=" * 66)
    all_assets = collect_assets()
    pal_png = build_palette_png()
    petal_png = build_petal_alpha_png(64)

    validate_assets(all_assets, pal_png, petal_png)
    _ok, scene_doc = validate_scene(all_assets)
    tables = validate_datatables()
    validate_consistency(all_assets, scene_doc, tables)

    # 汇总
    print()
    groups = {}
    for g, ok, msg in RESULTS:
        groups.setdefault(g, []).append((ok, msg))
    total = len(RESULTS)
    passed = sum(1 for _g, ok, _m in RESULTS if ok)
    for g in sorted(groups):
        items = groups[g]
        gpass = sum(1 for ok, _ in items if ok)
        print("\n【%s】 %d/%d" % (g, gpass, len(items)))
        for ok, msg in items:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", msg))

    print("\n" + "=" * 66)
    failed = total - passed
    print("校验项合计 %d | PASS %d | FAIL %d" % (total, passed, failed))
    if failed:
        print("结果：FAILED — 构建门未通过")
        return 1
    print("结果：ALL PASS — α 质量门通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
