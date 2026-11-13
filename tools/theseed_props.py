"""
theseed_props.py — 樱庭·离宫 庭院小品资产（9 个）

坐标系：右手系 +X东 +Y北 +Z上，单位=米。
所有模型底部贴 z=0 平面向上生长。
"""

import math
from theseed_geo import Mesh, tint_ao_bottom, tint_height


# ──────────────────────────────────────────────────────────────────────
# 辅助
# ──────────────────────────────────────────────────────────────────────

def _hex_prism(mesh, cx, cy, cz, r, h, segments=6, color="stone", cap_top=True, cap_bottom=True):
    """六角棱柱快捷方式。"""
    mesh.cylinder((cx, cy, cz), r, r, h, segments=segments,
                  cap_top=cap_top, cap_bottom=cap_bottom, color=color)
    return mesh


# ──────────────────────────────────────────────────────────────────────
# A1  石灯笼「春日型」 高 1.6m   budget 480
# ──────────────────────────────────────────────────────────────────────

def build_ishidoro_tall(ctx):
    rng = ctx["rng"]
    body = Mesh("IshidoroTall_Body", "stone")
    glow = Mesh("IshidoroTall_Glow", "paper_lamp")

    # 各段高度分配 (总 1.6m)
    # 基座 0.18 | 竿 0.50 | 中台 0.10 | 火袋 0.36 | 笠 0.28 | 宝珠 0.18
    z = 0.0

    # 1. 基座：六角扁柱
    base_h = 0.18
    body.cylinder((0, 0, z), 0.22, 0.25, base_h, segments=6, color="stone_dark",
                  tint_fn=tint_ao_bottom("z", 0.0, 0.15, dark=0.5))
    z += base_h

    # 2. 竿：细圆柱
    pole_h = 0.50
    body.cylinder((0, 0, z), 0.07, 0.07, pole_h, segments=6, color="stone")
    z += pole_h

    # 3. 中台：外扩平台
    mid_h = 0.10
    body.cylinder((0, 0, z), 0.25, 0.20, mid_h, segments=6, color="stone")
    z += mid_h

    # 4. 火袋：六角灯箱
    fire_h = 0.36
    fire_r = 0.20
    # 外壳
    body.cylinder((0, 0, z), fire_r, fire_r, fire_h, segments=6, color="stone",
                  cap_top=True, cap_bottom=True)
    # 六面窗口发光体（小扁盒嵌入每面）
    glow_z_center = z + fire_h * 0.5
    for i in range(6):
        angle = 2.0 * math.pi * i / 6.0
        gx = math.cos(angle) * (fire_r - 0.02)
        gy = math.sin(angle) * (fire_r - 0.02)
        # 小扁盒模拟窗口光
        gw = 0.08  # 窗宽
        gh = 0.16  # 窗高
        gd = 0.02  # 厚度
        # 用旋转的小box
        win = Mesh("win_%d" % i, "paper_lamp")
        win.box((gx, gy, glow_z_center), (gd, gw, gh), color="paper_lamp")
        # 朝向外侧旋转
        win.rotate(rz=math.degrees(angle))
        glow.merge(win)
    z += fire_h

    # 5. 笠：六角坡顶（锥台）
    kasa_h = 0.28
    body.cylinder((0, 0, z), 0.30, 0.06, kasa_h, segments=6, color="stone_dark")
    z += kasa_h

    # 6. 宝珠：小球
    hoju_r = 0.06
    body.sphere_uv((0, 0, z + hoju_r), hoju_r, rings=3, segments=4, color="stone")

    return [(body, "M_Palette_Stone"), (glow, "M_Lantern_Glow")]


# ──────────────────────────────────────────────────────────────────────
# A2  石灯笼「置灯篭型」矮款  高 0.7m   budget 320
# ──────────────────────────────────────────────────────────────────────

def build_ishidoro_short(ctx):
    rng = ctx["rng"]
    body = Mesh("IshidoroShort_Body", "stone")
    glow = Mesh("IshidoroShort_Glow", "paper_lamp")

    z = 0.0
    # 基座 0.10 | 竿 0.18 | 中台 0.06 | 火袋 0.18 | 笠 0.12 | 宝珠 0.06
    base_h = 0.10
    body.cylinder((0, 0, z), 0.20, 0.22, base_h, segments=6, color="stone_dark",
                  tint_fn=tint_ao_bottom("z", 0.0, 0.10, dark=0.5))
    z += base_h

    pole_h = 0.18
    body.cylinder((0, 0, z), 0.08, 0.08, pole_h, segments=6, color="stone")
    z += pole_h

    mid_h = 0.06
    body.cylinder((0, 0, z), 0.22, 0.18, mid_h, segments=6, color="stone")
    z += mid_h

    fire_h = 0.18
    fire_r = 0.18
    body.cylinder((0, 0, z), fire_r, fire_r, fire_h, segments=6, color="stone")
    glow_zc = z + fire_h * 0.5
    for i in range(6):
        angle = 2.0 * math.pi * i / 6.0
        gx = math.cos(angle) * (fire_r - 0.02)
        gy = math.sin(angle) * (fire_r - 0.02)
        win = Mesh("swin_%d" % i, "paper_lamp")
        win.box((gx, gy, glow_zc), (0.02, 0.07, 0.10), color="paper_lamp")
        win.rotate(rz=math.degrees(angle))
        glow.merge(win)
    z += fire_h

    kasa_h = 0.12
    body.cylinder((0, 0, z), 0.26, 0.05, kasa_h, segments=6, color="stone_dark")
    z += kasa_h

    hoju_r = 0.04
    body.sphere_uv((0, 0, z + hoju_r), hoju_r, rings=2, segments=3, color="stone")

    return [(body, "M_Palette_Stone"), (glow, "M_Lantern_Glow")]


# ──────────────────────────────────────────────────────────────────────
# A3  鹿威し  高 1.1m   budget 420
# ──────────────────────────────────────────────────────────────────────

def build_shishiodoshi(ctx):
    rng = ctx["rng"]
    body = Mesh("ShishiOdoshi_Body", "stone")
    tube = Mesh("ShishiOdoshi_Tube", "bamboo")

    # 石钵：挖空的圆石（扁球 + 内凹用一个倒锥暗示）
    bowl = Mesh("bowl", "stone")
    # center_z raised so bottom sits at z=0 after squash
    bowl.icosphere((0, 0, 0.22 * 0.55), 0.22, subdiv=1, color="stone", squash=0.55,
                   tint_fn=tint_ao_bottom("z", 0.0, 0.20, dark=0.5))
    # 内凹：一个小倒锥压进去暗示凹槽
    inner = Mesh("inner", "stone_dark")
    inner.cone((0, 0, 0.28), 0.12, 0.10, segments=5, color="water_dark", axis="z")
    # 翻转使开口朝上
    inner.rotate(rx=180)
    inner.translate(0, 0, 0.30)
    bowl.merge(inner)
    body.merge(bowl)

    # 支撑竹架：两根竖竹 + 一根横竹
    frame = Mesh("frame", "bamboo")
    # 左立柱
    frame.cylinder((-0.25, 0, 0), 0.025, 0.025, 0.85, segments=5, color="bamboo", axis="z")
    # 右立柱
    frame.cylinder((0.25, 0, 0), 0.025, 0.025, 0.85, segments=5, color="bamboo", axis="z")
    # 横杆（支点）
    cross = Mesh("cross", "bamboo")
    cross.cylinder((0, 0, 0), 0.02, 0.02, 0.55, segments=5, color="bamboo", axis="z")
    cross.rotate(rx=90)  # 沿Y方向
    cross.translate(0, 0, 0.70)
    frame.merge(cross)
    body.merge(frame)

    # 竹筒：可摆动，支点在竹筒中段
    # 竹筒长 0.6m，外径 0.04，绕 Y 轴放置
    tube_main = Mesh("tube_main", "bamboo")
    tube_main.cylinder((0, 0, 0), 0.04, 0.035, 0.60, segments=5, color="bamboo", axis="z")
    # 旋转到水平（沿Y），然后平移使支点在原点
    tube_main.rotate(rx=90)
    tube_main.translate(0, 0.0, 0.70)  # 支点高度
    tube.merge(tube_main)

    return [(body, "M_Palette_Stone"), (tube, "M_Palette_Wood")]


# ──────────────────────────────────────────────────────────────────────
# A4  石组A  3块  2.2×1.8m  budget 360
# ──────────────────────────────────────────────────────────────────────

def build_rock_cluster_a(ctx):
    rng = ctx["rng"]
    m = Mesh("RockClusterA", "stone")

    specs = [
        ((0.0, 0.0), 0.45, 0.6),    # 主石
        ((-0.6, 0.4), 0.30, 0.5),   # 副石
        ((0.5, -0.3), 0.22, 0.45),  # 陪石
    ]
    for (cx, cy), r, sq in specs:
        rock = Mesh("r", "stone")
        jitter_amt = 0.08
        # center_z = r*squash + jitter_amt 确保底部贴地
        cz = r * sq + jitter_amt
        rock.icosphere((cx, cy, cz), r, subdiv=1, color="stone",
                       squash=sq, tint_fn=tint_ao_bottom("z", 0.0, r * 0.6, dark=0.5))
        rock.jitter(jitter_amt, rng)
        m.merge(rock)

    return [(m, "M_Palette_Stone")]


# ──────────────────────────────────────────────────────────────────────
# A5  石组B  5块  3.0×2.4m  budget 520
# ──────────────────────────────────────────────────────────────────────

def build_rock_cluster_b(ctx):
    rng = ctx["rng"]
    m = Mesh("RockClusterB", "stone")

    specs = [
        ((0.0, 0.0), 0.55, 0.65),      # 主石
        ((-0.8, 0.5), 0.35, 0.50),     # 副石1
        ((0.7, -0.4), 0.30, 0.45),     # 副石2
        ((-0.3, -0.7), 0.20, 0.40),    # 陪石1
        ((0.9, 0.6), 0.18, 0.38),      # 陪石2
    ]
    for (cx, cy), r, sq in specs:
        rock = Mesh("r", "stone")
        jitter_amt = 0.10
        cz = r * sq + jitter_amt
        rock.icosphere((cx, cy, cz), r, subdiv=1, color="stone",
                       squash=sq, tint_fn=tint_ao_bottom("z", 0.0, r * 0.6, dark=0.5))
        rock.jitter(jitter_amt, rng)
        m.merge(rock)

    return [(m, "M_Palette_Stone")]


# ──────────────────────────────────────────────────────────────────────
# A6  单石  0.8m  budget 120
# ──────────────────────────────────────────────────────────────────────

def build_rock_single(ctx):
    rng = ctx["rng"]
    m = Mesh("RockSingle", "stone")
    r = 0.35
    sq = 0.55
    jitter_amt = 0.06
    cz = r * sq + jitter_amt
    m.icosphere((0, 0, cz), r, subdiv=1, color="stone", squash=sq,
                tint_fn=tint_ao_bottom("z", 0.0, r * 0.5, dark=0.5))
    m.jitter(jitter_amt, rng)
    return [(m, "M_Palette_Stone")]


# ──────────────────────────────────────────────────────────────────────
# A7  飞石（汀步） 0.55×0.4m  budget 64
# ──────────────────────────────────────────────────────────────────────

def build_stepping_stone(ctx):
    rng = ctx["rng"]
    m = Mesh("SteppingStone", "stone")
    # 扁不规则石板：用 jitter 过的扁 icosphere
    sq = 0.25
    r = 0.22
    jitter_amt = 0.03
    cz = r * sq + jitter_amt
    m.icosphere((0, 0, cz), r, subdiv=0, color="stone", squash=sq,
                tint_fn=tint_ao_bottom("z", 0.0, 0.06, dark=0.55))
    m.jitter(jitter_amt, rng)
    return [(m, "M_Palette_Stone")]


# ──────────────────────────────────────────────────────────────────────
# A8  手水钵  高 0.6m  budget 280
# ──────────────────────────────────────────────────────────────────────

def build_chozubachi(ctx):
    rng = ctx["rng"]
    body = Mesh("Chozubachi_Body", "stone")
    water = Mesh("Chozubachi_Water", "water")

    # 底部垫石
    base = Mesh("base", "stone_dark")
    base.cylinder((0, 0, 0), 0.22, 0.25, 0.08, segments=6, color="stone_dark",
                  tint_fn=tint_ao_bottom("z", 0.0, 0.08, dark=0.5))
    body.merge(base)

    # 圆形石钵
    bowl = Mesh("bowl", "stone")
    bowl.icosphere((0, 0, 0.25), 0.25, subdiv=1, color="stone", squash=0.55,
                   tint_fn=tint_ao_bottom("z", 0.08, 0.15, dark=0.55))
    bowl.jitter(0.02, rng)
    body.merge(bowl)

    # 内凹盛水面
    water.disc((0, 0, 0.30), 0.15, segments=8, color="water", normal="z")

    # 竹管引水
    pipe = Mesh("pipe", "bamboo")
    pipe.cylinder((0.20, 0, 0.35), 0.02, 0.02, 0.30, segments=4, color="bamboo", axis="z")
    pipe.rotate(rx=-30)
    pipe.translate(-0.05, 0, 0.05)
    body.merge(pipe)

    return [(body, "M_Palette_Stone"), (water, "M_Water")]


# ──────────────────────────────────────────────────────────────────────
# A9  呼应石  1.2×0.9m  budget 140
# ──────────────────────────────────────────────────────────────────────

def build_calling_stone(ctx):
    rng = ctx["rng"]
    m = Mesh("CallingStone", "stone")
    # 扁平、顶面平整的石台
    sq = 0.30
    r = 0.45
    jitter_amt = 0.05
    cz = r * sq + jitter_amt
    m.icosphere((0, 0, cz), r, subdiv=1, color="stone", squash=sq,
                tint_fn=tint_ao_bottom("z", 0.0, 0.12, dark=0.5))
    m.jitter(jitter_amt, rng)
    return [(m, "M_Palette_Stone")]


# ──────────────────────────────────────────────────────────────────────
# ASSETS 注册表
# ──────────────────────────────────────────────────────────────────────

ASSETS = {
    "asset_ishidoro_tall": {
        "file": "SM_Ishidoro_Tall.glb",
        "build": build_ishidoro_tall,
        "materials": ["M_Palette_Stone", "M_Lantern_Glow"],
        "tri_budget": 480,
        "parts": {"body": 0, "glow": 1},
    },
    "asset_ishidoro_short": {
        "file": "SM_Ishidoro_Short.glb",
        "build": build_ishidoro_short,
        "materials": ["M_Palette_Stone", "M_Lantern_Glow"],
        "tri_budget": 320,
        "parts": {"body": 0, "glow": 1},
    },
    "asset_shishiodoshi": {
        "file": "SM_ShishiOdoshi.glb",
        "build": build_shishiodoshi,
        "materials": ["M_Palette_Stone", "M_Palette_Wood"],
        "tri_budget": 420,
        "parts": {"body": 0, "tube": 1},
    },
    "asset_rock_cluster_a": {
        "file": "SM_Rock_Cluster_A.glb",
        "build": build_rock_cluster_a,
        "materials": ["M_Palette_Stone"],
        "tri_budget": 360,
    },
    "asset_rock_cluster_b": {
        "file": "SM_Rock_Cluster_B.glb",
        "build": build_rock_cluster_b,
        "materials": ["M_Palette_Stone"],
        "tri_budget": 520,
    },
    "asset_rock_single": {
        "file": "SM_Rock_Single.glb",
        "build": build_rock_single,
        "materials": ["M_Palette_Stone"],
        "tri_budget": 120,
    },
    "asset_stepping_stone": {
        "file": "SM_Stepping_Stone.glb",
        "build": build_stepping_stone,
        "materials": ["M_Palette_Stone"],
        "tri_budget": 64,
    },
    "asset_chozubachi": {
        "file": "SM_Chozubachi.glb",
        "build": build_chozubachi,
        "materials": ["M_Palette_Stone", "M_Water"],
        "tri_budget": 280,
        "parts": {"body": 0, "water": 1},
    },
    "asset_calling_stone": {
        "file": "SM_Calling_Stone.glb",
        "build": build_calling_stone,
        "materials": ["M_Palette_Stone"],
        "tri_budget": 140,
    },
}
