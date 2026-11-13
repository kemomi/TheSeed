"""
gen_scene_layout.py — 樱庭·离宫 场景布局生成器

产出引擎无关的 SceneLayout_SakuraTeien.json，把 43 个资产实例化到 8 个分区。
本文件是坐标的机器可读权威来源（见 02_LevelDesign_Hakoniwa.md §10）。

用法：
    python tools/gen_scene_layout.py [--out <path>]

坐标系：右手系 +X东 +Y北 +Z上，单位米。
确定性：所有随机用固定 seed，同输入产出字节一致。
"""

import os
import sys
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from theseed_geo import Rng, derive_seed  # noqa: E402

VERSION = "0.1.0-alpha"
SCENE_SEED = derive_seed("scene_sakura_teien")

# --------------------------------------------------------------------------
# 分区定义（02_LevelDesign_Hakoniwa.md §2）
# --------------------------------------------------------------------------
ZONES = [
    {"id": "zone_torii_approach", "name_cn": "鸟居参道", "shape": "rect",
     "size": [4.0, 14.0], "center": [0.0, -17.0, 0.0], "safe": True,
     "petal_density": 0.3, "wind_deg": 180.0, "navmesh": False, "ground_z": 0.0},
    {"id": "zone_tea_stall", "name_cn": "茶摊", "shape": "rect",
     "size": [5.0, 6.0], "center": [-7.0, -13.0, 0.0], "safe": True,
     "petal_density": 0.4, "wind_deg": 180.0, "navmesh": False, "ground_z": 0.0},
    {"id": "zone_kyobashi", "name_cn": "镜池·太鼓桥", "shape": "circle",
     "size": [7.4], "center": [0.0, 0.0, -0.3], "safe": True,
     "petal_density": 1.0, "wind_deg": 315.0, "navmesh": False, "ground_z": -0.3},
    {"id": "zone_azumaya", "name_cn": "樱亭", "shape": "rect",
     "size": [7.0, 7.0], "center": [11.0, 3.0, 0.45], "safe": True,
     "petal_density": 0.7, "wind_deg": 315.0, "navmesh": False, "ground_z": 0.45},
    {"id": "zone_karesansui", "name_cn": "枯山水", "shape": "rect",
     "size": [11.0, 10.0], "center": [-13.0, -3.0, 0.0], "safe": True,
     "petal_density": 0.5, "wind_deg": 270.0, "navmesh": False, "ground_z": 0.0},
    {"id": "zone_ishidoro_path", "name_cn": "石灯笼小径", "shape": "rect",
     "size": [4.0, 13.0], "center": [-6.0, 12.0, 0.3], "safe": True,
     "petal_density": 0.4, "wind_deg": 0.0, "navmesh": True, "ground_z": 0.3},
    {"id": "zone_sakura_grove", "name_cn": "樱花林", "shape": "circle",
     "size": [7.0], "center": [3.0, 14.0, 0.6], "safe": False,
     "petal_density": 0.8, "wind_deg": 0.0, "navmesh": True, "ground_z": 0.6},
    {"id": "zone_okunomori", "name_cn": "奥之森", "shape": "circle",
     "size": [7.0], "center": [-2.0, 28.0, 1.2], "safe": False,
     "petal_density": 0.2, "wind_deg": 0.0, "navmesh": True, "ground_z": 1.2},
]
ZONE_BY_ID = {z["id"]: z for z in ZONES}


def _r3(v):
    return round(float(v), 3)


def inst(aid, x, y, z, rot=0.0, scale=1.0, zone=None, collision="box",
         tags=None, destructible=False, rng=None, jitter=0.0):
    """构造一个实例字典。rot 为绕 Z（上）轴度数。jitter 做水平微抖动。"""
    if rng is not None and jitter > 0:
        x += rng.range(-jitter, jitter)
        y += rng.range(-jitter, jitter)
        rot += rng.range(-jitter * 4, jitter * 4)
    s = [scale, scale, scale] if isinstance(scale, (int, float)) else list(scale)
    d = {
        "id": None,  # 由 assign_ids 填充
        "asset": aid,
        "zone": zone or _guess_zone(x, y),
        "position": [_r3(x), _r3(y), _r3(z)],
        "rotation_deg": [_r3(rot) if rot else 0.0, 0.0, 0.0],
        "scale": [_r3(s[0]), _r3(s[1]), _r3(s[2])],
        "collision": collision,
        "destructible": bool(destructible),
        "tags": list(tags or []),
    }
    # 旋转约定：JSON 用 [rz, ry, rx]，本场景只用 rz（绕上轴），故写在第 0 位
    return d


def _guess_zone(x, y):
    """按坐标落到最近的分区（用于未显式指定 zone 的实例）。"""
    best = None
    bestd = 1e18
    for z in ZONES:
        cx, cy = z["center"][0], z["center"][1]
        d = math.hypot(x - cx, y - cy)
        if d < bestd:
            bestd = d
            best = z["id"]
    return best


# --------------------------------------------------------------------------
# 各分区摆放配方
# --------------------------------------------------------------------------

def layout_torii_approach(rng):
    """鸟居参道：主鸟居（南入口）+ 两侧石灯笼 + 石板 + 边界竹林。"""
    out = []
    # 主鸟居：位于参道南端，面朝北（玩家从南进入）
    out.append(inst("asset_torii_main", 0.0, -22.0, 0.0, rot=0.0,
                    zone="zone_torii_approach", tags=["landmark", "boundary_south", "spawn_gate"]))
    # 参道两侧石板地面
    for k in range(7):
        y = -22.0 + k * 2.0
        out.append(inst("asset_ground_tile", 0.0, y, 0.0, rot=0.0,
                        zone="zone_torii_approach", collision="none", tags=["path"]))
    # 两侧石灯笼（春日型），交替
    for k in range(4):
        y = -20.0 + k * 3.0
        for sx in (-1, 1):
            out.append(inst("asset_ishidoro_tall", sx * 1.7, y, 0.0,
                            zone="zone_torii_approach", collision="cylinder",
                            destructible=True, tags=["lantern", "lightable"]))
    # 边界竹林（东西两侧密集）
    for k in range(5):
        y = -23.0 + k * 3.0
        for sx in (-1, 1):
            out.append(inst("asset_bamboo_cluster", sx * 3.2, y, 0.0, rng=rng, jitter=0.3,
                            zone="zone_torii_approach", collision="none", tags=["boundary"]))
    # 参道起点樱花树（框景）
    for sx in (-1, 1):
        out.append(inst("asset_sakura_tree_mid", sx * 3.0, -14.0, 0.0,
                        zone="zone_torii_approach", collision="cylinder", tags=["framing"]))
    # 记录结晶（支线 quest_pond_crystal 的引子，漂浮于参道尽头）
    out.append(inst("asset_crystal_record", 0.0, -10.5, 0.9,
                    zone="zone_torii_approach", collision="none", tags=["pickup", "quest_pond_crystal"]))
    return out


def layout_tea_stall(rng):
    """茶摊：摊位建筑 + 团子 + 灌木 + 灯笼。NPC 三乃在此。"""
    out = []
    out.append(inst("asset_tea_stall", -7.0, -13.0, 0.0, rot=0.0,
                    zone="zone_tea_stall", collision="box", tags=["building", "shop"]))
    # 团子道具（柜台展示）
    out.append(inst("asset_item_dango", -7.0, -14.2, 1.0, zone="zone_tea_stall",
                    collision="none", tags=["shop_item", "item_sakura_dango"]))
    # 周围球形灌木
    for (bx, by) in [(-9.3, -11.0), (-4.7, -11.0), (-9.3, -15.0)]:
        out.append(inst("asset_bush_round", bx, by, 0.0, rng=rng, jitter=0.1,
                        zone="zone_tea_stall", collision="cylinder", tags=["decor"]))
    # 一株小樱花树
    out.append(inst("asset_sakura_tree_small", -4.6, -15.2, 0.0,
                    zone="zone_tea_stall", collision="cylinder", tags=["decor"]))
    # 苔藓片
    out.append(inst("asset_moss_patch", -8.5, -12.0, 0.01, zone="zone_tea_stall",
                    collision="none", tags=["decor"]))
    return out


def layout_kyobashi(rng):
    """镜池·太鼓桥：水面 + 拱桥 + 鹿威し + 环池石组 + 樱花林 + 樱花最密。"""
    out = []
    # 水面（圆心即世界原点）
    out.append(inst("asset_water_surface", 0.0, 0.0, -0.25, zone="zone_kyobashi",
                    collision="box", tags=["water", "pond"]))
    # 太鼓桥：南北横跨池面
    out.append(inst("asset_kyobashi", 0.0, 0.0, -0.25, rot=0.0,
                    zone="zone_kyobashi", collision="box", tags=["bridge", "landmark"]))
    # 鹿威し：池东南岸
    out.append(inst("asset_shishiodoshi", 4.2, 3.0, 0.0, zone="zone_kyobashi",
                    collision="cylinder", tags=["shishiodoshi", "sound_trigger"]))
    # 环池石组
    stone_spots = [(-5.0, -3.0), (5.2, -2.5), (-4.5, 4.0), (5.5, 3.5), (0.0, -6.0)]
    for i, (sx, sy) in enumerate(stone_spots):
        aid = "asset_rock_cluster_a" if i % 2 == 0 else "asset_rock_cluster_b"
        out.append(inst(aid, sx, sy, -0.1, rng=rng, jitter=0.2,
                        zone="zone_kyobashi", collision="cylinder", tags=["rock"]))
    # 环池樱花树（大树，视觉核心）
    for ang_deg in range(0, 360, 45):
        a = math.radians(ang_deg)
        r = 6.4
        x, y = math.cos(a) * r, math.sin(a) * r
        aid = "asset_sakura_tree_large" if ang_deg % 90 == 0 else "asset_sakura_tree_mid"
        out.append(inst(aid, x, y, -0.1, rng=rng, jitter=0.3,
                        zone="zone_kyobashi", collision="cylinder", tags=["sakura_ring"]))
    # 手水钵（桥北端）
    out.append(inst("asset_chozubachi", 1.5, 5.5, 0.0, zone="zone_kyobashi",
                    collision="cylinder", tags=["decor"]))
    # 草丛点缀
    for k in range(6):
        a = rng.range(0, 2 * math.pi)
        rr = rng.range(4.5, 6.8)
        out.append(inst("asset_grass_tuft", math.cos(a) * rr, math.sin(a) * rr, 0.0,
                        zone="zone_kyobashi", collision="none", tags=["grass"]))
    return out


def layout_azumaya(rng):
    """樱亭：凉亭 + 观景樱花 + 石灯笼 + 苔。NPC 椿在此（存档）。"""
    out = []
    # 樱亭主体，地台高 0.45，台阶朝南（-Y）
    out.append(inst("asset_azumaya", 11.0, 3.0, 0.0, rot=0.0,
                    zone="zone_azumaya", collision="box", tags=["building", "save_point", "viewpoint"]))
    # 亭周樱花树
    for (tx, ty) in [(7.0, 6.0), (14.5, 5.5), (13.5, -0.5), (7.5, 0.0)]:
        out.append(inst("asset_sakura_tree_large", tx, ty, 0.0, rng=rng, jitter=0.25,
                        zone="zone_azumaya", collision="cylinder", tags=["sakura"]))
    # 亭前石灯笼（一对）
    for sx in (-1, 1):
        out.append(inst("asset_ishidoro_tall", 11.0 + sx * 2.6, -1.0, 0.0,
                        zone="zone_azumaya", collision="cylinder",
                        destructible=True, tags=["lantern", "lightable"]))
    # 独樱（对景物，从亭中北望）
    out.append(inst("asset_sakura_solo", 13.0, 8.0, 0.0, zone="zone_azumaya",
                    collision="cylinder", tags=["solo_sakura", "taikei"]))
    # 灌木与苔
    for (bx, by) in [(8.0, 1.0), (14.0, 2.0)]:
        out.append(inst("asset_bush_round", bx, by, 0.0, zone="zone_azumaya",
                        collision="cylinder", tags=["decor"]))
    out.append(inst("asset_moss_patch", 9.5, 4.5, 0.46, zone="zone_azumaya",
                    collision="none", tags=["decor"]))
    return out


def layout_karesansui(rng):
    """枯山水：耙纹砂地（frame 自带）+ 黑松 + 缘侧 + 手水钵 + 石灯笼。NPC 源藏在此。"""
    out = []
    # 枯山水主体（11×10，自带砂、主石、围石、缘侧）
    out.append(inst("asset_karesansui_frame", -13.0, -3.0, 0.0, rot=0.0,
                    zone="zone_karesansui", collision="box", tags=["karesansui", "landmark"]))
    # 黑松（枯山水经典搭配）
    for (px, py) in [(-17.5, -6.5), (-8.5, -6.0), (-17.0, 0.5)]:
        out.append(inst("asset_pine_black", px, py, 0.0, rng=rng, jitter=0.2,
                        zone="zone_karesansui", collision="cylinder", tags=["pine"]))
    # 石灯笼（矮款，置于砂地边）
    out.append(inst("asset_ishidoro_short", -9.0, -1.0, 0.0, zone="zone_karesansui",
                    collision="cylinder", destructible=True, tags=["lantern", "lightable"]))
    out.append(inst("asset_ishidoro_short", -16.5, -2.5, 0.0, zone="zone_karesansui",
                    collision="cylinder", destructible=True, tags=["lantern", "lightable"]))
    # 手水钵
    out.append(inst("asset_chozubachi", -8.0, 0.5, 0.0, zone="zone_karesansui",
                    collision="cylinder", tags=["decor"]))
    # 石组点缀
    out.append(inst("asset_rock_single", -11.0, -7.0, 0.0, rng=rng, jitter=0.15,
                    zone="zone_karesansui", collision="cylinder", tags=["rock"]))
    # 苔藓
    for k in range(3):
        out.append(inst("asset_moss_patch", -14.0 + k * 1.5, 1.0, 0.01,
                        zone="zone_karesansui", collision="none", tags=["decor"]))
    return out


def layout_ishidoro_path(rng):
    """石灯笼小径：沿路石灯笼（支线点亮对象）+ 飞石 + 竹 + 过渡樱花。NPC 枫在此巡逻。"""
    out = []
    # 小径沿 Y 从 5.5 到 18.5，中线 x=-6
    ys = [6.0 + k * 1.8 for k in range(8)]
    for i, y in enumerate(ys):
        # 交替左右放灯笼（支线 quest_lantern_lighting 的 7 盏对象）
        sx = -1 if i % 2 == 0 else 1
        aid = "asset_ishidoro_tall" if i % 3 != 2 else "asset_ishidoro_short"
        out.append(inst(aid, -6.0 + sx * 1.4, y, 0.3, zone="zone_ishidoro_path",
                        collision="cylinder", destructible=True,
                        tags=["lantern", "lightable", "quest_lantern_lighting"]))
    # 飞石汀步（踏脚路径）
    for i, y in enumerate(ys):
        out.append(inst("asset_stepping_stone", -6.0 + (0.3 if i % 2 else -0.3), y, 0.3,
                        rot=rng.range(-15, 15), zone="zone_ishidoro_path",
                        collision="none", tags=["path"]))
    # 两侧竹林（收束视线，营造过渡感）
    for i, y in enumerate(ys):
        for sx in (-1, 1):
            if (i + (0 if sx > 0 else 1)) % 2 == 0:
                out.append(inst("asset_bamboo_cluster", -6.0 + sx * 2.6, y, 0.3,
                                rng=rng, jitter=0.2, zone="zone_ishidoro_path",
                                collision="none", tags=["bamboo", "boundary"]))
    # 樱花树（过渡，越往北越少）
    for (tx, ty) in [(-9.0, 7.0), (-3.0, 9.0), (-9.5, 13.0)]:
        out.append(inst("asset_sakura_tree_mid", tx, ty, 0.3, rng=rng, jitter=0.2,
                        zone="zone_ishidoro_path", collision="cylinder", tags=["sakura"]))
    # 独樱（对景物：从南端望见樱花林深处）
    out.append(inst("asset_sakura_solo", -3.0, 17.0, 0.3, zone="zone_ishidoro_path",
                    collision="cylinder", tags=["solo_sakura", "taikei"]))
    return out


def layout_sakura_grove(rng):
    """樱花林：首次战斗区。密集大樱花树 + 呼应石 + 敌人生成点。"""
    out = []
    # 环形密集樱花林（大林在外围，中心留出战斗空地）
    for ang_deg in range(0, 360, 40):
        a = math.radians(ang_deg)
        r = rng.range(5.0, 6.6)
        x, y = 3.0 + math.cos(a) * r, 14.0 + math.sin(a) * r
        out.append(inst("asset_sakura_tree_large", x, y, 0.6, rng=rng, jitter=0.3,
                        zone="zone_sakura_grove", collision="cylinder", tags=["grove"]))
    # 中心独樱（战斗场地焦点）
    out.append(inst("asset_sakura_solo", 3.0, 14.0, 0.6, zone="zone_sakura_grove",
                    collision="cylinder", tags=["center_sakura"]))
    # 呼应石（3 处，供切换系统拉近队友距离，见 02 §9）
    for (cx, cy) in [(1.0, 12.0), (5.0, 12.5), (3.0, 17.0)]:
        out.append(inst("asset_calling_stone", cx, cy, 0.6, zone="zone_sakura_grove",
                        collision="cylinder", tags=["calling_stone", "switch_anchor"]))
    # 石组与灌木
    for (rx, ry) in [(0.5, 16.0), (5.5, 16.5), (6.0, 11.5)]:
        out.append(inst("asset_rock_cluster_a", rx, ry, 0.6, rng=rng, jitter=0.2,
                        zone="zone_sakura_grove", collision="cylinder", tags=["rock"]))
    # 草丛（战斗区地面细节）
    for k in range(8):
        a = rng.range(0, 2 * math.pi)
        rr = rng.range(1.5, 6.0)
        out.append(inst("asset_grass_tuft", 3.0 + math.cos(a) * rr, 14.0 + math.sin(a) * rr,
                        0.6, zone="zone_sakura_grove", collision="none", tags=["grass"]))
    return out


def layout_okunomori(rng):
    """奥之森：区域守卫战。冷调、樱花稀少、黑松、小鸟居、高台、绯甲武者。"""
    out = []
    # 小鸟居（奥之森入口，标志进入危险区）
    out.append(inst("asset_torii_small", -2.0, 22.0, 1.0, zone="zone_okunomori",
                    collision="box", tags=["boundary", "danger_gate"]))
    # 黑松（冷调针叶，替代樱花）
    for ang_deg in range(0, 360, 51):
        a = math.radians(ang_deg)
        r = rng.range(5.2, 6.8)
        x, y = -2.0 + math.cos(a) * r, 28.0 + math.sin(a) * r
        out.append(inst("asset_pine_black", x, y, 1.2, rng=rng, jitter=0.3,
                        zone="zone_okunomori", collision="cylinder", tags=["pine", "cold"]))
    # 仅 1 株樱花（凋零感，与樱花林对比）
    out.append(inst("asset_sakura_tree_small", -5.0, 30.0, 1.2, zone="zone_okunomori",
                    collision="cylinder", tags=["withering"]))
    # 中央高台（绯甲武者驻守，居高临下）
    out.append(inst("asset_rock_cluster_b", -2.0, 28.0, 1.15, scale=1.3,
                    zone="zone_okunomori", collision="cylinder", tags=["boss_platform"]))
    # 呼应石
    for (cx, cy) in [(-4.0, 26.0), (0.5, 26.5), (-2.0, 31.0)]:
        out.append(inst("asset_calling_stone", cx, cy, 1.2, zone="zone_okunomori",
                        collision="cylinder", tags=["calling_stone", "switch_anchor"]))
    # 石灯笼（倾倒/熄灭，营造荒废感）
    out.append(inst("asset_ishidoro_tall", -5.5, 24.0, 1.1, rot=18.0,
                    zone="zone_okunomori", collision="cylinder", destructible=True,
                    tags=["lantern", "ruined"]))
    # 石组
    for (rx, ry) in [(1.5, 30.5), (-5.0, 27.0)]:
        out.append(inst("asset_rock_single", rx, ry, 1.2, rng=rng, jitter=0.15,
                        zone="zone_okunomori", collision="cylinder", tags=["rock"]))
    return out


# --------------------------------------------------------------------------
# 全局元素（灯光、天空、雾、NPC、敌人、出生点、volume）
# --------------------------------------------------------------------------

def global_instances(rng):
    """跨分区的全局实例：天空、雾、边界树。"""
    out = []
    out.append(inst("asset_sky_dome", 0.0, 0.0, 0.0, zone=None, collision="none",
                    tags=["sky", "global"]))
    # 边界雾环（4 组交叉雾片，围住整个区域）
    for ang_deg in range(0, 360, 45):
        a = math.radians(ang_deg)
        r = 30.0
        out.append(inst("asset_fog_plane", math.cos(a) * r, math.sin(a) * r, 0.0,
                        rot=ang_deg, scale=[1.0, 1.0, 1.0], zone=None,
                        collision="none", tags=["fog", "boundary"]))
    return out


def build_lights():
    return [
        {"id": "sun_main", "type": "directional", "rotation_deg": [-52.0, 0.0, 38.0],
         "color": [1.0, 0.95, 0.88], "energy": 1.15, "shadow": True,
         "shadow_resolution": 2048, "note": "午后偏西主光；安全区暖调"},
        {"id": "sun_okunomori_fill", "type": "directional", "rotation_deg": [-48.0, 0.0, 200.0],
         "color": [0.62, 0.70, 0.80], "energy": 0.55, "shadow": False,
         "shadow_resolution": 0, "note": "奥之森冷调补光，仅照亮 zone_okunomori/grove"},
        {"id": "ambient_sky", "type": "ambient", "color": [0.72, 0.74, 0.80], "energy": 0.35,
         "note": "天空环境光"},
        {"id": "lantern_glow_pool", "type": "omni_group", "color": [0.96, 0.85, 0.66],
         "energy": 0.9, "radius": 1.5, "count_limit": 6,
         "note": "石灯笼假光源：仅最近的 6 盏启用 OmniLight，其余靠自发光材质（见 01 §2.3）"},
    ]


def build_npc_placements():
    """NPC 摆放（ID 与 04_NPC_System.md 一致）。"""
    return [
        {"id": "npc_mino", "name_cn": "三乃", "role": "tea_stall",
         "zone": "zone_tea_stall", "position": [-7.0, -13.6, 0.0], "rotation_deg": 10.0,
         "asset": "asset_npc_base", "variant": "mino", "interactable": True,
         "note": "茶摊少女，商店；idle/talk/wave"},
        {"id": "npc_tsubaki", "name_cn": "椿", "role": "shrine_maiden",
         "zone": "zone_azumaya", "position": [11.0, 3.0, 0.45], "rotation_deg": 180.0,
         "asset": "asset_npc_base", "variant": "tsubaki", "interactable": True,
         "note": "巫女，存档点+记录结晶；idle/bow/talk"},
        {"id": "npc_genzo", "name_cn": "源藏", "role": "stonemason",
         "zone": "zone_karesansui", "position": [-16.0, -3.0, 0.0], "rotation_deg": 90.0,
         "asset": "asset_npc_base", "variant": "genzo", "interactable": True,
         "note": "石匠，装备强化+支线；sit/idle/talk；坐于缘侧凿石"},
        {"id": "npc_kaede", "name_cn": "枫", "role": "garden_guard",
         "zone": "zone_ishidoro_path", "position": [-6.0, 12.0, 0.3], "rotation_deg": 0.0,
         "asset": "asset_npc_base", "variant": "kaede", "interactable": True,
         "note": "樱守，巡逻+支线'点亮七盏石灯笼'；walk/idle/talk；手提灯笼"},
        {"id": "npc_busho", "name_cn": "绯甲武者", "role": "area_guardian",
         "zone": "zone_okunomori", "position": [-2.0, 28.0, 1.35], "rotation_deg": 180.0,
         "asset": "asset_enemy_hikabusho", "variant": "busho", "interactable": True,
         "hostile": True, "note": "奥之森守卫，敌对但战前可对话；guard/idle/attack"},
    ]


def build_spawners():
    """敌人刷新（ID 与 07_Combat_Design.md、DT_Enemy_SakuraTeien.csv 一致）。"""
    return [
        {"id": "spawn_grove_oni_grunt", "zone": "zone_sakura_grove",
         "enemy": "enemy_sakura_oni_grunt", "count": 3, "respawn_sec": 90, "max_alive": 3,
         "positions": [[1.5, 13.0, 0.6], [4.5, 15.0, 0.6], [2.5, 16.5, 0.6]],
         "first_entry_fixed": True, "note": "首次进入固定刷新（教学战）"},
        {"id": "spawn_grove_oni_blade", "zone": "zone_sakura_grove",
         "enemy": "enemy_sakura_oni_blade", "count": 1, "respawn_sec": 120, "max_alive": 1,
         "positions": [[3.0, 12.0, 0.6]],
         "unlock_condition": "player_level>=5", "note": "玩家 5 级后加入刷新池"},
        {"id": "spawn_okunomori_busho", "zone": "zone_okunomori",
         "enemy": "enemy_hikabuto_busho", "count": 1, "respawn_sec": 300, "max_alive": 1,
         "positions": [[-2.0, 28.0, 1.35]],
         "note": "区域守卫，击杀后 5 分钟重刷"},
        {"id": "spawn_okunomori_oni_blade", "zone": "zone_okunomori",
         "enemy": "enemy_sakura_oni_blade", "count": 2, "respawn_sec": 150, "max_alive": 2,
         "positions": [[-4.0, 27.0, 1.2], [0.5, 29.0, 1.2]],
         "linked_to": "spawn_okunomori_busho", "note": "与绯甲武者同时激活"},
    ]


def build_spawn_points():
    """玩家出生点与传送锚点。"""
    return [
        {"id": "player_spawn_main", "zone": "zone_torii_approach",
         "position": [0.0, -20.0, 0.0], "rotation_deg": 0.0,
         "note": "主出生点，鸟居内、面朝北"},
        {"id": "teleport_from_town", "zone": "zone_torii_approach",
         "position": [0.0, -21.0, 0.0], "rotation_deg": 0.0,
         "note": "起始之镇传送门落点"},
    ]


def build_volumes():
    """触发体：安全区、交战域、雾、传送。"""
    return [
        {"id": "vol_safe_torii", "type": "safe_zone", "zone": "zone_torii_approach",
         "combat_enabled": False},
        {"id": "vol_safe_tea", "type": "safe_zone", "zone": "zone_tea_stall",
         "combat_enabled": False},
        {"id": "vol_safe_kyobashi", "type": "safe_zone", "zone": "zone_kyobashi",
         "combat_enabled": False},
        {"id": "vol_safe_azumaya", "type": "safe_zone", "zone": "zone_azumaya",
         "combat_enabled": False},
        {"id": "vol_safe_karesansui", "type": "safe_zone", "zone": "zone_karesansui",
         "combat_enabled": False},
        {"id": "vol_combat_domain", "type": "combat_domain",
         "zones": ["zone_ishidoro_path", "zone_sakura_grove", "zone_okunomori"],
         "combat_enabled": True,
         "note": "三交战区合并为单一 Combat Domain，切换距离按玩家实际坐标判定（见 02 §9）"},
        {"id": "vol_boundary_fog", "type": "fog", "shape": "ring",
         "inner_radius": 26.0, "outer_radius": 34.0, "density": 1.0,
         "note": "边界雾，靠近 2m 内线性升浓；物理墙位于雾中"},
        {"id": "vol_combat_music", "type": "audio_trigger",
         "zones": ["zone_sakura_grove", "zone_okunomori"],
         "on_enter": "bgm_battle_start", "on_exit": "bgm_battle_fadeout_6s"},
        {"id": "vol_okunomori_cold", "type": "color_grade_trigger", "zone": "zone_okunomori",
         "note": "进入奥之森色温转冷（α 阶段靠 sun_okunomori_fill 补光实现，不用后处理）"},
    ]


def build_petal_emitters():
    """樱吹雪发射器（每分区一个，密度见 02 §7）。"""
    emitters = []
    for z in ZONES:
        cx, cy = z["center"][0], z["center"][1]
        if z["shape"] == "circle":
            rad = z["size"][0]
            shape, dims = "cylinder", [rad, rad, 8.0]
        else:
            shape, dims = "box", [z["size"][0], z["size"][1], 8.0]
        emitters.append({
            "id": "petal_" + z["id"], "zone": z["id"], "shape": shape,
            "center": [_r3(cx), _r3(cy), _r3(z["ground_z"] + 4.0)],
            "dimensions": [_r3(dims[0]), _r3(dims[1]), _r3(dims[2])],
            "density": z["petal_density"], "wind_deg": z["wind_deg"],
            "lifetime_sec": [6.0, 9.0], "ground_fade_sec": 12.0,
            "combat_suppress_factor": 0.4,
            "note": "交战中密度×0.4，脱战 4s 恢复（见 02 §7）",
        })
    return emitters


# --------------------------------------------------------------------------
# 组装
# --------------------------------------------------------------------------

def assign_ids(instances):
    """为实例分配稳定 ID：<asset短名>_<序号>，按出现顺序，保证可复现。"""
    counter = {}
    for d in instances:
        base = d["asset"].replace("asset_", "")
        counter[base] = counter.get(base, 0) + 1
        d["id"] = "%s_%03d" % (base, counter[base])
    return instances


def build_layout():
    rng = Rng(SCENE_SEED)
    instances = []
    for fn in (layout_torii_approach, layout_tea_stall, layout_kyobashi,
               layout_azumaya, layout_karesansui, layout_ishidoro_path,
               layout_sakura_grove, layout_okunomori, global_instances):
        instances.extend(fn(rng))
    instances = assign_ids(instances)

    doc = {
        "meta": {
            "name": "LV_SakuraTeien_Main",
            "version": VERSION,
            "unit": "meter",
            "coordinate": "right-handed, +Y=north, +X=east, +Z=up",
            "generator": "tools/gen_scene_layout.py",
            "source_of_truth": "02_LevelDesign_Hakoniwa.md",
            "seed": SCENE_SEED,
            "engine_adapters": {
                "godot": "godot_pos = (x, z, -y)",
                "unreal": "ue_pos = (x*100, y*100, z*100)  # 1m=100uu, left-handed +Z up",
                "unity": "unity_pos = (x, z, y)",
            },
        },
        "zones": ZONES,
        "instances": instances,
        "lights": build_lights(),
        "npc_placements": build_npc_placements(),
        "spawners": build_spawners(),
        "spawn_points": build_spawn_points(),
        "volumes": build_volumes(),
        "petal_emitters": build_petal_emitters(),
    }
    return doc


def main(argv):
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_out = os.path.join(root_dir, "The-Seed-Link-Future", "SAO_GameDesign",
                               "SakuraTeien", "SceneLayout_SakuraTeien.json")
    out_path = default_out
    if "--out" in argv:
        out_path = argv[argv.index("--out") + 1]

    doc = build_layout()

    # 校验：所有 instance.asset 必须在已生成资产清单内
    from gen_assets import collect_assets
    known = set(collect_assets().keys())
    missing = sorted({d["asset"] for d in doc["instances"]} - known)
    if missing:
        print("!! 引用了未生成的资产:", missing)
        return 1

    text = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=False)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")

    # 统计
    from collections import Counter
    zone_count = Counter(d["zone"] for d in doc["instances"] if d["zone"])
    asset_count = Counter(d["asset"] for d in doc["instances"])
    print("场景布局已写出:", out_path)
    print("实例总数:", len(doc["instances"]))
    print("分区数:", len(doc["zones"]), "| 灯光:", len(doc["lights"]),
          "| NPC:", len(doc["npc_placements"]), "| 刷新器:", len(doc["spawners"]),
          "| volume:", len(doc["volumes"]), "| 花瓣发射器:", len(doc["petal_emitters"]))
    print("\n各分区实例数:")
    for z in ZONES:
        print("  %-22s %3d" % (z["id"], zone_count.get(z["id"], 0)))
    print("\n资产使用频次（前 12）:")
    for aid, n in asset_count.most_common(12):
        print("  %-30s %3d" % (aid, n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
