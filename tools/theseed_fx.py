"""
theseed_fx.py — 樱庭·离宫 特效与道具资产（9 个）

坐标系：右手系 +X东 +Y北 +Z上，单位=米。
"""

import math
from theseed_geo import Mesh, tint_height


# ──────────────────────────────────────────────────────────────────────
# B1  樱花花瓣  2面  budget 2
# ──────────────────────────────────────────────────────────────────────

def build_petal(ctx):
    """单片樱花花瓣：1 个四边形 double=True → 4 三角面。
    但预算为 2 面，所以用 double=False 得 2 三角。
    引擎侧 M_Petal 材质已设双面渲染。"""
    rng = ctx["rng"]
    m = Mesh("SakuraPetal", "sakura")
    # 约 3cm × 2.5cm 的花瓣形状四边形
    hw = 0.012  # 半宽
    hh = 0.015  # 半高
    # 略带弧度的四顶点
    p0 = (-hw, -hh, 0.0)
    p1 = (hw, -hh * 0.8, 0.0)
    p2 = (hw * 0.7, hh, 0.0)
    p3 = (-hw * 0.6, hh * 0.9, 0.0)
    m.quad(p0, p1, p2, p3, color="sakura", double=False)
    return [(m, "M_Petal")]


# ──────────────────────────────────────────────────────────────────────
# B2  地面瓦片  2×2m  seg 4×4  budget 64
# ──────────────────────────────────────────────────────────────────────

def build_ground_tile(ctx):
    rng = ctx["rng"]
    m = Mesh("GroundTile", "grass")
    # 4×4 seg → 32 三角面（双面不需要，地面只朝上）
    # 用顶点色区分参道石板与草地
    # 中心区域用 tile 色，边缘用 grass 色
    m.plane((0, 0, 0), 2.0, 2.0, seg_x=4, seg_y=4, color="grass", normal="z")
    # 对中心区域的顶点重新着色为 tile
    for i, p in enumerate(m.pos):
        if abs(p[0]) < 0.5 and abs(p[1]) < 0.5:
            from theseed_geo import palette_uv_center
            m.col[i] = (1.0, 1.0, 1.0)  # tint 白色让调色板采样 tile 色
            m.uv[i] = palette_uv_center("tile")
    return [(m, "M_Palette_Opaque")]


# ──────────────────────────────────────────────────────────────────────
# B3  镜池水面  16×16 seg  budget 800
# ──────────────────────────────────────────────────────────────────────

def build_water_surface(ctx):
    rng = ctx["rng"]
    m = Mesh("WaterSurface", "water")
    # 16×16 seg → 512 三角面
    m.plane((0, 0, 0), 6.0, 6.0, seg_x=16, seg_y=16, color="water", normal="z")
    return [(m, "M_Water")]


# ──────────────────────────────────────────────────────────────────────
# B4  边界雾片  4 面片十字交叉  budget 8
# ──────────────────────────────────────────────────────────────────────

def build_fog_plane(ctx):
    """4 个大面片十字交叉。
    注意：M_Fog 材质用顶点色亮度表达透明度（COLOR_0 alpha 恒为 1），
    底部亮度 1.0（不透明）→ 顶部亮度 0.0（全透明）。
    真实 alpha 混合在引擎侧材质里处理。"""
    rng = ctx["rng"]
    m = Mesh("FogPlane", "white_robe")

    def fog_tint(p):
        """从底部(z=0)到顶部(z=3)渐变"""
        z = p[2]
        t = max(0.0, min(1.0, z / 3.0))
        return 1.0 - t  # 底亮顶暗

    # 4 片面，每片 1 quad double=False → 2 tri，共 8 tri
    # M_Fog 材质在引擎侧已设双面渲染，几何只需单面
    size_w = 8.0
    size_h = 3.0
    for angle_deg in [0, 45, 90, 135]:
        panel = Mesh("fog_%d" % angle_deg, "white_robe")
        hw = size_w * 0.5
        p0 = (-hw, 0, 0.0)
        p1 = (hw, 0, 0.0)
        p2 = (hw, 0, size_h)
        p3 = (-hw, 0, size_h)
        panel.set_tint_fn(fog_tint)
        panel.quad(p0, p1, p2, p3, color="white_robe", double=False)
        panel.rotate(rz=float(angle_deg))
        m.merge(panel)

    return [(m, "M_Fog")]


# ──────────────────────────────────────────────────────────────────────
# B5  天空球  budget 480
# ──────────────────────────────────────────────────────────────────────

def build_sky_dome(ctx):
    rng = ctx["rng"]
    m = Mesh("SkyDome", "white_robe")
    # 半球即可，rings=8 segments=12 → ~192 tri
    # 法线朝内：用 mirror 翻转绕序
    m.sphere_uv((0, 0, 0), 50.0, rings=8, segments=12, color="white_robe")

    # 顶点色做地平线→zenith渐变：暖白(地平线) → 淡蓝(天顶)
    from theseed_geo import palette_uv_center
    uv_warm = palette_uv_center("sand")       # 暖白
    uv_cold = palette_uv_center("blue_kimono") # 淡蓝
    for i, p in enumerate(m.pos):
        z = p[2]
        # z 范围 [-50, 50]，我们关心上半球
        t = max(0.0, min(1.0, (z + 50.0) / 100.0))
        # 亮度保持 1.0，UV 插值由引擎处理；这里用 col 做简单渐变
        # 底部偏暖，顶部偏冷
        r = 1.0 - t * 0.15
        g = 1.0 - t * 0.05
        b = 1.0 + t * 0.10
        m.col[i] = (min(1.0, r), min(1.0, g), min(1.0, b))

    # 翻转法线朝内
    m.mirror("x")

    return [(m, "M_Sky")]


# ──────────────────────────────────────────────────────────────────────
# B6  记录结晶  八面体  budget 48
# ──────────────────────────────────────────────────────────────────────

def build_crystal_record(ctx):
    rng = ctx["rng"]
    m = Mesh("CrystalRecord", "cold")
    # 八面体 = 两个四棱锥对扣
    # 上半锥
    top = Mesh("ctop", "cold")
    top.cone((0, 0, 0), 0.08, 0.15, segments=4, color="cold", axis="z")
    top.translate(0, 0, 0.0)
    # 下半锥（翻转）
    bot = Mesh("cbot", "cold")
    bot.cone((0, 0, 0), 0.08, 0.15, segments=4, color="cold", axis="z")
    bot.rotate(rx=180)
    m.merge(top)
    m.merge(bot)
    # 整体居中：底部贴 z=0
    m.translate(0, 0, 0.15)
    return [(m, "M_Crystal_Glow")]


# ──────────────────────────────────────────────────────────────────────
# B7  回廊结晶  拉长十二面体  budget 64
# ──────────────────────────────────────────────────────────────────────

def build_crystal_corridor(ctx):
    rng = ctx["rng"]
    m = Mesh("CrystalCorridor", "cold")
    # 拉长的六角柱近似十二面体效果
    # 中间粗两端细的拉长晶体
    # 用三段拼接：下锥 + 中柱 + 上锥
    bot = Mesh("cc_bot", "cold")
    bot.cone((0, 0, 0), 0.06, 0.12, segments=5, color="cold_dark", axis="z")
    mid = Mesh("cc_mid", "cold")
    mid.cylinder((0, 0, 0.12), 0.06, 0.06, 0.20, segments=5, color="cold", axis="z")
    top = Mesh("cc_top", "cold")
    top.cone((0, 0, 0.32), 0.06, 0.12, segments=5, color="cold_dark", axis="z")
    top.rotate(rx=180)
    top.translate(0, 0, 0.44)
    m.merge(bot)
    m.merge(mid)
    m.merge(top)
    return [(m, "M_Crystal_Glow")]


# ──────────────────────────────────────────────────────────────────────
# B8  团子  3球串竹签  budget 120
# ──────────────────────────────────────────────────────────────────────

def build_item_dango(ctx):
    rng = ctx["rng"]
    m = Mesh("ItemDango", "sakura")

    # 竹签
    stick = Mesh("stick", "bamboo")
    stick.cylinder((0, 0, 0), 0.005, 0.005, 0.22, segments=3, color="bamboo", axis="z")
    m.merge(stick)

    # 三个团子：粉/白/绿，从下到上
    colors = ["sakura", "white_robe", "moss"]
    z_positions = [0.05, 0.11, 0.17]
    for zi, col in zip(z_positions, colors):
        ball = Mesh("ball", col)
        ball.sphere_uv((0, 0, zi), 0.025, rings=3, segments=4, color=col)
        m.merge(ball)

    return [(m, "M_Palette_Opaque")]


# ──────────────────────────────────────────────────────────────────────
# B9  强化石（磨刀石） budget 96
# ──────────────────────────────────────────────────────────────────────

def build_item_whetstone(ctx):
    rng = ctx["rng"]
    m = Mesh("ItemWhetstone", "stone")
    # 扁平方块带倒角：用 box 即可，低模风格不需要真倒角
    m.box((0, 0, 0.03), (0.12, 0.06, 0.06), color="stone_dark",
          tint_fn=tint_height("z", 0.0, 0.06, dark=0.7, bright=1.0))
    return [(m, "M_Palette_Stone")]


# ──────────────────────────────────────────────────────────────────────
# ASSETS 注册表
# ──────────────────────────────────────────────────────────────────────

ASSETS = {
    "asset_petal": {
        "file": "SM_Sakura_Petal.glb",
        "build": build_petal,
        "materials": ["M_Petal"],
        "tri_budget": 2,
    },
    "asset_ground_tile": {
        "file": "SM_Ground_Tile.glb",
        "build": build_ground_tile,
        "materials": ["M_Palette_Opaque"],
        "tri_budget": 64,
    },
    "asset_water_surface": {
        "file": "SM_Water_Surface.glb",
        "build": build_water_surface,
        "materials": ["M_Water"],
        "tri_budget": 800,
    },
    "asset_fog_plane": {
        "file": "SM_Fog_Plane.glb",
        "build": build_fog_plane,
        "materials": ["M_Fog"],
        "tri_budget": 8,
    },
    "asset_sky_dome": {
        "file": "SM_Sky_Dome.glb",
        "build": build_sky_dome,
        "materials": ["M_Sky"],
        "tri_budget": 480,
    },
    "asset_crystal_record": {
        "file": "SM_Crystal_Record.glb",
        "build": build_crystal_record,
        "materials": ["M_Crystal_Glow"],
        "tri_budget": 48,
    },
    "asset_crystal_corridor": {
        "file": "SM_Crystal_Corridor.glb",
        "build": build_crystal_corridor,
        "materials": ["M_Crystal_Glow"],
        "tri_budget": 64,
    },
    "asset_item_dango": {
        "file": "SM_Item_Dango.glb",
        "build": build_item_dango,
        "materials": ["M_Palette_Opaque"],
        "tri_budget": 120,
    },
    "asset_item_whetstone": {
        "file": "SM_Item_Whetstone.glb",
        "build": build_item_whetstone,
        "materials": ["M_Palette_Stone"],
        "tri_budget": 96,
    },
}
