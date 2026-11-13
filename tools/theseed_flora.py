"""
theseed_flora.py — 「樱庭·离宫」植物资产程序化生成模块

纯 Python 标准库 + theseed_geo，不依赖任何第三方包。
所有随机使用 ctx["rng"]（Rng 实例），保证确定性可复现。
坐标系：右手系 +X东 +Y北 +Z上，单位=米，底部贴 z=0。
"""

import math
from theseed_geo import Mesh, tint_height, tint_ao_bottom


# ===========================================================================
# 辅助函数
# ===========================================================================

def _branch_recursive(mesh, origin, direction, length, radius, depth, max_depth, rng, sides=5):
    """递归生成分枝。每级 2-3 根子枝，长度×0.62，半径×0.6。"""
    if depth > max_depth or radius < 0.005:
        return
    # 当前枝段终点
    end = (origin[0] + direction[0] * length,
           origin[1] + direction[1] * length,
           origin[2] + direction[2] * length)
    mesh.ring_tube(points=[origin, end], radii=[radius, radius * 0.85], sides=sides, color="bark")
    # 子枝
    n_children = 2 if depth >= max_depth - 1 else int(rng.range(2, 3.99))
    for _ in range(n_children):
        # 随机偏转方向
        az = rng.range(0, 360)
        el = rng.range(20, 55)
        az_r = math.radians(az)
        el_r = math.radians(el)
        # 在局部坐标系中生成新方向
        dx = math.sin(el_r) * math.cos(az_r)
        dy = math.sin(el_r) * math.sin(az_r)
        dz = math.cos(el_r)
        # 将局部方向叠加到父方向上（简化混合）
        nd = (direction[0] * 0.4 + dx * 0.6,
              direction[1] * 0.4 + dy * 0.6,
              direction[2] * 0.4 + dz * 0.6)
        nl = math.sqrt(nd[0]**2 + nd[1]**2 + nd[2]**2) or 1.0
        nd = (nd[0]/nl, nd[1]/nl, nd[2]/nl)
        _branch_recursive(mesh, end, nd, length * 0.62, radius * 0.6,
                          depth + 1, max_depth, rng, sides)


def _canopy_cluster(mesh, center, radius, count, rng, subdiv=1, jitter_amt=0.15):
    """在中心附近放置 count 个 icosphere 组成树冠簇。"""
    colors = ["sakura", "sakura_deep", "sakura_white"]
    for i in range(count):
        # 随机偏移
        ox = rng.range(-radius * 0.6, radius * 0.6)
        oy = rng.range(-radius * 0.6, radius * 0.6)
        oz = rng.range(-radius * 0.3, radius * 0.5)
        c = (center[0] + ox, center[1] + oy, center[2] + oz)
        r = radius * rng.range(0.5, 0.85)
        col = colors[i % 3]
        mesh.set_color(col)
        mesh.icosphere(c, r, subdiv=subdiv)
    mesh.jitter(jitter_amt, rng)


def _make_trunk(height, r_base, r_top, rng, segments=6, bend=0.0):
    """生成树干 Mesh。"""
    trunk = Mesh("trunk", "bark")
    trunk.set_tint_fn(tint_ao_bottom("z", 0.0, 0.8, dark=0.55))
    trunk.cylinder((0, 0, 0), r_base, r_top, height, segments=segments,
                   cap_bottom=True, cap_top=False, color="bark", bend=bend)
    trunk.set_tint_fn(None)
    return trunk


# ===========================================================================
# 资产构建函数
# ===========================================================================

def build_sakura_tree_large(ctx):
    """大樱花树：主干 + 3级分枝 + 14团树冠。高6.5m，冠幅7m。"""
    rng = ctx["rng"]
    # 树干
    trunk = _make_trunk(3.2, 0.22, 0.10, rng, segments=6)
    # 分枝（从树干顶部附近开始）
    trunk.set_color("bark")
    branch_origin = (0, 0, 2.8)
    n_main = 4
    for i in range(n_main):
        az = rng.range(0, 360)
        el = rng.range(30, 50)
        az_r = math.radians(az)
        el_r = math.radians(el)
        dx = math.sin(el_r) * math.cos(az_r)
        dy = math.sin(el_r) * math.sin(az_r)
        dz = math.cos(el_r)
        d = (dx, dy, dz)
        _branch_recursive(trunk, branch_origin, d, 1.6, 0.08, 0, 2, rng, sides=5)

    # 树冠：14团
    canopy = Mesh("canopy", "sakura")
    canopy.set_tint_fn(tint_height("z", 3.0, 6.5, dark=0.7, bright=1.05))
    canopy_center = (0, 0, 4.8)
    _canopy_cluster(canopy, canopy_center, 1.8, 14, rng, subdiv=1, jitter_amt=0.15)
    canopy.set_tint_fn(None)

    return [(trunk, "M_Palette_Opaque"), (canopy, "M_Foliage_Cutout")]


def build_sakura_tree_mid(ctx):
    """中樱花树：9团树冠。高4.2m，冠幅4.5m。"""
    rng = ctx["rng"]
    trunk = _make_trunk(2.2, 0.16, 0.08, rng, segments=5)
    trunk.set_color("bark")
    branch_origin = (0, 0, 1.8)
    for i in range(3):
        az = rng.range(0, 360)
        el = rng.range(30, 50)
        az_r = math.radians(az)
        el_r = math.radians(el)
        dx = math.sin(el_r) * math.cos(az_r)
        dy = math.sin(el_r) * math.sin(az_r)
        dz = math.cos(el_r)
        _branch_recursive(trunk, branch_origin, (dx, dy, dz), 1.1, 0.06, 0, 1, rng, sides=5)

    canopy = Mesh("canopy", "sakura")
    canopy.set_tint_fn(tint_height("z", 2.0, 4.2, dark=0.7, bright=1.05))
    _canopy_cluster(canopy, (0, 0, 3.2), 1.2, 9, rng, subdiv=1, jitter_amt=0.12)
    canopy.set_tint_fn(None)

    return [(trunk, "M_Palette_Opaque"), (canopy, "M_Foliage_Cutout")]


def build_sakura_tree_small(ctx):
    """小樱花树：5团树冠。高2.4m，冠幅2.6m。"""
    rng = ctx["rng"]
    trunk = _make_trunk(1.3, 0.10, 0.05, rng, segments=5)
    trunk.set_color("bark")
    branch_origin = (0, 0, 1.0)
    for i in range(2):
        az = rng.range(0, 360)
        el = rng.range(30, 50)
        az_r = math.radians(az)
        el_r = math.radians(el)
        dx = math.sin(el_r) * math.cos(az_r)
        dy = math.sin(el_r) * math.sin(az_r)
        dz = math.cos(el_r)
        _branch_recursive(trunk, branch_origin, (dx, dy, dz), 0.7, 0.04, 0, 1, rng, sides=5)

    canopy = Mesh("canopy", "sakura")
    canopy.set_tint_fn(tint_height("z", 1.2, 2.4, dark=0.7, bright=1.05))
    _canopy_cluster(canopy, (0, 0, 1.8), 0.9, 5, rng, subdiv=0, jitter_amt=0.12)
    canopy.set_tint_fn(None)

    return [(trunk, "M_Palette_Opaque"), (canopy, "M_Foliage_Cutout")]


def build_sakura_solo(ctx):
    """独樱：刻意不对称，单侧倾斜、一枝横伸。高5.0m。"""
    rng = ctx["rng"]
    # 倾斜主干
    trunk = Mesh("trunk", "bark")
    trunk.set_tint_fn(tint_ao_bottom("z", 0.0, 0.8, dark=0.55))
    trunk.cylinder((0, 0, 0), 0.18, 0.09, 3.0, segments=6,
                   cap_bottom=True, cap_top=False, color="bark", bend=0.6)
    trunk.set_tint_fn(None)
    # 横伸枝
    trunk.set_color("bark")
    side_origin = (0.3, 0, 2.5)
    side_dir = (0.8, 0.1, 0.3)
    nl = math.sqrt(sum(x*x for x in side_dir))
    side_dir = tuple(x/nl for x in side_dir)
    _branch_recursive(trunk, side_origin, side_dir, 1.8, 0.07, 0, 2, rng, sides=5)
    # 另一侧短枝
    side2_dir = (-0.5, 0.3, 0.5)
    nl2 = math.sqrt(sum(x*x for x in side2_dir))
    side2_dir = tuple(x/nl2 for x in side2_dir)
    _branch_recursive(trunk, (0.1, 0, 2.0), side2_dir, 0.9, 0.05, 0, 1, rng, sides=5)

    # 树冠偏向一侧
    canopy = Mesh("canopy", "sakura")
    canopy.set_tint_fn(tint_height("z", 2.5, 5.0, dark=0.7, bright=1.05))
    # 主冠簇偏右上方
    _canopy_cluster(canopy, (0.6, 0.1, 3.6), 1.2, 8, rng, subdiv=1, jitter_amt=0.13)
    # 小簇在左侧
    _canopy_cluster(canopy, (-0.2, 0.2, 3.2), 0.65, 3, rng, subdiv=0, jitter_amt=0.10)
    canopy.set_tint_fn(None)

    return [(trunk, "M_Palette_Opaque"), (canopy, "M_Foliage_Cutout")]


def build_pine_black(ctx):
    """黑松：伞状分层树冠（4-5层扁平云片状），树干略弯曲。高4.0m。"""
    rng = ctx["rng"]
    # 树干略弯
    trunk = Mesh("trunk", "bark_dark")
    trunk.set_tint_fn(tint_ao_bottom("z", 0.0, 0.6, dark=0.5))
    trunk.cylinder((0, 0, 0), 0.14, 0.07, 3.5, segments=5,
                   cap_bottom=True, cap_top=False, color="bark_dark", bend=0.15)
    trunk.set_tint_fn(None)

    # 伞状层：5层扁平 icosphere
    canopy = Mesh("canopy", "moss")
    canopy.set_tint_fn(tint_height("z", 1.5, 4.0, dark=0.65, bright=1.0))
    layers = [
        (0, 0, 1.8, 1.3, 0.35),
        (0.1, 0, 2.3, 1.1, 0.32),
        (-0.05, 0.05, 2.8, 0.95, 0.30),
        (0, -0.05, 3.2, 0.75, 0.28),
        (0, 0, 3.6, 0.55, 0.25),
    ]
    colors_pine = ["moss", "grass_dark"]
    for i, (cx, cy, cz, r, sq) in enumerate(layers):
        # 每层加一点随机偏移
        ox = rng.range(-0.1, 0.1)
        oy = rng.range(-0.1, 0.1)
        col = colors_pine[i % 2]
        canopy.set_color(col)
        canopy.icosphere((cx + ox, cy + oy, cz), r, subdiv=1, squash=sq)
    canopy.jitter(0.08, rng)
    canopy.set_tint_fn(None)

    return [(trunk, "M_Palette_Opaque"), (canopy, "M_Foliage_Cutout")]


def build_bamboo_cluster(ctx):
    """竹林丛：7竿竹（带竹节）+ 顶部叶簇。高3.5m，占地1.5m。"""
    rng = ctx["rng"]
    stalks = Mesh("stalks", "bamboo")
    stalks.set_tint_fn(tint_height("z", 0.0, 3.5, dark=0.7, bright=1.0))

    positions = []
    for i in range(7):
        angle = rng.range(0, 360)
        dist = rng.range(0.05, 0.55)
        x = math.cos(math.radians(angle)) * dist
        y = math.sin(math.radians(angle)) * dist
        positions.append((x, y))

    for idx, (bx, by) in enumerate(positions):
        h = rng.range(2.8, 3.5)
        r = rng.range(0.025, 0.04)
        # 竹节：用 ring_tube 代替多段 cylinder 以节省面数
        # 每竿 5-6 个节点点，sides=4
        n_pts = 5
        pts = []
        radii = []
        for s in range(n_pts):
            t = s / (n_pts - 1)
            z = t * h
            # 节间处半径略大
            node_r = r * 1.15 if (s > 0 and s < n_pts - 1) else r
            pts.append((bx, by, z))
            radii.append(node_r)
        stalks.ring_tube(points=pts, radii=radii, sides=4, color="bamboo")

    stalks.set_tint_fn(None)

    # 顶部叶簇：每竿 1 个小 icosphere
    leaves = Mesh("leaves", "grass_dark")
    for bx, by in positions:
        top_z = rng.range(2.8, 3.5)
        lx = rng.range(-0.08, 0.08)
        ly = rng.range(-0.08, 0.08)
        leaves.icosphere((bx + lx, by + ly, top_z), rng.range(0.10, 0.16),
                         subdiv=0)
    leaves.jitter(0.03, rng)

    return [(stalks, "M_Palette_Opaque"), (leaves, "M_Foliage_Cutout")]


def build_bush_round(ctx):
    """球形灌木（刈込修剪造型）。直径1.1m。"""
    rng = ctx["rng"]
    bush = Mesh("bush", "moss")
    bush.set_tint_fn(tint_ao_bottom("z", 0.0, 0.4, dark=0.5))
    # 主体球 subdiv=1 = 80面
    bush.icosphere((0, 0, 0.55), 0.50, subdiv=1, color="moss")
    # 3个附加小球(subdiv=0=20面 each)制造修剪感的块面
    for _ in range(3):
        ox = rng.range(-0.2, 0.2)
        oy = rng.range(-0.2, 0.2)
        oz = rng.range(-0.1, 0.15)
        r = rng.range(0.2, 0.30)
        col = rng.pick(["moss", "grass_dark"])
        bush.set_color(col)
        bush.icosphere((ox, oy, 0.55 + oz), r, subdiv=0)
    bush.jitter(0.06, rng)
    bush.set_tint_fn(None)

    return [(bush, "M_Palette_Opaque")]


def build_grass_tuft(ctx):
    """草丛：十字交叉面片（2-3片quad相交），双面。高0.4m。"""
    rng = ctx["rng"]
    grass = Mesh("grass", "grass")
    n_blades = int(rng.range(2, 3.99))
    for i in range(n_blades):
        angle = (180.0 / n_blades) * i + rng.range(-10, 10)
        rad = math.radians(angle)
        hw = 0.08  # half-width
        h = rng.range(0.30, 0.40)
        cx = math.cos(rad) * hw
        cy = math.sin(rad) * hw
        p0 = (-cx, -cy, 0.0)
        p1 = (cx, cy, 0.0)
        p2 = (cx * 0.6, cy * 0.6, h)
        p3 = (-cx * 0.6, -cy * 0.6, h)
        col = rng.pick(["grass", "grass_dark"])
        grass.set_color(col)
        grass.quad(p0, p1, p2, p3, double=True)

    return [(grass, "M_Foliage_Cutout")]


def build_moss_patch(ctx):
    """苔藓片：贴地不规则圆面，顶点色从中心到边缘渐变。直径1.2m。"""
    rng = ctx["rng"]
    moss = Mesh("moss", "moss")

    def moss_gradient(p):
        d = math.sqrt(p[0]*p[0] + p[1]*p[1])
        t = min(1.0, d / 0.6)
        return 1.0 - t * 0.35

    moss.set_tint_fn(moss_gradient)
    # 用 disc 做基础，然后 jitter 边缘使其不规则
    moss.disc((0, 0, 0.005), 0.6, segments=10, color="moss", normal="z")
    moss.jitter(0.06, rng)
    moss.set_tint_fn(None)

    return [(moss, "M_Palette_Opaque")]


# ===========================================================================
# 资产注册表
# ===========================================================================

ASSETS = {
    "asset_sakura_tree_large": {
        "file": "SM_Sakura_Tree_Large.glb",
        "build": build_sakura_tree_large,
        "materials": ["M_Palette_Opaque", "M_Foliage_Cutout"],
        "tri_budget": 3200,
    },
    "asset_sakura_tree_mid": {
        "file": "SM_Sakura_Tree_Mid.glb",
        "build": build_sakura_tree_mid,
        "materials": ["M_Palette_Opaque", "M_Foliage_Cutout"],
        "tri_budget": 1800,
    },
    "asset_sakura_tree_small": {
        "file": "SM_Sakura_Tree_Small.glb",
        "build": build_sakura_tree_small,
        "materials": ["M_Palette_Opaque", "M_Foliage_Cutout"],
        "tri_budget": 900,
    },
    "asset_sakura_solo": {
        "file": "SM_Sakura_Solo.glb",
        "build": build_sakura_solo,
        "materials": ["M_Palette_Opaque", "M_Foliage_Cutout"],
        "tri_budget": 2000,
    },
    "asset_pine_black": {
        "file": "SM_Pine_Black.glb",
        "build": build_pine_black,
        "materials": ["M_Palette_Opaque", "M_Foliage_Cutout"],
        "tri_budget": 1200,
    },
    "asset_bamboo_cluster": {
        "file": "SM_Bamboo_Cluster.glb",
        "build": build_bamboo_cluster,
        "materials": ["M_Palette_Opaque", "M_Foliage_Cutout"],
        "tri_budget": 800,
    },
    "asset_bush_round": {
        "file": "SM_Bush_Round.glb",
        "build": build_bush_round,
        "materials": ["M_Palette_Opaque"],
        "tri_budget": 320,
    },
    "asset_grass_tuft": {
        "file": "SM_Grass_Tuft.glb",
        "build": build_grass_tuft,
        "materials": ["M_Foliage_Cutout"],
        "tri_budget": 48,
    },
    "asset_moss_patch": {
        "file": "SM_Moss_Patch.glb",
        "build": build_moss_patch,
        "materials": ["M_Palette_Opaque"],
        "tri_budget": 32,
    },
}
