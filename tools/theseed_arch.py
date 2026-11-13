"""
theseed_arch.py — 樱庭·离宫「建筑与结构」程序化资产

坐标系：右手系 +X东 +Y北 +Z上，单位米，底部贴 z=0。
规格来源：03_ArtAssetSpec_Procedural.md §2.1；02_LevelDesign_Hakoniwa.md。
美术风格：低多边形风格化（硬边、纯色块、顶点色承载明暗）。
所有随机使用 ctx["rng"]，保证字节级可复现。
"""

import math
from theseed_geo import (
    Mesh, Rng, derive_seed, m4_mul, m4_translate, m4_rot_z, m4_rot_y, m4_rot_x,
    tint_height, tint_ao_bottom,
)


# --------------------------------------------------------------------------
# 鸟居（Torii）
# --------------------------------------------------------------------------

def _build_torii(ctx, scale_w, scale_h, peel=True, detail=True):
    """通用鸟居构造。scale_w/scale_h 相对主鸟居(宽5.2 高4.6)缩放。"""
    rng = ctx["rng"]
    W = 5.2 * scale_w
    H = 4.6 * scale_h
    col_half = W * 0.345            # 柱中心 x 偏移
    col_z0 = 0.0
    col_z1 = H * 0.826              # 柱顶（贯以上由笠木/岛木承接）
    r_bot = 0.28 * scale_w
    r_top = 0.22 * scale_w
    peel_h = 0.6 * scale_h          # 柱脚风化剥落段高度

    body = Mesh("torii_body")
    peel_m = Mesh("torii_peel")

    # --- 二本柱（下段剥落灰木 + 上段朱漆）---
    for sx in (-1, 1):
        cx = sx * col_half
        if peel and peel_h > 0.05:
            # 剥落段
            peel_m.set_color("torii_peel")
            peel_m.set_tint_fn(tint_ao_bottom("z", 0.0, peel_h * 1.6, dark=0.6))
            peel_m.cylinder((cx, 0, col_z0), r_bot, r_bot * 0.97, peel_h,
                            segments=8, cap_top=False, cap_bottom=True)
            # 朱漆段
            body.set_color("torii_red")
            body.set_tint_fn(tint_height("z", peel_h, col_z1, dark=0.82, bright=1.06))
            body.cylinder((cx, 0, peel_h), r_bot * 0.97, r_top, col_z1 - peel_h,
                          segments=8, cap_top=True, cap_bottom=False)
        else:
            body.set_color("torii_red")
            body.set_tint_fn(tint_height("z", 0, col_z1, dark=0.8, bright=1.06))
            body.cylinder((cx, 0, col_z0), r_bot, r_top, col_z1,
                          segments=8, cap_top=True, cap_bottom=True)
        body.set_tint_fn(None)
        peel_m.set_tint_fn(None)
        # 柱顶冠木（台轮）
        if detail:
            body.set_color("torii_red")
            body.cylinder((cx, 0, col_z1), r_top * 1.35, r_top * 1.2, 0.12 * scale_h,
                          segments=8, cap_top=True, cap_bottom=False)

    # --- 贯（nuki）：横穿两柱的下横梁 ---
    nuki_z = col_z1 * 0.74
    body.set_color("torii_red")
    body.set_tint_fn(tint_height("z", nuki_z - 0.15, nuki_z + 0.15, dark=0.85, bright=1.0))
    body.box((0, 0, nuki_z), (W * 0.94, 0.20 * scale_w, 0.26 * scale_h))
    body.set_tint_fn(None)

    # --- 额束（gakuzuka）：贯与岛木之间的中央短柱 ---
    if detail:
        body.set_color("torii_red")
        gk_z0 = nuki_z + 0.13 * scale_h
        gk_z1 = col_z1 + 0.10 * scale_h
        body.box((0, 0, (gk_z0 + gk_z1) * 0.5),
                 (0.22 * scale_w, 0.16 * scale_w, gk_z1 - gk_z0))

    # --- 岛木（shimaki）：笠木下的垫木 ---
    shima_z = col_z1 + 0.14 * scale_h
    body.set_color("torii_red")
    body.set_tint_fn(tint_height("z", shima_z - 0.1, shima_z + 0.1, dark=0.82, bright=1.02))
    body.box((0, 0, shima_z), (W * 0.98, 0.22 * scale_w, 0.18 * scale_h))
    body.set_tint_fn(None)

    # --- 笠木（kasagi）：顶部横梁，两端上翘 ---
    kasagi_z = shima_z + 0.20 * scale_h
    body.set_color("torii_red")
    body.set_tint_fn(tint_height("z", kasagi_z - 0.12, kasagi_z + 0.12, dark=0.85, bright=1.05))
    # 中段
    body.box((0, 0, kasagi_z), (W * 0.72, 0.26 * scale_w, 0.22 * scale_h))
    # 两端上翘（各用一块旋转的 box）
    for sx in (-1, 1):
        tip = Mesh("tip")
        tip.set_color("torii_red")
        tip.box((0, 0, 0), (W * 0.30, 0.26 * scale_w, 0.22 * scale_h))
        tip.rotate(rz=sx * -13.0, ry=0, rx=0)
        tip.translate(sx * W * 0.455, 0, kasagi_z + 0.10 * scale_h)
        body.merge(tip)
    body.set_tint_fn(None)

    # --- 龟腹（柱脚石基）---
    if detail:
        for sx in (-1, 1):
            body.set_color("stone_dark")
            body.cylinder((sx * col_half, 0, 0.0), r_bot * 1.5, r_bot * 1.35,
                          0.14 * scale_h, segments=8, cap_top=True, cap_bottom=True)

    parts = [(body, "M_Palette_Wood")]
    if peel and not peel_m.is_empty():
        parts.append((peel_m, "M_Palette_Wood"))
    return parts


def build_torii_main(ctx):
    return _build_torii(ctx, 1.0, 1.0, peel=True, detail=True)


def build_torii_small(ctx):
    return _build_torii(ctx, 0.46, 0.48, peel=True, detail=False)


# --------------------------------------------------------------------------
# 樱亭（Azumaya）— 四角攒尖顶凉亭
# --------------------------------------------------------------------------

def build_azumaya(ctx):
    rng = ctx["rng"]
    wood = Mesh("azumaya_wood")
    roof = Mesh("azumaya_roof")
    floor_h = 0.45
    half = 3.5            # 7m 见方
    col_in = 2.75         # 柱内收
    col_top = 2.55        # 柱顶 z（自地台起）
    roof_base = floor_h + col_top
    roof_apex = 4.2

    # --- 地台 ---
    wood.set_color("wood")
    wood.set_tint_fn(tint_height("z", 0, floor_h, dark=0.7, bright=1.0))
    wood.box((0, 0, floor_h * 0.5), (half * 2, half * 2, floor_h))
    wood.set_tint_fn(None)
    # 地板面（略亮，行走面）
    wood.set_color("wood_dark")
    wood.box((0, 0, floor_h + 0.02), (half * 2 - 0.1, half * 2 - 0.1, 0.04))

    # --- 南侧台阶（-Y）三级 ---
    wood.set_color("wood")
    for i in range(3):
        step_h = floor_h / 3.0
        wood.box((0, -half - 0.28 + i * 0.02, step_h * (i + 0.5)),
                 (1.6, 0.55 - i * 0.02, step_h))

    # --- 四柱 ---
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * col_in, sy * col_in
            wood.set_color("wood_dark")
            wood.set_tint_fn(tint_height("z", floor_h, roof_base, dark=0.8, bright=1.05))
            wood.cylinder((cx, cy, floor_h), 0.13, 0.11, col_top,
                          segments=8, cap_top=True, cap_bottom=False)
            wood.set_tint_fn(None)

    # --- 栏干（四周，南侧留台阶口）---
    rail_z0 = floor_h + 0.12
    rail_z1 = floor_h + 0.55
    wood.set_color("wood")
    for sy in (-1, 1):
        # 东西向栏（南北两侧）
        if sy == -1:
            # 南侧：分两段，中间留 1.6m 台阶口
            for sx in (-1, 1):
                seg_cx = sx * (col_in * 0.5 + 0.85)
                seg_len = col_in - 0.85
                wood.box((seg_cx, sy * col_in, (rail_z0 + rail_z1) * 0.5),
                         (seg_len, 0.10, rail_z1 - rail_z0))
        else:
            wood.box((0, sy * col_in, (rail_z0 + rail_z1) * 0.5),
                     (col_in * 2, 0.10, rail_z1 - rail_z0))
    for sx in (-1, 1):
        wood.box((sx * col_in, 0, (rail_z0 + rail_z1) * 0.5),
                 (0.10, col_in * 2, rail_z1 - rail_z0))
    # 栏干望柱
    for sx in (-1, 1):
        for sy in (-1, 1):
            wood.set_color("wood_dark")
            wood.box((sx * col_in, sy * col_in, (floor_h + rail_z1) * 0.5 + 0.05),
                     (0.14, 0.14, rail_z1 - floor_h + 0.10))

    # --- 檐下横梁（ connecting 柱顶）---
    wood.set_color("wood_dark")
    for sy in (-1, 1):
        wood.box((0, sy * col_in, roof_base - 0.08), (col_in * 2 + 0.2, 0.16, 0.16))
    for sx in (-1, 1):
        wood.box((sx * col_in, 0, roof_base - 0.08), (0.16, col_in * 2 + 0.2, 0.16))

    # --- 出檐（外扩的屋檐底板）---
    eave = half + 0.55
    roof.set_color("wood_dark")
    roof.box((0, 0, roof_base + 0.06), (eave * 2, eave * 2, 0.10))

    # --- 四角攒尖顶（瓦顶）---
    # 四棱锥 segments=4 底面顶点默认落在 ±X/±Y（菱形），需旋转 45° 使其
    # 棱对齐方形地台。锥体单独建 mesh 旋转后再并入，避免连带转出檐底板。
    roof.set_color("tile")
    roof.set_tint_fn(tint_height("z", roof_base, roof_apex, dark=0.75, bright=1.08))
    hip = Mesh("hip")
    hip.set_color("tile")
    hip.set_tint_fn(tint_height("z", roof_base, roof_apex, dark=0.75, bright=1.08))
    hip.cone((0, 0, roof_base + 0.10), eave * 1.02, roof_apex - roof_base - 0.10,
             segments=4, axis="z")
    hip.rotate(rz=45.0)
    roof.merge(hip)
    roof.set_tint_fn(None)
    # 瓦垄暗示：四条垂脊（沿坡面的细 box），定位到旋转后的四棱中点
    roof.set_color("tile_dark")
    for k in range(4):
        ang = 45.0 + k * 90.0
        mx = math.cos(math.radians(ang)) * eave * 0.5
        my = math.sin(math.radians(ang)) * eave * 0.5
        mz = (roof_base + roof_apex) * 0.5
        ridge2 = Mesh("r2")
        ridge2.set_color("tile_dark")
        ridge2.box((mx, my, mz), (0.14, 0.14, (roof_apex - roof_base) * 0.95))
        ridge2.rotate(rz=ang + 90, ry=0, rx=0)
        roof.merge(ridge2)

    # --- 顶宝珠 ---
    roof.set_color("gold")
    roof.icosphere((0, 0, roof_apex + 0.10), 0.14, subdiv=0)
    roof.set_color("tile_dark")
    roof.cylinder((0, 0, roof_apex - 0.05), 0.08, 0.10, 0.16, segments=6)

    return [(wood, "M_Palette_Wood"), (roof, "M_Palette_Opaque")]


# --------------------------------------------------------------------------
# 太鼓桥（Kyobashi）— 拱形木桥
# --------------------------------------------------------------------------

def build_kyobashi(ctx):
    rng = ctx["rng"]
    deck = Mesh("bridge_deck")
    rail = Mesh("bridge_rail")
    span = 6.8          # 桥长（沿 Y）
    arch_h = 0.9        # 拱高
    width = 2.2         # 桥宽（沿 X）
    segs = 9

    def arch_z(t):
        # t in [0,1] 沿桥长；半正弦拱
        return arch_h * math.sin(math.pi * t)

    # --- 拱形桥面（9 段）---
    deck.set_color("wood")
    for i in range(segs):
        t0 = i / segs
        t1 = (i + 1) / segs
        y0 = -span * 0.5 + span * t0
        y1 = -span * 0.5 + span * t1
        z0 = arch_z(t0)
        z1 = arch_z(t1)
        ym = (y0 + y1) * 0.5
        zm = (z0 + z1) * 0.5
        seg_len = math.hypot(y1 - y0, z1 - z0)
        tilt = math.degrees(math.atan2(z1 - z0, y1 - y0))
        seg = Mesh("seg")
        seg.set_color("wood")
        seg.set_tint_fn(tint_height("z", -0.1, 0.1, dark=0.85, bright=1.05))
        seg.box((0, 0, 0), (width, seg_len * 1.02, 0.12))
        # 绕 X 轴倾斜对齐拱切线（注意 +Z 上、+Y 北：绕 X 旋转改变 YZ）
        seg.rotate(rz=0, ry=0, rx=-tilt)
        seg.translate(0, ym, zm)
        deck.merge(seg)
    deck.set_tint_fn(None)

    # --- 桥面横向防滑条 ---
    deck.set_color("wood_dark")
    for i in range(segs + 1):
        t = i / segs
        y = -span * 0.5 + span * t
        z = arch_z(t)
        deck.box((0, y, z + 0.07), (width * 0.98, 0.08, 0.04))

    # --- 桥下支撑梁（两根纵梁）---
    deck.set_color("wood_dark")
    for sx in (-1, 1):
        for i in range(segs):
            t0 = i / segs
            t1 = (i + 1) / segs
            y0 = -span * 0.5 + span * t0
            y1 = -span * 0.5 + span * t1
            z0 = arch_z(t0) - 0.18
            z1 = arch_z(t1) - 0.18
            ym, zm = (y0 + y1) * 0.5, (z0 + z1) * 0.5
            seg_len = math.hypot(y1 - y0, z1 - z0)
            tilt = math.degrees(math.atan2(z1 - z0, y1 - y0))
            beam = Mesh("beam")
            beam.set_color("wood_dark")
            beam.box((sx * (width * 0.42), 0, 0), (0.14, seg_len, 0.16))
            beam.rotate(rz=0, ry=0, rx=-tilt)
            beam.translate(0, ym, zm)
            deck.merge(beam)

    # --- 两侧栏干（拱形扶手 + 望柱）---
    for sx in (-1, 1):
        rx = sx * (width * 0.5 - 0.06)
        # 扶手：沿拱的斜置 box 序列
        rail.set_color("torii_red")
        rail.set_tint_fn(tint_height("z", 0, arch_h + 0.6, dark=0.85, bright=1.05))
        for i in range(segs):
            t0 = i / segs
            t1 = (i + 1) / segs
            y0 = -span * 0.5 + span * t0
            y1 = -span * 0.5 + span * t1
            z0 = arch_z(t0) + 0.62
            z1 = arch_z(t1) + 0.62
            ym, zm = (y0 + y1) * 0.5, (z0 + z1) * 0.5
            seg_len = math.hypot(y1 - y0, z1 - z0)
            tilt = math.degrees(math.atan2(z1 - z0, y1 - y0))
            h = Mesh("h")
            h.set_color("torii_red")
            h.box((rx, 0, 0), (0.12, seg_len * 1.02, 0.12))
            h.rotate(rz=0, ry=0, rx=-tilt)
            h.translate(0, ym, zm)
            rail.merge(h)
        rail.set_tint_fn(None)
        # 望柱：每段边界一根，高度随拱变化
        rail.set_color("torii_red")
        for i in range(segs + 1):
            if i % 2 == 1 and i not in (0, segs):
                continue  # 隔一根放一根，省面数
            t = i / segs
            y = -span * 0.5 + span * t
            zb = arch_z(t)
            post = Mesh("post")
            post.set_color("torii_red")
            post.cylinder((rx, y, zb), 0.055, 0.05, 0.66, segments=6,
                          cap_top=True, cap_bottom=False)
            rail.merge(post)
        # 柱头球
        rail.set_color("gold")
        for i in (0, segs):
            t = i / segs
            y = -span * 0.5 + span * t
            zb = arch_z(t) + 0.66
            rail.icosphere((rx, y, zb), 0.075, subdiv=0)

    # --- 桥两端接地石 ---
    deck.set_color("stone_dark")
    for sy in (-1, 1):
        deck.box((0, sy * (span * 0.5 + 0.15), 0.06), (width + 0.3, 0.5, 0.14))

    return [(deck, "M_Palette_Wood"), (rail, "M_Palette_Wood")]


# --------------------------------------------------------------------------
# 茶摊（Tea Stall）
# --------------------------------------------------------------------------

def build_tea_stall(ctx):
    rng = ctx["rng"]
    wood = Mesh("stall_wood")
    cloth = Mesh("stall_cloth")
    glow = Mesh("stall_glow")
    W, D = 5.0, 4.0         # 占地
    post_h = 2.3
    roof_z = 2.55

    # --- 四柱（前低后高，形成单坡顶）---
    posts = [(-W/2+0.15, -D/2+0.15), (W/2-0.15, -D/2+0.15),
             (-W/2+0.15, D/2-0.15), (W/2-0.15, D/2-0.15)]
    wood.set_color("wood_dark")
    for i, (px, py) in enumerate(posts):
        h = post_h if py < 0 else post_h + 0.35   # 后侧（+Y）更高
        wood.set_tint_fn(tint_height("z", 0, h, dark=0.78, bright=1.04))
        wood.cylinder((px, py, 0), 0.09, 0.08, h, segments=6, cap_top=True, cap_bottom=True)
    wood.set_tint_fn(None)

    # --- 单坡布帘顶 ---
    cloth.set_color("cloth")
    cloth.set_tint_fn(tint_height("z", roof_z - 0.2, roof_z + 0.4, dark=0.8, bright=1.08))
    roof = Mesh("roofslab")
    roof.set_color("cloth")
    roof.box((0, 0, 0), (W + 0.5, D + 0.5, 0.08))
    tilt = math.degrees(math.atan2(0.35, D))
    roof.rotate(rz=0, ry=0, rx=tilt)
    roof.translate(0, 0, roof_z + 0.1)
    cloth.merge(roof)
    cloth.set_tint_fn(None)
    # 顶椽木
    wood.set_color("wood")
    for k in range(5):
        fx = -W/2 + 0.3 + k * (W - 0.6) / 4
        wood.box((fx, 0, roof_z - 0.02), (0.09, D + 0.3, 0.10))

    # --- 前檐暖帘（noren，多条竖布）---
    cloth.set_color("blue_kimono")
    noren_z = roof_z - 0.05
    for k in range(6):
        nx = -W/2 + 0.4 + k * (W - 0.8) / 5
        n = Mesh("noren")
        n.set_color("blue_kimono")
        n.quad((nx - 0.28, -D/2 - 0.02, noren_z),
               (nx + 0.28, -D/2 - 0.02, noren_z),
               (nx + 0.28, -D/2 - 0.02, noren_z - 0.62),
               (nx - 0.28, -D/2 - 0.02, noren_z - 0.62),
               double=True)
        cloth.merge(n)

    # --- 柜台（南向 -Y）---
    wood.set_color("wood")
    wood.box((0, -D/2 + 0.55, 0.95), (W - 0.6, 0.5, 0.10))   # 台面
    wood.set_color("wood_dark")
    wood.box((0, -D/2 + 0.55, 0.47), (W - 0.7, 0.42, 0.90))   # 柜体
    # 台面上茶碗若干
    wood.set_color("white_robe")
    for k in range(3):
        wood.cylinder((-1.2 + k * 1.2, -D/2 + 0.55, 1.0), 0.07, 0.06, 0.09,
                      segments=8, cap_top=True)

    # --- 长凳 ×2（柜台外侧）---
    wood.set_color("wood")
    for sy in (-1, 1):
        bx = sy * 1.35
        wood.box((bx, -D/2 - 0.55, 0.42), (1.5, 0.34, 0.07))   # 凳面
        wood.set_color("wood_dark")
        for lx in (-0.6, 0.6):
            wood.box((bx + lx, -D/2 - 0.55, 0.20), (0.10, 0.30, 0.40))
        wood.set_color("wood")

    # --- 后墙货架 ---
    wood.set_color("wood_dark")
    wood.box((0, D/2 - 0.2, 1.1), (W - 0.8, 0.16, 0.10))
    wood.box((0, D/2 - 0.2, 1.6), (W - 0.8, 0.16, 0.10))

    # --- 悬挂灯笼（自发光，前檐两侧）---
    for sx in (-1, 1):
        lx = sx * (W/2 - 0.4)
        ly = -D/2 - 0.05
        lz = noren_z - 0.15
        # 吊绳
        wood.set_color("ink")
        wood.cylinder((lx, ly, lz), 0.015, 0.015, 0.25, segments=4)
        # 灯笼体（发光）
        glow.set_color("paper_lamp")
        glow.cylinder((lx, ly, lz - 0.42), 0.16, 0.16, 0.42, segments=8,
                      cap_top=True, cap_bottom=True)
        # 灯笼上下箍
        wood.set_color("torii_red")
        wood.cylinder((lx, ly, lz - 0.42), 0.17, 0.17, 0.04, segments=8)
        wood.cylinder((lx, ly, lz - 0.02), 0.17, 0.17, 0.04, segments=8)

    # --- 地面踏板 ---
    wood.set_color("wood_dark")
    wood.box((0, 0, 0.03), (W - 0.3, D - 0.3, 0.06))

    parts = [(wood, "M_Palette_Wood"), (cloth, "M_Palette_Opaque")]
    if not glow.is_empty():
        parts.append((glow, "M_Lantern_Glow"))
    return parts


# --------------------------------------------------------------------------
# 枯山水（Karesansui）— 白川砂 + 围石 + 缘侧
# --------------------------------------------------------------------------

def build_karesansui(ctx):
    rng = ctx["rng"]
    sand = Mesh("karesansui_sand")
    rock = Mesh("karesansui_rock")
    wood = Mesh("karesansui_wood")
    W, D = 11.0, 10.0

    # 石组中心（耙纹同心圆的圆心）
    cx0, cy0 = 1.2, 0.6

    def rake(x, y, z):
        """耙纹位移：围绕石组的同心圆 + 外围平行直纹，振幅 0.035m。"""
        d = math.hypot(x - cx0, y - cy0)
        if d < 4.2:
            zz = 0.035 * math.sin(d * 5.2)
        else:
            zz = 0.030 * math.sin(x * 3.4)
        # 边缘轻微抬升（砂堆边界）
        ex = max(0.0, (abs(x) - W * 0.44)) * 0.35
        ey = max(0.0, (abs(y) - D * 0.44)) * 0.35
        return (x, y, z + zz + ex + ey)

    # --- 白川砂地面（耙纹）---
    sand.set_color("sand")
    sand.set_tint_fn(tint_height("z", -0.04, 0.06, dark=0.9, bright=1.06))
    sand.plane((0, 0, 0.0), W, D, seg_x=22, seg_y=20, normal="z", displace_fn=rake)
    sand.set_tint_fn(None)

    # --- 主石组（中央 3 块，象征蓬莱）---
    main_stones = [
        (cx0, cy0, 0.62, 0.85, 0.0),
        (cx0 - 1.05, cy0 + 0.5, 0.42, 0.6, 0.4),
        (cx0 + 0.95, cy0 - 0.55, 0.36, 0.5, 0.9),
    ]
    for (sx, sy, sr, sh, rot) in main_stones:
        st = Mesh("stone")
        st.set_color("stone")
        st.set_tint_fn(tint_ao_bottom("z", 0.0, sh * 1.2, dark=0.55))
        st.icosphere((sx, sy, sh * 0.55), sr, subdiv=1, squash=sh / (sr * 2))
        st.jitter(sr * 0.16, rng)
        st.rotate(rz=rot * 57.0)
        rock.merge(st)
    rock.set_tint_fn(None)

    # --- 围石（边缘 12 块，界定砂地范围）---
    edge_positions = []
    n_edge = 12
    for i in range(n_edge):
        ang = 2 * math.pi * i / n_edge + rng.range(-0.12, 0.12)
        ex = math.cos(ang) * (W * 0.46)
        ey = math.sin(ang) * (D * 0.46)
        edge_positions.append((ex, ey))
    for (ex, ey) in edge_positions:
        st = Mesh("estone")
        r = rng.range(0.20, 0.34)
        st.set_color("stone_dark")
        st.set_tint_fn(tint_ao_bottom("z", 0.0, r * 2, dark=0.5))
        st.icosphere((ex, ey, r * 0.5), r, subdiv=0, squash=rng.range(0.6, 0.9))
        st.jitter(r * 0.18, rng)
        # 偶尔点缀苔痕
        rock.merge(st)
    rock.set_tint_fn(None)

    # 苔痕斑（少量石头顶部）
    for (ex, ey) in edge_positions[:4]:
        moss = Mesh("moss")
        moss.set_color("moss")
        moss.icosphere((ex, ey, 0.22), 0.16, subdiv=0, squash=0.35)
        moss.jitter(0.03, rng)
        rock.merge(moss)

    # --- 缘侧木台（西侧 -X，供源藏坐着凿石）---
    wood.set_color("wood")
    wood.set_tint_fn(tint_height("z", 0, 0.4, dark=0.78, bright=1.04))
    wood.box((-W * 0.5 + 0.6, 0, 0.20), (1.2, D * 0.6, 0.40))
    wood.set_tint_fn(None)
    # 缘侧地板条
    wood.set_color("wood_dark")
    for k in range(6):
        fy = -D * 0.3 + 0.15 + k * (D * 0.6 - 0.3) / 5
        wood.box((-W * 0.5 + 0.6, fy, 0.41), (1.15, 0.16, 0.03))
    # 缘侧支撑脚
    wood.set_color("wood_dark")
    for fy in (-D * 0.28, 0, D * 0.28):
        wood.box((-W * 0.5 + 0.6, fy, 0.10), (1.1, 0.14, 0.20))

    # --- 砂地边界木框（防止砂"流出"）---
    wood.set_color("wood_dark")
    for sy in (-1, 1):
        wood.box((0, sy * D * 0.5, 0.06), (W + 0.2, 0.14, 0.12))
    for sx in (-1, 1):
        wood.box((sx * W * 0.5, 0, 0.06), (0.14, D + 0.2, 0.12))

    return [(sand, "M_Palette_Opaque"), (rock, "M_Palette_Stone"), (wood, "M_Palette_Wood")]


# --------------------------------------------------------------------------
# 注册表
# --------------------------------------------------------------------------

ASSETS = {
    "asset_torii_main": {
        "file": "SM_Torii_Gate_Main.glb", "build": build_torii_main,
        "materials": ["M_Palette_Wood"], "tri_budget": 900,
    },
    "asset_torii_small": {
        "file": "SM_Torii_Gate_Small.glb", "build": build_torii_small,
        "materials": ["M_Palette_Wood"], "tri_budget": 500,
    },
    "asset_azumaya": {
        "file": "SM_Azumaya_Pavilion.glb", "build": build_azumaya,
        "materials": ["M_Palette_Wood", "M_Palette_Opaque"], "tri_budget": 2400,
    },
    "asset_kyobashi": {
        "file": "SM_Kyobashi_Bridge.glb", "build": build_kyobashi,
        "materials": ["M_Palette_Wood"], "tri_budget": 1400,
    },
    "asset_tea_stall": {
        "file": "SM_Tea_Stall.glb", "build": build_tea_stall,
        "materials": ["M_Palette_Wood", "M_Palette_Opaque", "M_Lantern_Glow"],
        "tri_budget": 1600,
        "parts": {"body": 0, "cloth": 1, "glow": 2},
    },
    "asset_karesansui_frame": {
        "file": "SM_Karesansui_Frame.glb", "build": build_karesansui,
        "materials": ["M_Palette_Opaque", "M_Palette_Stone", "M_Palette_Wood"],
        "tri_budget": 2200,
        "parts": {"sand": 0, "rock": 1, "wood": 2},
    },
}
