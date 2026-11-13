"""
theseed_geo.py — TheSeed「樱庭·离宫」程序化资产几何库

纯 Python 标准库实现，不依赖任何第三方包，不需要网络。
提供：向量/矩阵运算、Mesh 容器与基础图元、调色板纹理生成、PNG 编码、
     glTF 2.0 Binary (GLB) 写入器（含骨骼蒙皮与动画）。

规格来源：The-Seed-Link-Future/SAO_GameDesign/SakuraTeien/03_ArtAssetSpec_Procedural.md
坐标系：右手系，+Y 北，+X 东，+Z 上；单位 = 米。
"""

import math
import struct
import zlib

GLB_MAGIC = 0x46546C67
GLB_VERSION = 2
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

CT_BYTE = 5120
CT_UBYTE = 5121
CT_SHORT = 5122
CT_USHORT = 5123
CT_UINT = 5125
CT_FLOAT = 5126

TARGET_ARRAY = 34962
TARGET_ELEMENT = 34963

CT_SIZE = {CT_BYTE: 1, CT_UBYTE: 1, CT_SHORT: 2, CT_USHORT: 2, CT_UINT: 4, CT_FLOAT: 4}
CT_NAME = {CT_BYTE: 5120, CT_UBYTE: 5121, CT_SHORT: 5122, CT_USHORT: 5123,
           CT_UINT: 5125, CT_FLOAT: 5126}

GLOBAL_SEED = 20261113


# --------------------------------------------------------------------------
# 确定性随机
# --------------------------------------------------------------------------

class Rng:
    """固定种子的确定性伪随机数发生器（xorshift64*）。

    不使用 random 模块，避免不同 Python 版本 / 哈希种子导致产物字节漂移。
    """

    def __init__(self, seed):
        self.s = (seed * 2654435761 + 12345) & 0xFFFFFFFFFFFFFFFF
        if self.s == 0:
            self.s = 0x9E3779B97F4A7C15

    def _next(self):
        s = self.s
        s ^= (s >> 12) & 0xFFFFFFFFFFFFFFFF
        s ^= (s << 25) & 0xFFFFFFFFFFFFFFFF
        s ^= (s >> 27) & 0xFFFFFFFFFFFFFFFF
        self.s = s
        return (s * 0x2545F4914F6CDD1D) & 0xFFFFFFFFFFFFFFFF

    def unit(self):
        return self._next() / 18446744073709551616.0

    def range(self, lo, hi):
        return lo + (hi - lo) * self.unit()

    def sign(self):
        return 1.0 if self.unit() < 0.5 else -1.0

    def pick(self, seq):
        return seq[int(self.unit() * len(seq)) % len(seq)]


def derive_seed(asset_id, salt=0):
    """由资产 ID 派生子种子，保证同 ID 恒定、异 ID 分散。"""
    h = 2166136261
    for ch in asset_id.encode("utf-8"):
        h ^= ch
        h = (h * 16777619) & 0xFFFFFFFF
    return (GLOBAL_SEED + h + salt * 7919) & 0xFFFFFFFF


# --------------------------------------------------------------------------
# 矩阵（4x4，列主序，与 glTF 一致）
# --------------------------------------------------------------------------

def m4_identity():
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def m4_mul(a, b):
    out = [0.0] * 16
    for c in range(4):
        for r in range(4):
            acc = 0.0
            for k in range(4):
                acc += a[k * 4 + r] * b[c * 4 + k]
            out[c * 4 + r] = acc
    return out


def m4_translate(x, y, z):
    m = m4_identity()
    m[12], m[13], m[14] = float(x), float(y), float(z)
    return m


def m4_scale(sx, sy=None, sz=None):
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    m = m4_identity()
    m[0], m[5], m[10] = float(sx), float(sy), float(sz)
    return m


def m4_rot_x(a_deg):
    a = math.radians(a_deg)
    c, s = math.cos(a), math.sin(a)
    return [1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]


def m4_rot_y(a_deg):
    a = math.radians(a_deg)
    c, s = math.cos(a), math.sin(a)
    return [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]


def m4_rot_z(a_deg):
    a = math.radians(a_deg)
    c, s = math.cos(a), math.sin(a)
    return [c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def m4_compose(translation=None, rot_zyx_deg=(0, 0, 0), scale=(1, 1, 1)):
    m = m4_identity()
    rz, ry, rx = rot_zyx_deg
    if rz:
        m = m4_mul(m, m4_rot_z(rz))
    if ry:
        m = m4_mul(m, m4_rot_y(ry))
    if rx:
        m = m4_mul(m, m4_rot_x(rx))
    m = m4_mul(m4_translate(*(translation or (0, 0, 0))), m)
    m = m4_mul(m, m4_scale(*scale))
    return m


def m4_apply_point(m, p):
    x, y, z = p
    return (m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14])


def m4_apply_dir(m, v):
    x, y, z = v
    return (m[0] * x + m[4] * y + m[8] * z,
            m[1] * x + m[5] * y + m[9] * z,
            m[2] * x + m[6] * y + m[10] * z)


def m4_invert(m):
    """通用 4x4 求逆（伴随矩阵法）。用于计算蒙皮的 inverseBindMatrix。"""
    inv = [0.0] * 16
    inv[0] = (m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15]
              + m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10])
    inv[4] = (-m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15]
              - m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10])
    inv[8] = (m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15]
              + m[8] * m[7] * m[13] + m[12] * m[5] * m[11] - m[12] * m[7] * m[9])
    inv[12] = (-m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14]
               - m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9])
    inv[1] = (-m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15]
              - m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10])
    inv[5] = (m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15]
              + m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10])
    inv[9] = (-m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15]
              - m[8] * m[3] * m[13] - m[12] * m[1] * m[11] + m[12] * m[3] * m[9])
    inv[13] = (m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14]
               + m[8] * m[2] * m[13] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9])
    inv[2] = (m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15]
              + m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6])
    inv[6] = (-m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15]
              - m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6])
    inv[10] = (m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15]
               + m[4] * m[3] * m[13] + m[12] * m[1] * m[7] - m[12] * m[3] * m[5])
    inv[14] = (-m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14]
               - m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5])
    inv[3] = (-m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11]
              - m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6])
    inv[7] = (m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11]
              + m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6])
    inv[11] = (-m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11]
               - m[4] * m[3] * m[9] - m[8] * m[1] * m[7] + m[8] * m[3] * m[5])
    inv[15] = (m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10]
               + m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5])
    det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]
    if abs(det) < 1e-12:
        return m4_identity()
    det = 1.0 / det
    return [v * det for v in inv]


def v3_normalize(v):
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (x / n, y / n, z / n)


def v3_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def v3_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v3_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v3_lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def quat_from_axis_angle(axis, angle_deg):
    ax = v3_normalize(axis)
    h = math.radians(angle_deg) * 0.5
    s = math.sin(h)
    return [ax[0] * s, ax[1] * s, ax[2] * s, math.cos(h)]


def quat_mul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]


def quat_slerp(a, b, t):
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b = [-x for x in b]
        dot = -dot
    if dot > 0.9995:
        r = [a[i] + (b[i] - a[i]) * t for i in range(4)]
        n = math.sqrt(sum(x * x for x in r)) or 1.0
        return [x / n for x in r]
    th0 = math.acos(max(-1.0, min(1.0, dot)))
    s = math.sin(th0)
    if abs(s) < 1e-9:
        return list(a)
    w1 = math.sin((1 - t) * th0) / s
    w2 = math.sin(t * th0) / s
    return [a[i] * w1 + b[i] * w2 for i in range(4)]


# --------------------------------------------------------------------------
# 调色板（03_ArtAssetSpec_Procedural.md §3.1）
# --------------------------------------------------------------------------

PALETTE_ROWS = [
    [("sakura", 0xF2C6D0), ("sakura_deep", 0xD98FA3), ("sakura_white", 0xFAE8EC),
     ("bark", 0x6E5346), ("bark_dark", 0x4A372E), ("wood", 0x8B5A3C),
     ("wood_dark", 0x5E3A26), ("bamboo", 0x7E9A5B)],
    [("torii_red", 0xB33A2B), ("torii_peel", 0x6E6259), ("tile", 0x4A4E57),
     ("tile_dark", 0x33363D), ("stone", 0x9A968E), ("stone_dark", 0x6F6C66),
     ("sand", 0xE8E4DC), ("moss", 0x6B8055)],
    [("grass", 0x7C9A5E), ("grass_dark", 0x5C7744), ("water", 0x4E7A82),
     ("water_dark", 0x33555C), ("cloth", 0xC8B79A), ("paper_lamp", 0xF5D9A8),
     ("cold", 0x5C6B7A), ("cold_dark", 0x3E4A56)],
    [("armor_red", 0xA33B32), ("armor_dark", 0x6E2620), ("gold", 0xC9A24A),
     ("oni_skin", 0x8E6B7A), ("oni_skin_dark", 0x5E4450), ("horn", 0xD8CFC0),
     ("bone", 0xE3DED4), ("ink", 0x2A2A2E)],
    [("skin", 0xE8C4A8), ("hair_black", 0x2E2A33), ("hair_red", 0x8B3A3A),
     ("white_robe", 0xEDEAE3), ("red_hakama", 0xA8434F), ("blue_kimono", 0x4A6B82),
     ("brown_kimono", 0x8A7358), ("grey_kimono", 0x6E6E72)],
]

PALETTE_CELLS = 8
PALETTE_SIZE = 256
PALETTE_CELL = PALETTE_SIZE // PALETTE_CELLS


def palette_cell(name):
    """返回调色板名对应的 (col, row)；未定义名回落到 white。"""
    for r, row in enumerate(PALETTE_ROWS):
        for c, (n, _hexv) in enumerate(row):
            if n == name:
                return (c, r)
    return (7, 7)


def palette_hex(name):
    for row in PALETTE_ROWS:
        for n, h in row:
            if n == name:
                return h
    return 0xFFFFFF


def palette_uv_center(name):
    c, r = palette_cell(name)
    u = (c * PALETTE_CELL + PALETTE_CELL * 0.5) / PALETTE_SIZE
    v = 1.0 - (r * PALETTE_CELL + PALETTE_CELL * 0.5) / PALETTE_SIZE
    return (u, v)


def build_palette_png():
    """生成 256x256 调色板纹理 PNG（RGBA）。纯色块，压缩后体积极小。"""
    grid = [[0xFFFFFF] * PALETTE_CELLS for _ in range(PALETTE_CELLS)]
    for r, row in enumerate(PALETTE_ROWS):
        for c, (_n, hexv) in enumerate(row):
            grid[r][c] = hexv
    raw = bytearray()
    for py in range(PALETTE_SIZE):
        raw.append(0)
        row = grid[py // PALETTE_CELL]
        for px in range(PALETTE_SIZE):
            v = row[px // PALETTE_CELL]
            raw.append((v >> 16) & 0xFF)
            raw.append((v >> 8) & 0xFF)
            raw.append(v & 0xFF)
            raw.append(255)
    return encode_png(PALETTE_SIZE, PALETTE_SIZE, bytes(raw), PALETTE_SIZE * 4)


def build_petal_alpha_png(size=64):
    """花瓣贴图：RGBA，alpha 勾勒花瓣轮廓，颜色为樱粉渐变。"""
    rng = Rng(derive_seed("petal_alpha"))
    raw = bytearray()
    cx, cy = size * 0.5, size * 0.54
    for py in range(size):
        raw.append(0)
        for px in range(size):
            dx = (px - cx) / (size * 0.42)
            dy = (py - cy) / (size * 0.50)
            notch = 0.16 * math.exp(-abs(dx) * 3.0) * (1.0 if dy < -0.35 else 0.0)
            r = math.sqrt(dx * dx + (dy + notch) * (dy + notch))
            edge = 1.0 - r
            a = 0.0 if r > 1.0 else min(1.0, edge * 5.0)
            jit = rng.range(0.94, 1.06)
            base = 0xF2C6D0 if dy < 0 else 0xD98FA3
            t = max(0.0, min(1.0, (dy + 1.0) * 0.5))
            rr = int(((0xF2 + (0xD9 - 0xF2) * t) * jit))
            gg = int(((0xC6 + (0x8F - 0xC6) * t) * jit))
            bb = int(((0xD0 + (0xA3 - 0xD0) * t) * jit))
            raw.append(max(0, min(255, rr)))
            raw.append(max(0, min(255, gg)))
            raw.append(max(0, min(255, bb)))
            raw.append(int(a * 255))
    _ = base
    return encode_png(size, size, bytes(raw), size * 4)


# --------------------------------------------------------------------------
# PNG 编码（zlib 手写，不依赖 Pillow）
# --------------------------------------------------------------------------

def _png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def encode_png(width, height, raw_rows, stride):
    """raw_rows: 已含每行 filter 字节(0x00) 的原始 RGBA 数据。stride = width*4。"""
    idat = zlib.compress(raw_rows, 9)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    _ = stride
    return sig + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", idat) + _png_chunk(b"IEND", b"")


# --------------------------------------------------------------------------
# Mesh
# --------------------------------------------------------------------------

class Mesh:
    """顶点容器 + 基础图元生成器。

    当前颜色/色调/骨骼权重是「状态」，由 set_color / set_tint / set_skin_weight
    切换，后续添加的顶点继承该状态。每个三角面三个顶点共享同一 UV，
    因此调色板采样恒为纯色块，不会出现跨格插值。
    """

    def __init__(self, name, color="stone"):
        self.name = name
        self.pos = []
        self.nrm = []
        self.col = []
        self.uv = []
        self.idx = []
        self.jnt = []
        self.wgt = []
        self.skinned = False
        self._color = color
        self._tint = (1.0, 1.0, 1.0)
        self._tint_fn = None
        self._joints = (0, 0, 0, 0)
        self._weights = (1.0, 0.0, 0.0, 0.0)

    # -- 状态 -------------------------------------------------------------
    def set_color(self, name):
        self._color = name
        return self

    def set_tint(self, rgb_or_scalar):
        if isinstance(rgb_or_scalar, (int, float)):
            v = float(rgb_or_scalar)
            self._tint = (v, v, v)
        else:
            self._tint = tuple(float(x) for x in rgb_or_scalar)
        return self

    def set_tint_fn(self, fn):
        """fn(local_pos) -> scalar 或 (r,g,b)，用于高度渐变 / AO。传 None 关闭。"""
        self._tint_fn = fn
        return self

    def set_skin_weight(self, joints, weights):
        self._joints = tuple(int(j) for j in joints[:4]) + (0,) * max(0, 4 - len(joints))
        w = list(weights[:4])
        w += [0.0] * max(0, 4 - len(w))
        tot = sum(w) or 1.0
        self._weights = tuple(x / tot for x in w)
        self.skinned = True
        return self

    # -- 底层 -------------------------------------------------------------
    def _emit(self, p, n):
        self.pos.append((float(p[0]), float(p[1]), float(p[2])))
        nn = v3_normalize(n)
        self.nrm.append((float(nn[0]), float(nn[1]), float(nn[2])))
        if self._tint_fn is not None:
            t = self._tint_fn(p)
            self._tint = (t, t, t) if isinstance(t, (int, float)) else tuple(t)
        self.col.append((float(self._tint[0]), float(self._tint[1]), float(self._tint[2])))
        self.uv.append(palette_uv_center(self._color))
        if self.skinned:
            self.jnt.append(self._joints)
            self.wgt.append(self._weights)
        return len(self.pos) - 1

    def add_tri(self, a, b, c):
        base = len(self.pos)
        p0, p1, p2 = self.pos[base + a], self.pos[base + b], self.pos[base + c]
        n = v3_cross(v3_sub(p1, p0), v3_sub(p2, p0))
        if n[0] == n[1] == n[2] == 0:
            return None
        n = v3_normalize(n)
        ia, ib, ic = self._emit(p0, n), self._emit(p1, n), self._emit(p2, n)
        self.idx.append((ia, ib, ic))
        return (ia, ib, ic)

    def add_quad(self, a, b, c, d):
        self.add_tri(a, b, c)
        self.add_tri(a, c, d)

    @property
    def tri_count(self):
        return len(self.idx)

    def is_empty(self):
        return len(self.idx) == 0

    # -- 变换与合并 --------------------------------------------------------
    def transform(self, m):
        if m == m4_identity():
            return self
        newpos = [m4_apply_point(m, p) for p in self.pos]
        newnrm = [v3_normalize(m4_apply_dir(m, n)) for n in self.nrm]
        self.pos = newpos
        self.nrm = newnrm
        return self

    def translate(self, x, y, z):
        return self.transform(m4_translate(x, y, z))

    def rotate(self, rz=0.0, ry=0.0, rx=0.0):
        m = m4_identity()
        if rz:
            m = m4_mul(m, m4_rot_z(rz))
        if ry:
            m = m4_mul(m, m4_rot_y(ry))
        if rx:
            m = m4_mul(m, m4_rot_x(rx))
        return self.transform(m)

    def mirror(self, axis="x"):
        i = {"x": 0, "y": 1, "z": 2}[axis]
        newpos = []
        for p in self.pos:
            q = list(p)
            q[i] = -q[i]
            newpos.append(tuple(q))
        self.pos = newpos
        newnrm = []
        for n in self.nrm:
            q = list(n)
            q[i] = -q[i]
            newnrm.append(tuple(q))
        self.nrm = newnrm
        self.idx = [(a, c, b) for (a, b, c) in self.idx]
        return self

    def merge(self, other):
        """把 other 并入自身。骨骼属性不一致时自动升级为蒙皮网格。"""
        if other.is_empty():
            return self
        # other 带蒙皮而 self 不带：升级 self。对空 self 也安全（填充长度为 0 的
        # joints/weights，随后由 extend 继承 other 的真实蒙皮数据）。
        if other.skinned and not self.skinned:
            self._promote_to_skinned()
        if self.skinned and not other.skinned:
            other = other.clone()._promote_to_skinned()
        off = len(self.pos)
        self.pos.extend(other.pos)
        self.nrm.extend(other.nrm)
        self.col.extend(other.col)
        self.uv.extend(other.uv)
        if self.skinned:
            self.jnt.extend(other.jnt)
            self.wgt.extend(other.wgt)
        for tri in other.idx:
            self.idx.append((tri[0] + off, tri[1] + off, tri[2] + off))
        return self

    def _promote_to_skinned(self):
        n = len(self.pos)
        self.jnt = [(0, 0, 0, 0)] * n
        self.wgt = [(1.0, 0.0, 0.0, 0.0)] * n
        self.skinned = True
        return self

    def clone(self):
        m = Mesh(self.name + "_copy", self._color)
        m.pos = list(self.pos)
        m.nrm = list(self.nrm)
        m.col = list(self.col)
        m.uv = list(self.uv)
        m.idx = list(self.idx)
        m.jnt = list(self.jnt)
        m.wgt = list(self.wgt)
        m.skinned = self.skinned
        return m

    def jitter(self, amount, rng):
        """按顶点抖动位置，用于岩石/树冠的有机感。保持法线在之后重算。"""
        if amount <= 0:
            return self
        seen = {}
        for i, p in enumerate(self.pos):
            key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
            if key not in seen:
                seen[key] = (rng.range(-amount, amount),
                             rng.range(-amount, amount),
                             rng.range(-amount, amount))
            d = seen[key]
            self.pos[i] = (p[0] + d[0], p[1] + d[1], p[2] + d[2])
        self._recompute_flat_normals()
        return self

    def _recompute_flat_normals(self):
        for tri in self.idx:
            a, b, c = tri
            p0, p1, p2 = self.pos[a], self.pos[b], self.pos[c]
            n = v3_normalize(v3_cross(v3_sub(p1, p0), v3_sub(p2, p0)))
            self.nrm[a] = self.nrm[b] = self.nrm[c] = n

    # -- 图元 -------------------------------------------------------------
    def box(self, center, size, color=None, tint_fn=None):
        """轴对齐盒体。center=(cx,cy,cz) size=(sx,sy,sz)。24 顶点 12 面。"""
        cx, cy, cz = center
        hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
        if color:
            self.set_color(color)
        if tint_fn is not None:
            self.set_tint_fn(tint_fn)
        v = [
            (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
            (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
            (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
        ]
        faces = [
            (4, 5, 6, 7, (0, 0, 1)),    # +Z 北
            (1, 0, 3, 2, (0, 0, -1)),   # -Z 南
            (5, 1, 2, 6, (1, 0, 0)),    # +X 东
            (0, 4, 7, 3, (-1, 0, 0)),   # -X 西
            (7, 6, 2, 3, (0, 1, 0)),    # +Y 上
            (0, 1, 5, 4, (0, -1, 0)),   # -Y 下
        ]
        for a, b, c, d, _n in faces:
            base = len(self.pos)
            for k in (a, b, c, d):
                self._emit(v[k], _n)
            self.idx.append((base, base + 1, base + 2))
            self.idx.append((base, base + 2, base + 3))
        self.set_tint_fn(None)
        return self

    def cylinder(self, base_center, r_bottom, r_top, height, segments=8,
                 cap_bottom=True, cap_top=True, color=None, tint_fn=None,
                 axis="z", bend=0.0):
        """圆柱/圆台。axis='z' 沿 +Z 生长；'y' 沿 +Y。bend 为顶部侧向偏移(米)。"""
        if color:
            self.set_color(color)
        if tint_fn is not None:
            self.set_tint_fn(tint_fn)
        bx, by, bz = base_center
        seg = max(3, int(segments))
        dx, dy = 0.0, 0.0
        if axis == "y":
            dy = bend
            top = (bx + dx, by + height, bz)
        else:
            dx = bend
            top = (bx + dx, by, bz + height)
        ring_b, ring_t = [], []
        for i in range(seg):
            a = 2.0 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            if axis == "y":
                ring_b.append((bx + ca * r_bottom, by, bz + sa * r_bottom))
                ring_t.append((top[0] + ca * r_top, top[1], top[2] + sa * r_top))
            else:
                ring_b.append((bx + ca * r_bottom, by + sa * r_bottom, bz))
                ring_t.append((top[0] + ca * r_top, top[1] + sa * r_top, top[2]))
        n_side = seg * 2
        for i in range(seg):
            j = (i + 1) % seg
            p0, p1, p2, p3 = ring_b[i], ring_b[j], ring_t[j], ring_t[i]
            nn = v3_normalize(v3_cross(v3_sub(p1, p0), v3_sub(p3, p0)))
            base = len(self.pos)
            for p in (p0, p1, p2, p3):
                self._emit(p, nn)
            self.idx.append((base, base + 1, base + 2))
            self.idx.append((base, base + 2, base + 3))
        _ = n_side
        if cap_top and r_top > 1e-6:
            ctr = top
            nrm = (0, 1, 0) if axis == "y" else (0, 0, 1)
            cidx = self._emit(ctr, nrm)
            for i in range(seg):
                j = (i + 1) % seg
                a1 = self._emit(ring_t[i], nrm)
                a2 = self._emit(ring_t[j], nrm)
                if axis == "y":
                    self.idx.append((cidx, a2, a1))
                else:
                    self.idx.append((cidx, a1, a2))
        if cap_bottom and r_bottom > 1e-6:
            ctr = (bx, by, bz)
            nrm = (0, -1, 0) if axis == "y" else (0, 0, -1)
            cidx = self._emit(ctr, nrm)
            for i in range(seg):
                j = (i + 1) % seg
                a1 = self._emit(ring_b[i], nrm)
                a2 = self._emit(ring_b[j], nrm)
                if axis == "y":
                    self.idx.append((cidx, a1, a2))
                else:
                    self.idx.append((cidx, a2, a1))
        self.set_tint_fn(None)
        return self

    def cone(self, base_center, radius, height, segments=8, color=None, tint_fn=None, axis="z"):
        return self.cylinder(base_center, radius, 0.0, height, segments,
                             cap_bottom=True, cap_top=False, color=color,
                             tint_fn=tint_fn, axis=axis)

    def sphere_uv(self, center, radius, rings=6, segments=8, color=None,
                  tint_fn=None, squash=1.0):
        cx, cy, cz = center
        if color:
            self.set_color(color)
        if tint_fn is not None:
            self.set_tint_fn(tint_fn)
        rings = max(2, int(rings))
        seg = max(3, int(segments))
        grid = []
        for ri in range(rings + 1):
            phi = math.pi * ri / rings
            ring = []
            for si in range(seg):
                th = 2.0 * math.pi * si / seg
                x = math.sin(phi) * math.cos(th)
                y = math.sin(phi) * math.sin(th)
                z = math.cos(phi) * squash
                p = (cx + x * radius, cy + y * radius, cz + z * radius)
                n = v3_normalize((x, y, z))
                ring.append(self._emit(p, n))
            grid.append(ring)
        for ri in range(rings):
            for si in range(seg):
                sj = (si + 1) % seg
                a, b = grid[ri][si], grid[ri][sj]
                c, d = grid[ri + 1][sj], grid[ri + 1][si]
                if ri != 0:
                    self.idx.append((a, b, c))
                if ri != rings - 1:
                    self.idx.append((a, c, d))
        self.set_tint_fn(None)
        return self

    _ICO_V = None
    _ICO_F = None

    def _ico_base(self):
        if Mesh._ICO_V is not None:
            return Mesh._ICO_V, Mesh._ICO_F
        t = (1.0 + math.sqrt(5.0)) * 0.5
        verts = [v3_normalize(v) for v in [
            (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
            (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
            (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1),
        ]]
        faces = [
            (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
            (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
            (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
            (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
        ]
        Mesh._ICO_V, Mesh._ICO_F = verts, faces
        return verts, faces

    def icosphere(self, center, radius, subdiv=1, color=None, tint_fn=None, squash=1.0):
        """二十面体细分球。subdiv=0 -> 20 面；1 -> 80 面；2 -> 320 面。"""
        cx, cy, cz = center
        if color:
            self.set_color(color)
        if tint_fn is not None:
            self.set_tint_fn(tint_fn)
        verts, faces = self._ico_base()
        verts = list(verts)
        cache = {}
        for _ in range(max(0, int(subdiv))):
            new_faces = []
            for a, b, c in faces:
                ab = self._ico_mid(a, b, verts, cache)
                bc = self._ico_mid(b, c, verts, cache)
                ca = self._ico_mid(c, a, verts, cache)
                new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
            faces = new_faces
            cache = {}
        for v in verts:
            x, y, z = v
            self._emit((cx + x * radius, cy + y * radius, cz + z * radius * squash),
                       v3_normalize((x, y, z * (1.0 / squash if squash else 1.0))))
        for a, b, c in faces:
            self.idx.append((a, b, c))
        self.set_tint_fn(None)
        return self

    @staticmethod
    def _ico_mid(a, b, verts, cache):
        key = (min(a, b), max(a, b))
        if key in cache:
            return cache[key]
        m = v3_normalize(v3_lerp(verts[a], verts[b], 0.5))
        verts.append(m)
        cache[key] = len(verts) - 1
        return cache[key]

    def plane(self, center, size_x, size_y, seg_x=1, seg_y=1, color=None,
              tint_fn=None, normal="z", displace_fn=None):
        """平面网格。normal='z' 为水平地面(XY)，'y' 为竖直面(XZ)。"""
        cx, cy, cz = center
        if color:
            self.set_color(color)
        if tint_fn is not None:
            self.set_tint_fn(tint_fn)
        sx = max(1, int(seg_x))
        sy = max(1, int(seg_y))
        grid = []
        for j in range(sy + 1):
            row = []
            for i in range(sx + 1):
                u = i / sx - 0.5
                v = j / sy - 0.5
                if normal == "z":
                    p = [cx + u * size_x, cy + v * size_y, cz]
                else:
                    p = [cx + u * size_x, cy, cz + v * size_y]
                if displace_fn is not None:
                    p = list(displace_fn(p[0], p[1], p[2]))
                row.append(p)
            grid.append(row)
        nrm = (0, 0, 1) if normal == "z" else (0, -1, 0)
        ids = [[self._emit(p, nrm) for p in row] for row in grid]
        if displace_fn is not None:
            for j in range(sy):
                for i in range(sx):
                    p0 = grid[j][i]
                    p1 = grid[j][i + 1]
                    p2 = grid[j + 1][i + 1]
                    p3 = grid[j + 1][i]
                    n1 = v3_normalize(v3_cross(v3_sub(p1, p0), v3_sub(p2, p0)))
                    n2 = v3_normalize(v3_cross(v3_sub(p2, p0), v3_sub(p3, p0)))
                    for k, (ii, jj, nn) in enumerate([
                        (i, j, n1), (i + 1, j, n1), (i + 1, j + 1, n1),
                        (i, j, n2), (i + 1, j + 1, n2), (i, j + 1, n2)]):
                        _ = k
                        self.nrm[ids[jj][ii]] = nn
        for j in range(sy):
            for i in range(sx):
                a, b = ids[j][i], ids[j][i + 1]
                c, d = ids[j + 1][i + 1], ids[j + 1][i]
                if normal == "z":
                    self.idx.append((a, b, c))
                    self.idx.append((a, c, d))
                else:
                    self.idx.append((a, c, b))
                    self.idx.append((a, d, c))
        self.set_tint_fn(None)
        return self

    def quad(self, p0, p1, p2, p3, color=None, double=True):
        """任意四边形面片（用于草丛、雾片、花瓣）。double=True 生成双面。"""
        if color:
            self.set_color(color)
        n = v3_normalize(v3_cross(v3_sub(p1, p0), v3_sub(p3, p0)))
        base = len(self.pos)
        for p in (p0, p1, p2, p3):
            self._emit(p, n)
        self.idx.append((base, base + 1, base + 2))
        self.idx.append((base, base + 2, base + 3))
        if double:
            base2 = len(self.pos)
            for p in (p0, p1, p2, p3):
                self._emit(p, (-n[0], -n[1], -n[2]))
            self.idx.append((base2, base2 + 2, base2 + 1))
            self.idx.append((base2, base2 + 3, base2 + 2))
        return self

    def disc(self, center, radius, segments=12, color=None, tint_fn=None, normal="z"):
        cx, cy, cz = center
        if color:
            self.set_color(color)
        if tint_fn is not None:
            self.set_tint_fn(tint_fn)
        seg = max(3, int(segments))
        nrm = (0, 0, 1) if normal == "z" else (0, 1, 0)
        cidx = self._emit((cx, cy, cz), nrm)
        ring = []
        for i in range(seg):
            a = 2.0 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            if normal == "z":
                p = (cx + ca * radius, cy + sa * radius, cz)
            else:
                p = (cx + ca * radius, cy, cz + sa * radius)
            ring.append(self._emit(p, nrm))
        for i in range(seg):
            j = (i + 1) % seg
            if normal == "z":
                self.idx.append((cidx, ring[i], ring[j]))
            else:
                self.idx.append((cidx, ring[j], ring[i]))
        self.set_tint_fn(None)
        return self

    def torus(self, center, r_major, r_minor, seg_major=12, seg_minor=6,
              color=None, axis="z"):
        cx, cy, cz = center
        if color:
            self.set_color(color)
        sm = max(3, int(seg_major))
        sn = max(3, int(seg_minor))
        grid = []
        for i in range(sm):
            u = 2.0 * math.pi * i / sm
            cu, su = math.cos(u), math.sin(u)
            ring = []
            for j in range(sn):
                v = 2.0 * math.pi * j / sn
                cv, sv = math.cos(v), math.sin(v)
                rr = r_major + r_minor * cv
                if axis == "z":
                    p = (cx + rr * cu, cy + rr * su, cz + r_minor * sv)
                    n = (cv * cu, cv * su, sv)
                else:
                    p = (cx + rr * cu, cy + r_minor * sv, cz + rr * su)
                    n = (cv * cu, sv, cv * su)
                ring.append(self._emit(p, n))
            grid.append(ring)
        for i in range(sm):
            i2 = (i + 1) % sm
            for j in range(sn):
                j2 = (j + 1) % sn
                a, b = grid[i][j], grid[i][j2]
                c, d = grid[i2][j2], grid[i2][j]
                self.idx.append((a, b, c))
                self.idx.append((a, c, d))
        return self

    def ring_tube(self, points, radii, sides=6, color=None, closed=False):
        """沿折线扫掠圆管，用于树枝、竹竿、栏干。points=[(x,y,z),...] radii=[r,...]"""
        if color:
            self.set_color(color)
        n = len(points)
        if n < 2:
            return self
        sides = max(3, int(sides))
        rings = []
        for k in range(n):
            p = points[k]
            if k == 0:
                fwd = v3_sub(points[1], points[0])
            elif k == n - 1:
                fwd = v3_sub(points[-1], points[-2])
            else:
                fwd = v3_sub(points[k + 1], points[k - 1])
            fwd = v3_normalize(fwd)
            up = (0, 0, 1) if abs(fwd[2]) < 0.9 else (1, 0, 0)
            right = v3_normalize(v3_cross(fwd, up))
            up2 = v3_cross(right, fwd)
            r = radii[k] if k < len(radii) else radii[-1]
            ring = []
            for i in range(sides):
                a = 2.0 * math.pi * i / sides
                ca, sa = math.cos(a), r and math.sin(a)
                nrm = v3_normalize((right[0] * ca + up2[0] * sa,
                                    right[1] * ca + up2[1] * sa,
                                    right[2] * ca + up2[2] * sa))
                pos = (p[0] + nrm[0] * r, p[1] + nrm[1] * r, p[2] + nrm[2] * r)
                ring.append(self._emit(pos, nrm))
            rings.append(ring)
        cnt = n if closed else n - 1
        for k in range(cnt):
            k2 = (k + 1) % n
            for i in range(sides):
                i2 = (i + 1) % sides
                a, b = rings[k][i], rings[k][i2]
                c, d = rings[k2][i2], rings[k2][i]
                self.idx.append((a, b, c))
                self.idx.append((a, c, d))
        return self

    def finalize(self):
        """展平索引为三角形列表，返回统计信息。"""
        flat = []
        for a, b, c in self.idx:
            flat.extend((a, b, c))
        self.flat_indices = flat
        return {"vertices": len(self.pos), "triangles": len(self.idx)}

    def bounds(self):
        if not self.pos:
            return ((0, 0, 0), (0, 0, 0))
        xs = [p[0] for p in self.pos]
        ys = [p[1] for p in self.pos]
        zs = [p[2] for p in self.pos]
        return ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


# --------------------------------------------------------------------------
# 渐变/着色辅助
# --------------------------------------------------------------------------

def tint_height(axis, lo, hi, dark=0.62, bright=1.0):
    """返回 tint_fn：按指定轴在 [lo,hi] 区间内做明暗渐变（根部暗、顶部亮）。"""
    ai = {"x": 0, "y": 1, "z": 2}[axis]
    span = (hi - lo) or 1.0

    def fn(p):
        t = max(0.0, min(1.0, (p[ai] - lo) / span))
        return dark + (bright - dark) * t
    return fn


def tint_ao_bottom(axis, ground_z, radius, dark=0.55):
    """返回 tint_fn：贴近地面的顶点压暗，模拟接触阴影（AO）。"""
    ai = {"x": 0, "y": 1, "z": 2}[axis]

    def fn(p):
        d = abs(p[ai] - ground_z)
        if d >= radius:
            return 1.0
        t = d / radius
        return dark + (1.0 - dark) * (t * t)
    return fn


# --------------------------------------------------------------------------
# glTF 2.0 文档 / GLB 写入器
# --------------------------------------------------------------------------

def _f32(v):
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


def _round3(v):
    return round(float(v) + 0.0, 6)


class GltfDoc:
    """最小可用的 glTF 2.0 文档构建器。

    支持：多网格多材质、内嵌 PNG 图像与纹理、节点层级、
         骨骼蒙皮（skin + inverseBindMatrices）、动画（TRS 采样）。
    产物为单文件 GLB，几何与图像全部内嵌于 BIN chunk。
    """

    def __init__(self):
        self._bin = bytearray()
        self._bufferviews = []
        self._accessors = []
        self.meshes = []
        self.materials = []
        self._mat_cache = {}
        self.images = []
        self.textures = []
        self._tex_cache = {}
        self.nodes = []
        self.skins = []
        self.animations = []
        self.samplers = []
        self.scene_nodes = []

    # -- 缓冲 -------------------------------------------------------------
    def _push_bytes(self, data, target=None, align=4):
        pad = (-len(self._bin)) % align
        if pad:
            self._bin.extend(b"\x00" * pad)
        off = len(self._bin)
        self._bin.extend(data)
        self._bufferviews.append({
            "buffer": 0, "byteOffset": off, "byteLength": len(data),
            **({"target": target} if target else {}),
        })
        return len(self._bufferviews) - 1

    def _add_accessor(self, bv, ctype, count, vtype, minv=None, maxv=None, byte_off=0):
        n_comp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[vtype]
        acc = {"bufferView": bv, "byteOffset": byte_off, "componentType": ctype,
               "count": count, "type": vtype}
        if minv is not None:
            acc["min"] = [_round3(x) for x in minv]
        if maxv is not None:
            acc["max"] = [_round3(x) for x in maxv]
        _ = n_comp
        self._accessors.append(acc)
        return len(self._accessors) - 1

    # -- 图像 / 纹理 / 材质 ------------------------------------------------
    def add_image(self, png_bytes, name, mime="image/png"):
        bv = self._push_bytes(png_bytes, align=4)
        self.images.append({"bufferView": bv, "mimeType": mime, "name": name})
        return len(self.images) - 1

    def add_texture(self, image_idx, name):
        key = (image_idx,)
        if key in self._tex_cache:
            return self._tex_cache[key]
        self.samplers.append({"magFilter": 9728, "minFilter": 9984,
                              "wrapS": 10497, "wrapT": 10497})
        self.textures.append({"sampler": len(self.samplers) - 1,
                              "source": image_idx, "name": name})
        idx = len(self.textures) - 1
        self._tex_cache[key] = idx
        return idx

    def add_material(self, name, base_tex=None, base_factor=None, metallic=0.0,
                     roughness=0.85, emissive=(0.0, 0.0, 0.0), alpha_mode="OPAQUE",
                     double_sided=False, emissive_strength=1.0):
        key = (base_tex, tuple(base_factor or (1, 1, 1, 1)), metallic, roughness,
               tuple(emissive), alpha_mode, double_sided, emissive_strength)
        if key in self._mat_cache:
            return self._mat_cache[key]
        pbr = {"metallicFactor": _round3(metallic), "roughnessFactor": _round3(roughness)}
        if base_tex is not None:
            pbr["baseColorTexture"] = {"index": base_tex, "texCoord": 0}
        if base_factor:
            pbr["baseColorFactor"] = [_round3(x) for x in base_factor]
        mat = {"name": name, "pbrMetallicRoughness": pbr,
               "alphaMode": alpha_mode, "doubleSided": bool(double_sided)}
        if any(emissive):
            mat["emissiveFactor"] = [_round3(x * emissive_strength) for x in emissive]
        self.materials.append(mat)
        idx = len(self.materials) - 1
        self._mat_cache[key] = idx
        return idx

    # -- 网格 -------------------------------------------------------------
    def add_mesh(self, name, parts):
        """parts = [(Mesh, material_index), ...]"""
        prims = []
        for mesh, mat_idx in parts:
            if mesh.is_empty():
                continue
            mesh.finalize()
            attrs = {}
            pos_bytes = bytearray()
            mins = [1e30] * 3
            maxs = [-1e30] * 3
            for p in mesh.pos:
                pos_bytes.extend(struct.pack("<fff", _f32(p[0]), _f32(p[1]), _f32(p[2])))
                for i in range(3):
                    mins[i] = min(mins[i], p[i])
                    maxs[i] = max(maxs[i], p[i])
            bv = self._push_bytes(bytes(pos_bytes), TARGET_ARRAY)
            attrs["POSITION"] = self._add_accessor(bv, CT_FLOAT, len(mesh.pos), "VEC3",
                                                   [_round3(x) for x in mins],
                                                   [_round3(x) for x in maxs])
            nrm_bytes = bytearray()
            for n in mesh.nrm:
                nrm_bytes.extend(struct.pack("<fff", _f32(n[0]), _f32(n[1]), _f32(n[2])))
            bv = self._push_bytes(bytes(nrm_bytes), TARGET_ARRAY)
            attrs["NORMAL"] = self._add_accessor(bv, CT_FLOAT, len(mesh.nrm), "VEC3")

            col_bytes = bytearray()
            for c in mesh.col:
                col_bytes.extend(struct.pack("<ffff", _f32(c[0]), _f32(c[1]),
                                             _f32(c[2]), _f32(1.0)))
            bv = self._push_bytes(bytes(col_bytes), TARGET_ARRAY)
            attrs["COLOR_0"] = self._add_accessor(bv, CT_FLOAT, len(mesh.col), "VEC4")

            uv_bytes = bytearray()
            for t in mesh.uv:
                uv_bytes.extend(struct.pack("<ff", _f32(t[0]), _f32(t[1])))
            bv = self._push_bytes(bytes(uv_bytes), TARGET_ARRAY)
            attrs["TEXCOORD_0"] = self._add_accessor(bv, CT_FLOAT, len(mesh.uv), "VEC2")

            if mesh.skinned and mesh.jnt:
                j_bytes = bytearray()
                for j in mesh.jnt:
                    j_bytes.extend(struct.pack("<BBBB", j[0] & 255, j[1] & 255,
                                               j[2] & 255, j[3] & 255))
                bv = self._push_bytes(bytes(j_bytes), TARGET_ARRAY)
                attrs["JOINTS_0"] = self._add_accessor(bv, CT_UBYTE, len(mesh.jnt), "VEC4")
                w_bytes = bytearray()
                for w in mesh.wgt:
                    w_bytes.extend(struct.pack("<ffff", _f32(w[0]), _f32(w[1]),
                                               _f32(w[2]), _f32(w[3])))
                bv = self._push_bytes(bytes(w_bytes), TARGET_ARRAY)
                attrs["WEIGHTS_0"] = self._add_accessor(bv, CT_FLOAT, len(mesh.wgt), "VEC4")

            flat = mesh.flat_indices
            max_idx = max(flat) if flat else 0
            if max_idx > 65535:
                ib = bytearray()
                for v in flat:
                    ib.extend(struct.pack("<I", v))
                bv = self._push_bytes(bytes(ib), TARGET_ELEMENT)
                acc = self._add_accessor(bv, CT_UINT, len(flat), "SCALAR")
            else:
                ib = bytearray()
                for v in flat:
                    ib.extend(struct.pack("<H", v))
                bv = self._push_bytes(bytes(ib), TARGET_ELEMENT)
                acc = self._add_accessor(bv, CT_USHORT, len(flat), "SCALAR")
            prims.append({"attributes": attrs, "indices": acc, "material": mat_idx,
                          "mode": 4})
        self.meshes.append({"name": name, "primitives": prims})
        return len(self.meshes) - 1

    # -- 节点 / 蒙皮 / 动画 ------------------------------------------------
    def add_node(self, name, mesh=None, translation=None, rotation=None,
                 scale=None, matrix=None, children=None, skin=None):
        node = {"name": name}
        if matrix is not None:
            node["matrix"] = [_round3(x) for x in matrix]
        else:
            if translation:
                node["translation"] = [_round3(x) for x in translation]
            if rotation:
                node["rotation"] = [_round3(x) for x in rotation]
            if scale:
                node["scale"] = [_round3(x) for x in scale]
        if mesh is not None:
            node["mesh"] = mesh
        if skin is not None:
            node["skin"] = skin
        if children:
            node["children"] = list(children)
        self.nodes.append(node)
        return len(self.nodes) - 1

    def add_skin(self, name, joint_nodes, ibm_matrices, skeleton_root=None):
        data = bytearray()
        for m in ibm_matrices:
            for v in m:
                data.extend(struct.pack("<f", _f32(v)))
        bv = self._push_bytes(bytes(data), TARGET_ARRAY)
        acc = self._add_accessor(bv, CT_FLOAT, len(ibm_matrices), "MAT4")
        skin = {"name": name, "joints": list(joint_nodes), "inverseBindMatrices": acc}
        if skeleton_root is not None:
            skin["skeleton"] = skeleton_root
        self.skins.append(skin)
        return len(self.skins) - 1

    def add_animation(self, name, channels, samplers):
        """channels=[{"sampler":i,"target":{"node":n,"path":"rotation"}}]
        samplers=[{"input":acc,"output":acc,"interpolation":"LINEAR"}]
        调用方需先用 self.add_keyframe_accessor 建立 input/output。"""
        self.animations.append({"name": name, "channels": channels, "samplers": samplers})
        return len(self.animations) - 1

    def add_float_accessor(self, values):
        data = bytearray()
        for v in values:
            data.extend(struct.pack("<f", _f32(v)))
        bv = self._push_bytes(bytes(data), TARGET_ARRAY)
        return self._add_accessor(bv, CT_FLOAT, len(values), "SCALAR",
                                  [_round3(min(values))], [_round3(max(values))])

    def add_vec_accessor(self, vecs, vtype):
        data = bytearray()
        n = len(vecs[0])
        for v in vecs:
            for x in v:
                data.extend(struct.pack("<f", _f32(x)))
        bv = self._push_bytes(bytes(data), TARGET_ARRAY)
        return self._add_accessor(bv, CT_FLOAT, len(vecs), vtype)

    # -- 输出 -------------------------------------------------------------
    def build(self, generator="TheSeed gen_assets.py 0.1.0-alpha"):
        padded_bin = bytes(self._bin)
        pad = (-len(padded_bin)) % 4
        padded_bin += b"\x00" * pad

        gltf = {
            "asset": {"version": "2.0", "generator": generator},
            "scene": 0,
            "scenes": [{"name": "Scene", "nodes": list(self.scene_nodes)}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self._accessors,
            "bufferViews": self._bufferviews,
            "buffers": [{"byteLength": len(padded_bin)}],
        }
        if self.images:
            gltf["images"] = self.images
        if self.textures:
            gltf["textures"] = self.textures
            gltf["samplers"] = self.samplers
        if self.skins:
            gltf["skins"] = self.skins
        if self.animations:
            gltf["animations"] = self.animations

        js = json_dumps(gltf).encode("utf-8")
        js += b" " * ((-len(js)) % 4)

        total = 12 + 8 + len(js) + 8 + len(padded_bin)
        out = bytearray()
        out.extend(struct.pack("<III", GLB_MAGIC, GLB_VERSION, total))
        out.extend(struct.pack("<II", len(js), CHUNK_JSON))
        out.extend(js)
        out.extend(struct.pack("<II", len(padded_bin), CHUNK_BIN))
        out.extend(padded_bin)
        return bytes(out)


def json_dumps(obj):
    """紧凑 JSON，键序稳定，保证字节级可复现。"""
    import json
    return json.dumps(obj, separators=(",", ":"), sort_keys=False, ensure_ascii=False)


# --------------------------------------------------------------------------
# GLB 回读校验
# --------------------------------------------------------------------------

def read_glb(path):
    """读取 GLB，返回 (gltf_json_dict, bin_length, byte_length)。用于独立校验。"""
    import json
    with open(path, "rb") as f:
        blob = f.read()
    if len(blob) < 12:
        raise ValueError("文件过短，非合法 GLB: %s" % path)
    magic, version, length = struct.unpack("<III", blob[:12])
    if magic != GLB_MAGIC:
        raise ValueError("magic 不符: %s" % path)
    if version != 2:
        raise ValueError("version 非 2: %s" % path)
    if length != len(blob):
        raise ValueError("头部长度 %d != 实际 %d: %s" % (length, len(blob), path))
    off = 12
    chunks = []
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack("<II", blob[off:off + 8])
        chunks.append((ctype, blob[off + 8: off + 8 + clen]))
        off += 8 + clen
    js_chunk = next((c for t, c in chunks if t == CHUNK_JSON), None)
    bin_chunk = next((c for t, c in chunks if t == CHUNK_BIN), b"")
    if js_chunk is None:
        raise ValueError("缺少 JSON chunk: %s" % path)
    doc = json.loads(js_chunk.decode("utf-8"))
    return doc, len(bin_chunk), length


def count_triangles(gltf_doc):
    total = 0
    for m in gltf_doc.get("meshes", []):
        for p in m.get("primitives", []):
            acc = gltf_doc["accessors"][p["indices"]]
            total += acc["count"] // 3
    return total
