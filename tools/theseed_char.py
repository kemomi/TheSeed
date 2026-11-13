"""
theseed_char.py — 樱庭·离宫「角色与敌人」程序化资产（含骨骼蒙皮与动画）

坐标系：右手系 +X东 +Y北 +Z上，单位米，脚底贴 z=0，角色面向 +Y（北）。
命名约定：.R 在 +X（角色右手侧），.L 在 -X（角色左手侧）。

本模块提供两类资产：
  A) skinned 角色（含骨骼 + 蒙皮 + 动画）：通过 assemble(doc, ctx, tex, matfn) 直接装配
  B) 静态配件/武器（无骨骼）：通过普通 build(ctx) -> [(Mesh, matname)] 接口

规格来源：03_ArtAssetSpec_Procedural.md §2.4；06_Animation_Spec.md。
"""

import math
from theseed_geo import (
    Mesh, Rng, derive_seed, m4_identity, m4_mul, m4_translate, m4_invert,
    quat_from_axis_angle, tint_height, tint_ao_bottom,
)


# ==========================================================================
# 一、人形骨骼定义（16 根）
# ==========================================================================

# (name, parent_index, local_translation)  —— bind pose，直立，手臂自然下垂(-Z)
BONES = [
    ("Hips",        -1, (0.0,   0.0,  0.90)),   # 0
    ("Spine",        0, (0.0,   0.0,  0.16)),   # 1  world z=1.06
    ("Chest",        1, (0.0,   0.0,  0.20)),   # 2  world z=1.26
    ("Head",         2, (0.0,   0.0,  0.24)),   # 3  world z=1.50
    ("UpperArm.R",   2, (0.16,  0.0,  0.14)),   # 4  肩 world z=1.40
    ("LowerArm.R",   4, (0.0,   0.0, -0.28)),   # 5  肘 world z=1.12
    ("Hand.R",       5, (0.0,   0.0, -0.26)),   # 6  腕 world z=0.86
    ("UpperArm.L",   2, (-0.16, 0.0,  0.14)),   # 7
    ("LowerArm.L",   7, (0.0,   0.0, -0.28)),   # 8
    ("Hand.L",       8, (0.0,   0.0, -0.26)),   # 9
    ("UpperLeg.R",   0, (0.10,  0.0, -0.02)),   # 10 髋 world z=0.88
    ("LowerLeg.R",  10, (0.0,   0.0, -0.42)),   # 11 膝 world z=0.46
    ("Foot.R",      11, (0.0,   0.0, -0.40)),   # 12 踝 world z=0.06
    ("UpperLeg.L",   0, (-0.10, 0.0, -0.02)),   # 13
    ("LowerLeg.L",  13, (0.0,   0.0, -0.42)),   # 14
    ("Foot.L",      14, (0.0,   0.0, -0.40)),   # 15
]
BONE_INDEX = {b[0]: i for i, b in enumerate(BONES)}


def bone_world_matrices(scale=1.0):
    """计算 bind pose 下每根骨骼的世界矩阵（仅平移累积）。"""
    worlds = [None] * len(BONES)
    for i, (name, parent, lt) in enumerate(BONES):
        local = m4_translate(lt[0] * scale, lt[1] * scale, lt[2] * scale)
        worlds[i] = local if parent < 0 else m4_mul(worlds[parent], local)
    return worlds


def bone_world_positions(scale=1.0):
    ws = bone_world_matrices(scale)
    return [(ws[i][12], ws[i][13], ws[i][14]) for i in range(len(BONES))]


# ==========================================================================
# 二、顶点蒙皮绑定
# ==========================================================================

def rebind_by_z(mesh, stops, joints):
    """按顶点世界 z 在 stops（升序阈值）划分的区间内，对相邻两骨骼线性混合权重。

    stops  : [z0, z1, z2, ...]  长度 = len(joints)-1
    joints : [j0, j1, j2, ...]  骨骼索引，顶点 z 越小越偏向 j0
    用于躯干（Hips/Spine/Chest）等跨骨骼部件，使弯腰/转身更自然。
    """
    n = len(mesh.pos)
    if not mesh.skinned:
        mesh._promote_to_skinned()
    new_j = [None] * n
    new_w = [None] * n
    for i in range(n):
        z = mesh.pos[i][2]
        # 找到 z 落在哪个区段
        seg = 0
        while seg < len(stops) and z >= stops[seg]:
            seg += 1
        if seg == 0:
            new_j[i] = (joints[0], 0, 0, 0)
            new_w[i] = (1.0, 0.0, 0.0, 0.0)
        elif seg >= len(stops):
            # z 高于最后一个阈值：完全绑定到最后一根骨骼
            jl = joints[-1]
            new_j[i] = (jl, 0, 0, 0)
            new_w[i] = (1.0, 0.0, 0.0, 0.0)
        else:
            z0 = stops[seg - 1]
            z1 = stops[seg]
            t = (z - z0) / (z1 - z0) if z1 > z0 else 0.0
            t = max(0.0, min(1.0, t))
            ja, jb = joints[seg - 1], joints[seg]
            new_j[i] = (ja, jb, 0, 0)
            new_w[i] = (1.0 - t, t, 0.0, 0.0)
    mesh.jnt = new_j
    mesh.wgt = new_w
    return mesh


def bind_rigid(mesh, joint_index):
    """把「当前尚未绑定」的顶点刚性绑定到单根骨骼，并设状态供后续顶点继承。

    用 len(mesh.jnt) 跟踪已绑定顶点数，只回填新增的未绑定区间，因此：
      - 先建几何后调用（head/eye/horn）：回填全部已有顶点；
      - 多段绑定（arm 上臂→前臂→手）：每段只回填该段新增顶点，
        已绑定段保持不变。
    低模角色的四肢/头/手脚采用此法，稳健且无需逐顶点权重。
    """
    if not mesh.skinned:
        mesh.skinned = True
    bound = len(mesh.jnt)
    total = len(mesh.pos)
    for _ in range(bound, total):
        mesh.jnt.append((joint_index, 0, 0, 0))
        mesh.wgt.append((1.0, 0.0, 0.0, 0.0))
    mesh._joints = (joint_index, 0, 0, 0)
    mesh._weights = (1.0, 0.0, 0.0, 0.0)
    return mesh


# ==========================================================================
# 三、人形几何生成（参数化）
# ==========================================================================

class HumanoidParams:
    def __init__(self, **kw):
        self.height = kw.get("height", 1.70)
        self.build = kw.get("build", "normal")        # slim/normal/stocky/armored
        self.skin = kw.get("skin", "skin")
        self.robe = kw.get("robe", "blue_kimono")
        self.robe2 = kw.get("robe2", "white_robe")
        self.hair = kw.get("hair", "hair_black")
        self.hair_style = kw.get("hair_style", "short")  # short/long/topknot/hood/oni
        self.has_hakama = kw.get("has_hakama", True)
        self.limb = kw.get("limb", None)              # 覆盖四肢颜色（如鬼肌/甲）
        self.armored = kw.get("armored", False)
        self.horn = kw.get("horn", False)
        self.eye_glow = kw.get("eye_glow", None)


def _limb_radius(p):
    return {"slim": 0.055, "normal": 0.07, "stocky": 0.095, "armored": 0.09}[p.build]


def build_humanoid(p, rng):
    """返回 {part_name: (Mesh, material_name)} 有序字典，已完成蒙皮绑定。

    part_name 用于装配时区分需要单独 emissive 的部件（如 eye_glow）。
    """
    S = p.height / 1.70
    wp = bone_world_positions(S)
    def W(bname):
        return wp[BONE_INDEX[bname]]
    lr = _limb_radius(p)
    limb_col = p.limb or p.skin
    parts = {}

    body = Mesh("body")

    # --- 骨盆 / 腰（绑 Hips）---
    bind_rigid(body, BONE_INDEX["Hips"])
    body.set_color(p.robe)
    hips = W("Hips")
    body.set_tint_fn(tint_ao_bottom("z", hips[2] - 0.2, 0.3, dark=0.72))
    body.box((0, 0, hips[2] + 0.02 * S), (0.30 * S, 0.20 * S, 0.22 * S))
    body.set_tint_fn(None)

    # --- 躯干（胸腹，跨 Spine/Chest，按 z 混合权重）---
    torso = Mesh("torso")
    torso.set_color(p.robe)
    spine_z = W("Spine")[2]
    chest_z = W("Chest")[2]
    torso_h = (chest_z + 0.16 * S) - (hips[2] - 0.02)
    torso_cz = (hips[2] - 0.02 + chest_z + 0.16 * S) * 0.5
    # 胸宽于腰
    torso.set_tint_fn(tint_height("z", hips[2], chest_z + 0.2, dark=0.82, bright=1.05))
    torso.box((0, 0, torso_cz), (0.34 * S, 0.21 * S, torso_h))
    # 肩部加宽
    bind_rigid(torso, BONE_INDEX["Chest"])
    torso.box((0, 0, chest_z + 0.10 * S), (0.42 * S, 0.20 * S, 0.14 * S))
    torso.set_tint_fn(None)
    # 交领（和服 V 领）——用两块斜置薄板
    torso.set_color(p.robe2)
    for sx in (-1, 1):
        lapel = Mesh("lapel")
        lapel.set_color(p.robe2)
        lapel.box((0, 0, 0), (0.10 * S, 0.03 * S, 0.34 * S))
        lapel.rotate(rz=0, ry=sx * 18.0, rx=0)
        lapel.translate(sx * 0.05 * S, -0.10 * S, chest_z + 0.02 * S)
        bind_rigid(lapel, BONE_INDEX["Chest"])
        torso.merge(lapel)
    rebind_by_z(torso, [spine_z, chest_z], [BONE_INDEX["Hips"], BONE_INDEX["Spine"], BONE_INDEX["Chest"]])
    parts["torso"] = (torso, "M_Palette_Opaque")

    # --- 和服下摆 / 袴（hakama，从腰到膝的筒裙）---
    if p.has_hakama:
        haka = Mesh("hakama")
        haka.set_color(p.robe2 if p.build != "armored" else p.robe)
        knee_z = W("LowerLeg.R")[2]
        haka.set_tint_fn(tint_height("z", knee_z, hips[2], dark=0.8, bright=1.04))
        # 用圆台下宽上窄模拟裙摆
        haka.cylinder((0, 0, knee_z), 0.24 * S, 0.19 * S, hips[2] + 0.02 - knee_z,
                      segments=8, cap_top=False, cap_bottom=True)
        haka.set_tint_fn(None)
        # 下摆绑 Hips（裙摆随髋），膝部权重低
        rebind_by_z(haka, [spine_z], [BONE_INDEX["Hips"], BONE_INDEX["Spine"]])
        parts["hakama"] = (haka, "M_Palette_Opaque")

    # --- 头（绑 Head）---
    head = Mesh("head")
    head.set_color(p.skin)
    hz = W("Head")[2]
    head_cz = hz + 0.11 * S
    head.set_tint_fn(tint_height("z", hz, hz + 0.22 * S, dark=0.9, bright=1.05))
    head.icosphere((0, 0, head_cz), 0.115 * S, subdiv=1, squash=1.15)
    head.set_tint_fn(None)
    # 脖子
    bind_rigid(head, BONE_INDEX["Head"])
    head.set_color(p.skin)
    head.cylinder((0, 0, chest_z + 0.14 * S), 0.05 * S, 0.05 * S, hz - chest_z - 0.10 * S,
                  segments=6)
    # 头发
    hair = _build_hair(p, rng, S, head_cz)
    if hair is not None:
        head.merge(hair)
    # 眼睛发光体（鬼/武者）
    if p.eye_glow:
        eye = Mesh("eye")
        eye.set_color("paper_lamp")
        for sx in (-1, 1):
            eye.icosphere((sx * 0.045 * S, -0.09 * S, head_cz + 0.02 * S),
                          0.018 * S, subdiv=0)
        bind_rigid(eye, BONE_INDEX["Head"])
        parts["eye_glow"] = (eye, "M_Crystal_Glow")
    parts["head"] = (head, "M_Palette_Opaque")

    # --- 角（鬼）---
    if p.horn:
        horn = Mesh("horn")
        horn.set_color("horn")
        for sx in (-1, 1):
            horn.cone((sx * 0.06 * S, 0.01 * S, head_cz + 0.10 * S),
                      0.035 * S, 0.16 * S, segments=5, axis="z")
        bind_rigid(horn, BONE_INDEX["Head"])
        horn.rotate(rz=0, ry=0, rx=0)
        parts["horn"] = (horn, "M_Palette_Opaque")

    # --- 双臂 ---
    for side in ("R", "L"):
        sx = 1 if side == "R" else -1
        ua_i = BONE_INDEX["UpperArm." + side]
        la_i = BONE_INDEX["LowerArm." + side]
        hd_i = BONE_INDEX["Hand." + side]
        sh = W("UpperArm." + side)
        el = W("LowerArm." + side)
        wr = W("Hand." + side)

        arm = Mesh("arm_" + side)
        # 上臂
        bind_rigid(arm, ua_i)
        arm.set_color(limb_col if not p.armored else p.robe)
        arm.set_tint_fn(tint_height("z", el[2], sh[2], dark=0.85, bright=1.03))
        arm.cylinder((sh[0], sh[1], el[2]), lr * S, lr * 1.1 * S, sh[2] - el[2],
                     segments=6, cap_top=True, cap_bottom=True, axis="z")
        # 肩甲（武者）
        if p.armored:
            arm.set_color("armor_red")
            arm.box((sh[0], sh[1], sh[2] - 0.02 * S), (0.18 * S, 0.16 * S, 0.10 * S))
        arm.set_tint_fn(None)
        # 前臂
        bind_rigid(arm, la_i)
        arm.set_color(limb_col if not p.armored else p.robe2)
        arm.cylinder((el[0], el[1], wr[2]), lr * 0.85 * S, lr * S, el[2] - wr[2],
                     segments=6, cap_top=True, cap_bottom=True, axis="z")
        arm.set_tint_fn(None)
        # 手
        bind_rigid(arm, hd_i)
        arm.set_color(limb_col)
        arm.box((wr[0], wr[1], wr[2] - 0.05 * S), (0.07 * S, 0.05 * S, 0.11 * S))
        parts["arm_" + side] = (arm, "M_Palette_Opaque")

    # --- 双腿 ---
    for side in ("R", "L"):
        sx = 1 if side == "R" else -1
        ul_i = BONE_INDEX["UpperLeg." + side]
        ll_i = BONE_INDEX["LowerLeg." + side]
        ft_i = BONE_INDEX["Foot." + side]
        hp = W("UpperLeg." + side)
        kn = W("LowerLeg." + side)
        an = W("Foot." + side)

        leg = Mesh("leg_" + side)
        leg_col = p.robe2 if (p.has_hakama and not p.armored) else (limb_col if not p.armored else p.robe)
        # 大腿（若有袴则被裙摆遮住，仍生成以保绑定完整）
        bind_rigid(leg, ul_i)
        leg.set_color(leg_col)
        leg.set_tint_fn(tint_height("z", kn[2], hp[2], dark=0.78, bright=1.0))
        leg.cylinder((hp[0], hp[1], kn[2]), lr * 1.15 * S, lr * 1.25 * S, hp[2] - kn[2],
                     segments=6, cap_top=True, cap_bottom=True, axis="z")
        leg.set_tint_fn(None)
        # 小腿
        bind_rigid(leg, ll_i)
        leg.set_color(limb_col if not p.armored else p.robe)
        leg.cylinder((kn[0], kn[1], an[2]), lr * 0.8 * S, lr * 1.05 * S, kn[2] - an[2],
                     segments=6, cap_top=True, cap_bottom=True, axis="z")
        # 胫甲（武者）
        if p.armored:
            leg.set_color("armor_dark")
            leg.box((kn[0], kn[1] - 0.05 * S, (kn[2] + an[2]) * 0.5),
                    (0.11 * S, 0.08 * S, (kn[2] - an[2]) * 0.8))
        leg.set_tint_fn(None)
        # 脚（草鞋/足袋，朝 +Y 前）
        bind_rigid(leg, ft_i)
        leg.set_color("ink" if not p.armored else "armor_dark")
        leg.box((an[0], an[1] + 0.04 * S, 0.035 * S), (0.09 * S, 0.20 * S, 0.07 * S))
        parts["leg_" + side] = (leg, "M_Palette_Opaque")

    # 骨盆并入 body（body 目前可能只有腰块）
    if not body.is_empty():
        parts["hips"] = (body, "M_Palette_Opaque")

    return parts


def _build_hair(p, rng, S, head_cz):
    """按发型生成头发网格，绑 Head。返回 Mesh 或 None。"""
    hair = Mesh("hair")
    hair.set_color(p.hair)
    bind_rigid(hair, BONE_INDEX["Head"])
    style = p.hair_style
    hr = 0.125 * S
    if style == "short":
        hair.set_tint_fn(tint_height("z", head_cz - 0.05, head_cz + 0.15, dark=0.8, bright=1.05))
        hair.icosphere((0, 0.01 * S, head_cz + 0.02 * S), hr, subdiv=1, squash=1.05)
        # 削掉下半：用一个下沉的球差集太贵，改为只保留——低模直接整球压扁即可
        hair.set_tint_fn(None)
    elif style == "long":
        hair.set_tint_fn(tint_height("z", head_cz - 0.35, head_cz + 0.15, dark=0.75, bright=1.05))
        hair.icosphere((0, 0.01 * S, head_cz + 0.02 * S), hr, subdiv=1, squash=1.05)
        # 后垂长发
        hair.cylinder((0, 0.06 * S, head_cz - 0.30 * S), 0.10 * S, 0.07 * S,
                      0.34 * S, segments=6, cap_top=True, cap_bottom=True, axis="z")
        hair.set_tint_fn(None)
    elif style == "topknot":  # 武士发髻
        hair.icosphere((0, 0.01 * S, head_cz + 0.02 * S), hr, subdiv=1, squash=1.0)
        hair.icosphere((0, 0.02 * S, head_cz + 0.15 * S), 0.055 * S, subdiv=0)
        hair.cylinder((0, 0.02 * S, head_cz + 0.10 * S), 0.03 * S, 0.03 * S, 0.06 * S,
                      segments=5, axis="z")
    elif style == "hood":  # 巫女/斗笠
        hair.set_color(p.robe2)
        hair.icosphere((0, 0, head_cz + 0.03 * S), hr * 1.15, subdiv=1, squash=0.9)
    elif style == "oni":  # 鬼的乱发
        hair.set_tint_fn(tint_height("z", head_cz - 0.1, head_cz + 0.2, dark=0.7, bright=1.0))
        hair.icosphere((0, 0, head_cz + 0.02 * S), hr, subdiv=1, squash=1.0)
        hair.jitter(0.03 * S, rng)
        hair.set_tint_fn(None)
    else:
        return None
    return hair


# ==========================================================================
# 四、动画生成
# ==========================================================================

def _swing(bone, axis, amp_deg, period, n, phase=0.0, loops=1, base_deg=0.0):
    """绕 axis 正弦摆动，返回 (bone, path, times, quats)。"""
    times = [period * loops * i / (n - 1) for i in range(n)]
    quats = []
    for t in times:
        ang = base_deg + amp_deg * math.sin(2 * math.pi * (t / period) + phase)
        quats.append(quat_from_axis_angle(axis, ang))
    return (bone, "rotation", times, quats)


def _hold(bone, quat, dur, n=2):
    times = [dur * i / (n - 1) for i in range(n)]
    return (bone, "rotation", times, [list(quat) for _ in times])


def anim_npc_idle(dur=3.0):
    """待机：胸廓呼吸 + 双臂微摆 + 头部轻晃。循环。"""
    n = 13
    return [
        _swing("Chest", (1, 0, 0), 1.6, dur, n, phase=0),
        _swing("Spine", (1, 0, 0), 1.0, dur, n, phase=0.3),
        _swing("Head", (0, 1, 0), 2.2, dur * 1.3, n, phase=0.5),
        _swing("UpperArm.R", (0, 1, 0), 2.0, dur, n, phase=0.2),
        _swing("UpperArm.L", (0, 1, 0), 2.0, dur, n, phase=math.pi + 0.2),
        _swing("Hips", (0, 0, 1), 0.6, dur * 1.5, n, phase=0),
    ]


def anim_npc_wave(dur=2.4):
    """挥手致意：右臂侧抬，前臂摆动。非循环（单次）。"""
    n = 13
    up = quat_from_axis_angle((0, 1, 0), -75)   # 右上臂侧抬
    tracks = [
        _hold("UpperArm.R", quat_from_axis_angle((0, 1, 0), 0), dur * 0.18, 2),
    ]
    # 抬起到位 + 摆动 + 放下：用分段关键帧
    times = [0.0, dur * 0.2, dur * 0.35, dur * 0.5, dur * 0.65, dur * 0.8, dur]
    ua_quats = [
        quat_from_axis_angle((0, 1, 0), 0),
        quat_from_axis_angle((0, 1, 0), -70),
        quat_from_axis_angle((0, 1, 0), -78),
        quat_from_axis_angle((0, 1, 0), -70),
        quat_from_axis_angle((0, 1, 0), -78),
        quat_from_axis_angle((0, 1, 0), -70),
        quat_from_axis_angle((0, 1, 0), 0),
    ]
    la_times = times
    la_quats = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), -20),
        quat_from_axis_angle((1, 0, 0), 15),
        quat_from_axis_angle((1, 0, 0), -20),
        quat_from_axis_angle((1, 0, 0), 15),
        quat_from_axis_angle((1, 0, 0), -20),
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    head_quats = [
        quat_from_axis_angle((0, 1, 0), 0),
        quat_from_axis_angle((0, 0, 1), 6),
        quat_from_axis_angle((0, 0, 1), -6),
        quat_from_axis_angle((0, 0, 1), 6),
        quat_from_axis_angle((0, 0, 1), -6),
        quat_from_axis_angle((0, 0, 1), 4),
        quat_from_axis_angle((0, 0, 1), 0),
    ]
    _ = up
    _ = tracks
    return [
        ("UpperArm.R", "rotation", times, ua_quats),
        ("LowerArm.R", "rotation", la_times, la_quats),
        ("Head", "rotation", times, head_quats),
    ]


def anim_npc_talk(dur=2.0):
    """说话：头部点头 + 右手小幅手势。循环。"""
    n = 9
    return [
        _swing("Head", (1, 0, 0), 4.0, dur * 0.6, n, phase=0),
        _swing("Head", (0, 1, 0), 3.0, dur, n, phase=0.7),
        _swing("UpperArm.R", (1, 0, 0), 8.0, dur, n, phase=0),
        _swing("LowerArm.R", (1, 0, 0), 12.0, dur * 0.7, n, phase=0.4),
        _swing("Chest", (0, 1, 0), 2.0, dur, n, phase=0.2),
    ]


def anim_npc_bow(dur=2.2):
    """鞠躬：脊柱前屈再回正。单次。"""
    times = [0.0, dur * 0.35, dur * 0.6, dur]
    spine_q = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), 32),
        quat_from_axis_angle((1, 0, 0), 32),
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    chest_q = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), 14),
        quat_from_axis_angle((1, 0, 0), 14),
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    head_q = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), 12),
        quat_from_axis_angle((1, 0, 0), 12),
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    return [
        ("Spine", "rotation", times, spine_q),
        ("Chest", "rotation", times, chest_q),
        ("Head", "rotation", times, head_q),
    ]


def anim_npc_walk(dur=1.0):
    """行走：四肢交替摆动，循环。"""
    n = 13
    return [
        _swing("UpperLeg.R", (1, 0, 0), 24, dur, n, phase=0),
        _swing("UpperLeg.L", (1, 0, 0), 24, dur, n, phase=math.pi),
        _swing("LowerLeg.R", (1, 0, 0), -18, dur, n, phase=0.6),
        _swing("LowerLeg.L", (1, 0, 0), -18, dur, n, phase=math.pi + 0.6),
        _swing("UpperArm.R", (1, 0, 0), 18, dur, n, phase=math.pi),
        _swing("UpperArm.L", (1, 0, 0), 18, dur, n, phase=0),
        _swing("Hips", (0, 0, 1), 2.5, dur * 0.5, n, phase=0),
        _swing("Hips", (1, 0, 0), 1.5, dur * 0.5, n, phase=0),
    ]


def anim_npc_sit(dur=3.0):
    """坐姿（源藏凿石/椿静坐）：髋膝弯曲保持 + 上身微动。循环。"""
    n = 9
    base_leg = quat_from_axis_angle((1, 0, 0), -80)   # 大腿前抬（坐）
    base_shin = quat_from_axis_angle((1, 0, 0), 75)   # 小腿后折
    tracks = [
        _hold("UpperLeg.R", base_leg, dur, 2),
        _hold("UpperLeg.L", base_leg, dur, 2),
        _hold("LowerLeg.R", base_shin, dur, 2),
        _hold("LowerLeg.L", base_shin, dur, 2),
        _swing("Spine", (1, 0, 0), 3.0, dur, n, phase=0),
        _swing("Chest", (1, 0, 0), 2.0, dur * 1.2, n, phase=0.5),
        _swing("UpperArm.R", (1, 0, 0), 6.0, dur * 0.8, n, phase=0),
    ]
    return tracks


def anim_enemy_idle(dur=2.2, fierce=False):
    n = 11
    amp = 3.0 if fierce else 2.2
    return [
        _swing("Chest", (1, 0, 0), amp, dur, n, phase=0),
        _swing("Head", (0, 1, 0), amp + 2, dur * 0.8, n, phase=0.4),
        _swing("UpperArm.R", (1, 0, 0), amp, dur, n, phase=0.2),
        _swing("UpperArm.L", (1, 0, 0), amp, dur, n, phase=math.pi + 0.2),
        _swing("Hips", (0, 0, 1), 1.2, dur * 1.3, n, phase=0),
    ]


def anim_enemy_walk(dur=0.9):
    n = 13
    return [
        _swing("UpperLeg.R", (1, 0, 0), 26, dur, n, phase=0),
        _swing("UpperLeg.L", (1, 0, 0), 26, dur, n, phase=math.pi),
        _swing("LowerLeg.R", (1, 0, 0), -20, dur, n, phase=0.6),
        _swing("LowerLeg.L", (1, 0, 0), -20, dur, n, phase=math.pi + 0.6),
        _swing("UpperArm.R", (1, 0, 0), 20, dur, n, phase=math.pi),
        _swing("UpperArm.L", (1, 0, 0), 20, dur, n, phase=0),
        _swing("Chest", (0, 1, 0), 4, dur, n, phase=0),
    ]


def anim_enemy_attack(dur=1.1):
    """挥砍：右臂高举再劈下，配合躯干扭转。单次。"""
    times = [0.0, dur * 0.35, dur * 0.5, dur * 0.62, dur]
    ua = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), 150),    # 高举过顶
        quat_from_axis_angle((0, 1, 0), -20),
        quat_from_axis_angle((1, 0, 0), -55),    # 劈下
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    la = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), -35),
        quat_from_axis_angle((1, 0, 0), -15),
        quat_from_axis_angle((1, 0, 0), -5),
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    chest = [
        quat_from_axis_angle((0, 0, 1), 0),
        quat_from_axis_angle((0, 0, 1), -18),
        quat_from_axis_angle((0, 0, 1), 12),
        quat_from_axis_angle((0, 0, 1), 20),
        quat_from_axis_angle((0, 0, 1), 0),
    ]
    return [
        ("UpperArm.R", "rotation", times, ua),
        ("LowerArm.R", "rotation", times, la),
        ("Chest", "rotation", times, chest),
        ("Spine", "rotation", times, [quat_from_axis_angle((0, 0, 1), c) for c in (0, -8, 6, 10, 0)]),
    ]


def anim_enemy_hit(dur=0.4):
    """受击后仰。单次。"""
    times = [0.0, dur * 0.3, dur]
    q = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), -16),
        quat_from_axis_angle((1, 0, 0), 0),
    ]
    return [
        ("Chest", "rotation", times, q),
        ("Head", "rotation", times, [quat_from_axis_angle((1, 0, 0), a) for a in (0, -20, 0)]),
    ]


def anim_enemy_die(dur=1.3):
    """倒地：整体后倒 + 四肢松弛。单次，末帧保持。"""
    times = [0.0, dur * 0.4, dur * 0.7, dur]
    hips = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), -35),
        quat_from_axis_angle((1, 0, 0), -75),
        quat_from_axis_angle((1, 0, 0), -88),
    ]
    spine = [
        quat_from_axis_angle((1, 0, 0), 0),
        quat_from_axis_angle((1, 0, 0), -12),
        quat_from_axis_angle((1, 0, 0), -20),
        quat_from_axis_angle((1, 0, 0), -22),
    ]
    return [
        ("Hips", "rotation", times, hips),
        ("Spine", "rotation", times, spine),
        ("UpperArm.R", "rotation", times, [quat_from_axis_angle((0, 1, 0), a) for a in (0, -30, -55, -70)]),
        ("UpperArm.L", "rotation", times, [quat_from_axis_angle((0, 1, 0), a) for a in (0, 30, 55, 70)]),
        ("UpperLeg.R", "rotation", times, [quat_from_axis_angle((1, 0, 0), a) for a in (0, -20, -35, -40)]),
    ]


def anim_busho_guard(dur=2.5):
    """绯甲武者持刀警戒：双手持刀于身前，微幅浮动。循环。"""
    n = 11
    ua_r = quat_from_axis_angle((1, 0, 0), -45)
    ua_l = quat_from_axis_angle((1, 0, 0), -40)
    return [
        _hold("UpperArm.R", ua_r, dur, 2),
        _hold("UpperArm.L", ua_l, dur, 2),
        _hold("LowerArm.R", quat_from_axis_angle((1, 0, 0), -50), dur, 2),
        _hold("LowerArm.L", quat_from_axis_angle((1, 0, 0), -55), dur, 2),
        _swing("Chest", (1, 0, 0), 2.0, dur, n, phase=0),
        _swing("Hips", (0, 0, 1), 1.0, dur * 1.2, n, phase=0),
    ]


# ==========================================================================
# 五、装配 skinned 资产到 GltfDoc
# ==========================================================================

def assemble_skinned(doc, ctx, tex_idx, matfn, params, anim_set, name):
    """把人形装配进 doc：骨骼节点 + skin + 蒙皮网格 + 动画。返回 root 节点索引。

    matfn(mat_name) -> glTF material index（由主程序提供，含调色板纹理绑定）
    """
    p = params
    S = p.height / 1.70
    parts = build_humanoid(p, ctx["rng"])

    # 合并所有非发光部件到一个网格（按材质分组）
    by_mat = {}
    for pname, (mesh, matname) in parts.items():
        by_mat.setdefault(matname, Mesh(name + "_" + matname)).merge(mesh)

    prim_list = []
    for matname in sorted(by_mat.keys()):
        m = by_mat[matname]
        if m.is_empty():
            continue
        prim_list.append((m, matfn(matname)))

    mesh_idx = doc.add_mesh(name, prim_list)

    # 骨骼节点
    worlds = bone_world_matrices(S)
    joint_nodes = []
    for i, (bname, parent, lt) in enumerate(BONES):
        ni = doc.add_node(name + "_" + bname,
                          translation=(lt[0] * S, lt[1] * S, lt[2] * S))
        joint_nodes.append(ni)
    # 设置父子
    for i, (bname, parent, lt) in enumerate(BONES):
        if parent >= 0:
            doc.nodes[joint_nodes[parent]].setdefault("children", []).append(joint_nodes[i])
    # armature 根
    armature = doc.add_node(name + "_armature", children=[joint_nodes[0]])

    ibm = [m4_invert(worlds[i]) for i in range(len(BONES))]
    skin_idx = doc.add_skin(name + "_skin", joint_nodes, ibm, skeleton_root=armature)

    mesh_node = doc.add_node(name, mesh=mesh_idx, skin=skin_idx)
    root = doc.add_node(name + "_root", children=[mesh_node, armature])

    # 动画
    for aname, tracks in anim_set:
        channels = []
        samplers = []
        for si, (bone, path, times, values) in enumerate(tracks):
            tin = doc.add_float_accessor(times)
            vtype = "VEC4" if path == "rotation" else "VEC3"
            vout = doc.add_vec_accessor(values, vtype)
            samplers.append({"input": tin, "output": vout, "interpolation": "LINEAR"})
            channels.append({"sampler": si,
                             "target": {"node": joint_nodes[BONE_INDEX[bone]], "path": path}})
        doc.add_animation(name + "_" + aname, channels, samplers)

    return root


# ==========================================================================
# 六、角色配方（skinned）
# ==========================================================================

NPC_BASE_ANIMS = [
    ("idle", anim_npc_idle()),
    ("wave", anim_npc_wave()),
    ("talk", anim_npc_talk()),
    ("bow", anim_npc_bow()),
    ("walk", anim_npc_walk()),
    ("sit", anim_npc_sit()),
]

SAKURA_ONI_ANIMS = [
    ("idle", anim_enemy_idle(fierce=False)),
    ("walk", anim_enemy_walk()),
    ("attack", anim_enemy_attack()),
    ("hit", anim_enemy_hit()),
    ("die", anim_enemy_die()),
]

HIKABUSHO_ANIMS = [
    ("idle", anim_enemy_idle(fierce=True)),
    ("walk", anim_enemy_walk()),
    ("guard", anim_busho_guard()),
    ("attack", anim_enemy_attack()),
    ("hit", anim_enemy_hit()),
    ("die", anim_enemy_die()),
]


def assemble_npc_base(doc, ctx, tex_idx, matfn):
    p = HumanoidParams(height=1.70, build="normal", skin="skin", robe="blue_kimono",
                       robe2="white_robe", hair="hair_black", hair_style="short")
    return assemble_skinned(doc, ctx, tex_idx, matfn, p, NPC_BASE_ANIMS, "SK_NPC_Base")


def assemble_sakura_oni(doc, ctx, tex_idx, matfn):
    p = HumanoidParams(height=1.40, build="stocky", skin="oni_skin", limb="oni_skin",
                       robe="oni_skin_dark", robe2="oni_skin_dark", hair="oni_skin_dark",
                       hair_style="oni", has_hakama=False, horn=True, eye_glow=True)
    return assemble_skinned(doc, ctx, tex_idx, matfn, p, SAKURA_ONI_ANIMS, "SK_Enemy_SakuraOni")


def assemble_hikabusho(doc, ctx, tex_idx, matfn):
    p = HumanoidParams(height=1.90, build="armored", skin="skin", limb="armor_dark",
                       robe="armor_red", robe2="armor_dark", hair="hair_black",
                       hair_style="topknot", has_hakama=True, armored=True, eye_glow=True)
    return assemble_skinned(doc, ctx, tex_idx, matfn, p, HIKABUSHO_ANIMS, "SK_Enemy_Hikabusho")


# ==========================================================================
# 七、静态配件与武器（普通 build 接口）
# ==========================================================================

def build_hair_variants(ctx):
    """4 种发型网格合并为单文件，供 NPC 换装引用。沿 +X 依次排开。"""
    rng = ctx["rng"]
    out = Mesh("hair_variants")
    styles = ["short", "long", "topknot", "hood"]
    for i, st in enumerate(styles):
        p = HumanoidParams(hair=("hair_black" if st != "hood" else "white_robe"),
                           hair_style=st, robe2="white_robe")
        h = _build_hair(p, rng, 1.0, 0.0)
        if h is not None:
            h.translate(i * 0.5, 0, 0)
            out.merge(h)
    return [(out, "M_Palette_Opaque")]


def build_prop_lantern(ctx):
    """手提灯笼（枫用）：纸罩 + 上下箍 + 提手，含自发光。"""
    body = Mesh("lantern_body")
    glow = Mesh("lantern_glow")
    # 提手
    body.set_color("ink")
    body.torus((0, 0, 0.30), 0.06, 0.012, seg_major=8, seg_minor=5, axis="z")
    # 上下箍
    body.set_color("wood_dark")
    body.cylinder((0, 0, 0.22), 0.075, 0.075, 0.03, segments=8)
    body.cylinder((0, 0, -0.02), 0.075, 0.075, 0.03, segments=8)
    # 纸罩（发光）
    glow.set_color("paper_lamp")
    glow.cylinder((0, 0, 0.0), 0.07, 0.07, 0.22, segments=8, cap_top=False, cap_bottom=False)
    return [(body, "M_Palette_Wood"), (glow, "M_Lantern_Glow")]


def build_prop_hammer(ctx):
    """石匠锤（源藏用）：木柄 + 铁头。"""
    m = Mesh("hammer")
    m.set_color("wood")
    m.cylinder((0, 0, 0), 0.022, 0.02, 0.38, segments=6, axis="z")
    m.set_color("stone_dark")
    m.box((0, 0, 0.38), (0.10, 0.09, 0.13))
    m.set_color("gold")
    m.box((0, 0, 0.30), (0.05, 0.05, 0.03))
    return [(m, "M_Palette_Wood")]


def build_prop_teacup(ctx):
    """茶碗（三之介用）：碗体 + 茶水。"""
    m = Mesh("teacup")
    m.set_color("white_robe")
    m.cylinder((0, 0, 0), 0.045, 0.06, 0.075, segments=8, cap_bottom=True, cap_top=False)
    tea = Mesh("tea")
    tea.set_color("moss")
    tea.disc((0, 0, 0.065), 0.055, segments=8, normal="z")
    m.merge(tea)
    return [(m, "M_Palette_Stone")]


def build_prop_miko_wand(ctx):
    """巫女笏（椿用）：扁平板 + 饰带。"""
    m = Mesh("wand")
    m.set_color("wood")
    m.box((0, 0, 0.22), (0.05, 0.012, 0.44))
    m.set_color("white_robe")
    m.box((0, 0, 0.05), (0.055, 0.02, 0.06))
    m.set_color("torii_red")
    m.cylinder((0, 0, 0.0), 0.014, 0.014, 0.06, segments=6, axis="z")
    return [(m, "M_Palette_Wood")]


def build_weapon_tachi(ctx):
    """太刀：刀身（弧）+ 锷 + 柄 + 头。玩家与绯甲武者共用。"""
    m = Mesh("tachi")
    L = 1.05
    # 刀身：用 ring_tube 沿微弧扫掠，扁平截面靠 scale 近似——改用多段 box 拼弧
    m.set_color("bone")
    segs = 8
    for i in range(segs):
        t0 = i / segs
        t1 = (i + 1) / segs
        z0 = 0.28 + t0 * (L - 0.28)
        z1 = 0.28 + t1 * (L - 0.28)
        # 刀刃微弯：沿 -Y 偏移
        yb = -0.03 * math.sin(math.pi * (t0 + t1) * 0.5)
        seg = Mesh("blade")
        seg.set_color("bone")
        seg.set_tint_fn(tint_height("z", 0.28, L, dark=0.9, bright=1.1))
        seg.box((0, yb, (z0 + z1) * 0.5), (0.035, 0.012, (z1 - z0) * 1.05))
        m.merge(seg)
    m.set_tint_fn(None)
    # 刀尖
    m.set_color("bone")
    m.cone((0, -0.03, L), 0.02, 0.06, segments=4, axis="z")
    # 锷（护手）
    m.set_color("gold")
    m.cylinder((0, 0, 0.26), 0.055, 0.055, 0.015, segments=8, axis="z")
    # 柄
    m.set_color("ink")
    m.cylinder((0, 0, 0.0), 0.022, 0.024, 0.26, segments=6, axis="z")
    # 柄头
    m.set_color("gold")
    m.cylinder((0, 0, 0.0), 0.026, 0.026, 0.02, segments=6, axis="z")
    return [(m, "M_Palette_Metal")]


def build_weapon_oni_blade(ctx):
    """樱鬼的骨刀：粗糙骨质刃 + 骨柄。"""
    rng = ctx["rng"]
    m = Mesh("oniblade")
    L = 0.80
    m.set_color("bone")
    segs = 6
    for i in range(segs):
        t0 = i / segs
        t1 = (i + 1) / segs
        z0 = 0.18 + t0 * (L - 0.18)
        z1 = 0.18 + t1 * (L - 0.18)
        w = 0.05 * (1.0 - 0.5 * (t0 + t1) * 0.5)
        seg = Mesh("b")
        seg.set_color("bone")
        seg.set_tint_fn(tint_height("z", 0.18, L, dark=0.85, bright=1.05))
        seg.box((0, 0, (z0 + z1) * 0.5), (w, 0.02, (z1 - z0) * 1.05))
        seg.jitter(0.008, rng)
        m.merge(seg)
    m.set_tint_fn(None)
    # 骨柄
    m.set_color("horn")
    m.cylinder((0, 0, 0.0), 0.03, 0.025, 0.20, segments=5, axis="z")
    m.icosphere((0, 0, 0.0), 0.035, subdiv=0)
    return [(m, "M_Palette_Opaque")]


# ==========================================================================
# 八、注册表
# ==========================================================================

ASSETS = {
    # --- skinned 角色（走 assemble 路径）---
    "asset_npc_base": {
        "file": "SK_NPC_Base.glb", "skinned": True, "assemble": assemble_npc_base,
        "tri_budget": 1600,
    },
    "asset_enemy_sakura_oni": {
        "file": "SK_Enemy_SakuraOni.glb", "skinned": True, "assemble": assemble_sakura_oni,
        "tri_budget": 1400,
    },
    "asset_enemy_hikabusho": {
        "file": "SK_Enemy_Hikabusho.glb", "skinned": True, "assemble": assemble_hikabusho,
        "tri_budget": 2600,
    },
    # --- 静态配件与武器（走 build 路径）---
    "asset_npc_hair_variants": {
        "file": "SM_NPC_Hair_Variants.glb", "build": build_hair_variants,
        "materials": ["M_Palette_Opaque"], "tri_budget": 600,
    },
    "asset_npc_prop_lantern": {
        "file": "SM_NPC_Prop_Lantern.glb", "build": build_prop_lantern,
        "materials": ["M_Palette_Wood", "M_Lantern_Glow"], "tri_budget": 200,
        "parts": {"body": 0, "glow": 1},
    },
    "asset_npc_prop_hammer": {
        "file": "SM_NPC_Prop_Hammer.glb", "build": build_prop_hammer,
        "materials": ["M_Palette_Wood"], "tri_budget": 140,
    },
    "asset_npc_prop_teacup": {
        "file": "SM_NPC_Prop_Teacup.glb", "build": build_prop_teacup,
        "materials": ["M_Palette_Stone"], "tri_budget": 80,
    },
    "asset_npc_prop_miko_wand": {
        "file": "SM_NPC_Prop_MikoWand.glb", "build": build_prop_miko_wand,
        "materials": ["M_Palette_Wood"], "tri_budget": 100,
    },
    "asset_weapon_tachi": {
        "file": "SM_Weapon_Tachi.glb", "build": build_weapon_tachi,
        "materials": ["M_Palette_Metal"], "tri_budget": 240,
    },
    "asset_weapon_katana_oni": {
        "file": "SM_Weapon_OniBlade.glb", "build": build_weapon_oni_blade,
        "materials": ["M_Palette_Opaque"], "tri_budget": 160,
    },
}
