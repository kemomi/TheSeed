# 程序化资产规格：樱庭·离宫

> **上游依赖**：`00_Baseline_Conventions.md`（命名、单位、坐标系）、`02_LevelDesign_Hakoniwa.md`（分区与坐标）
> **下游被依赖**：`08_Quest3_Perf_Budget.md`、`tools/gen_assets.py`、`SceneLayout_SakuraTeien.json`

---

## 设计思路

外部素材下载在本项目环境下不可用（GitHub 连接超时、本机 TLS 凭据异常），因此全部 3D 资产改为**程序化生成**：用纯 Python 标准库直接写出 glTF 2.0 二进制（`.glb`），不引入任何第三方依赖，不联网。

这个约束反过来带来了三个实际好处：

1. **可复现**。资产是代码的确定性输出（固定随机种子），任何一次改动都能 diff、能回滚、能重建，不存在「素材文件丢了就完了」的风险。
2. **引擎无关**。glTF 是 Godot、Unreal、Unity 都能直接吃的通用格式。路线尚未确定引擎（见 `00` 的 α 阶段决策），产出 glTF 意味着**现在做的资产不会因为后来换引擎而作废**。
3. **面数天生可控**。手写生成器时，每个物体的分段数是显式参数，不会像下载素材那样混进一个 50 万面的精模把 Quest 3 拖垮。

代价是视觉精度：程序化低模做不到手绘精模的细节密度。这与 `01_WorldSetting.md` 已选定的「低多边形风格化」基调是一致的——不是妥协后的降级，而是本来就要走的路。

---

## 一、工具链

| 项 | 规定 |
|----|------|
| 语言 | Python 3.12（本机已装 3.12.10） |
| 第三方依赖 | **无**。仅用 `json` / `math` / `struct` / `zlib` / `random` / `os` 标准库 |
| 网络 | **不需要**。全程离线 |
| 输出格式 | glTF 2.0 Binary（`.glb`），单文件内嵌几何与贴图 |
| 贴图格式 | PNG（用 `zlib` 手写编码器生成，不依赖 Pillow） |
| 确定性 | 所有随机使用固定 seed（见 §5），同输入必得同输出字节 |
| 入口脚本 | `tools/gen_assets.py`（资产）、`tools/gen_scene_layout.py`（布局）、`tools/validate_assets.py`（校验） |
| 产物目录 | `assets/models/`、`assets/textures/` |

### 1.1 模块划分

| 文件 | 职责 |
|------|------|
| `tools/theseed_geo.py` | 几何库：向量/矩阵运算、`Mesh` 类、基础图元（盒/柱/锥/球/环/面）、PNG 编码、GLB 写入器 |
| `tools/gen_assets.py` | 资产配方：每种物体的几何构造逻辑与材质参数，调用几何库输出 `.glb` |
| `tools/gen_scene_layout.py` | 按 `02` 的分区坐标生成 `SceneLayout_SakuraTeien.json` |
| `tools/validate_assets.py` | 回读生成的 GLB，校验头部/JSON 合法性、统计面数、比对性能预算 |

---

## 二、资产清单

面数为**硬上限**，`tools/validate_assets.py` 会逐个校验，超限即构建失败。预算依据见 `08_Quest3_Perf_Budget.md`。

### 2.1 建筑与结构

| 资产 ID | 文件名 | 内容 | 尺寸 | 面数上限 | 材质 |
|---------|--------|------|------|----------|------|
| `asset_torii_main` | `SM_Torii_Gate_Main.glb` | 主鸟居：二本柱、笠木、岛木、贯、额束 | 宽 5.2m 高 4.6m | 900 | 朱漆剥落（双色顶点色） |
| `asset_torii_small` | `SM_Torii_Gate_Small.glb` | 奥之森小鸟居 | 宽 2.4m 高 2.2m | 500 | 同上，褪色更重 |
| `asset_azumaya` | `SM_Azumaya_Pavilion.glb` | 樱亭：四角攒尖顶、四柱、栏杆、抬高地台、台阶 | 7×7m 高 4.2m | 2,400 | 木构 + 瓦顶 |
| `asset_kyobashi` | `SM_Kyobashi_Bridge.glb` | 太鼓桥：拱形桥面（9 段）、两侧栏干、望柱 | 长 6.8m 拱高 0.9m | 1,400 | 木构，朱栏 |
| `asset_tea_stall` | `SM_Tea_Stall.glb` | 茶摊：四柱、布帘顶、柜台、长凳 ×2、灯笼 | 5×4m 高 2.8m | 1,600 | 木 + 布（暖色自发光灯笼） |
| `asset_karesansui_frame` | `SM_Karesansui_Frame.glb` | 枯山水：白川砂地面（耙纹用顶点位移）、围石 12 块、缘侧木台 | 11×10m | 2,200 | 白砂 + 苔石 |

### 2.2 庭院小品

| 资产 ID | 文件名 | 内容 | 尺寸 | 面数上限 | 备注 |
|---------|--------|------|------|----------|------|
| `asset_ishidoro_tall` | `SM_Ishidoro_Tall.glb` | 石灯笼（春日型）：基座、竿、中台、火袋、笠、宝珠 | 高 1.6m | 480 | 火袋内自发光球，**可击碎** |
| `asset_ishidoro_short` | `SM_Ishidoro_Short.glb` | 石灯笼（置灯篭型）：矮款 | 高 0.7m | 320 | 可击碎 |
| `asset_shishiodoshi` | `SM_ShishiOdoshi.glb` | 鹿威し：竹筒、支点、石钵、支架 | 高 1.1m | 420 | 有动画（见 `06`），触发音 |
| `asset_rock_cluster_a` | `SM_Rock_Cluster_A.glb` | 石组 A：3 块组合 | 2.2×1.8m | 360 | 十二面体抖动生成 |
| `asset_rock_cluster_b` | `SM_Rock_Cluster_B.glb` | 石组 B：5 块组合 | 3.0×2.4m | 520 | 同上 |
| `asset_rock_single` | `SM_Rock_Single.glb` | 单石 | 0.8m | 120 | 十二面体 |
| `asset_stepping_stone` | `SM_Stepping_Stone.glb` | 飞石（汀步） | 0.55×0.4m | 64 | 扁圆柱 + 抖动 |
| `asset_chozubachi` | `SM_Chozubachi.glb` | 手水钵：石钵 + 竹管 | 高 0.6m | 280 | 水面材质 |
| `asset_calling_stone` | `SM_Calling_Stone.glb` | 呼应石：扁平可站立石台 | 1.2×0.9m | 140 | 见 `02` §9，用于拉近切换距离 |

### 2.3 植被

| 资产 ID | 文件名 | 内容 | 尺寸 | 面数上限 | 备注 |
|---------|--------|------|------|----------|------|
| `asset_sakura_tree_large` | `SM_Sakura_Tree_Large.glb` | 大樱花树：主干 + 3 级分枝 + 14 团树冠 | 高 6.5m 冠幅 7m | 3,200 | 树冠为抖动的二十面体簇 |
| `asset_sakura_tree_mid` | `SM_Sakura_Tree_Mid.glb` | 中樱花树 | 高 4.2m 冠幅 4.5m | 1,800 | 9 团树冠 |
| `asset_sakura_tree_small` | `SM_Sakura_Tree_Small.glb` | 小樱花树 | 高 2.4m 冠幅 2.6m | 900 | 5 团树冠 |
| `asset_sakura_solo` | `SM_Sakura_Solo.glb` | 独樱（对景物，见 `02` §4.3） | 高 5.0m | 2,000 | 造型刻意不对称 |
| `asset_pine_black` | `SM_Pine_Black.glb` | 黑松：伞状分层树冠 | 高 4.0m | 1,200 | 枯山水与奥之森用 |
| `asset_bamboo_cluster` | `SM_Bamboo_Cluster.glb` | 竹林丛：7 竿 + 叶簇 | 高 3.5m 占地 1.5m | 800 | 边界遮挡用，株距密 |
| `asset_bush_round` | `SM_Bush_Round.glb` | 球形灌木（刈込） | 直径 1.1m | 320 | 修剪整齐，庭园感来源 |
| `asset_grass_tuft` | `SM_Grass_Tuft.glb` | 草丛 | 0.4m | 48 | 十字交叉面片 |
| `asset_moss_patch` | `SM_Moss_Patch.glb` | 苔藓片 | 1.2m | 32 | 贴地圆面，顶点色渐变 |

### 2.4 角色与敌人

| 资产 ID | 文件名 | 内容 | 尺寸 | 面数上限 | 备注 |
|---------|--------|------|------|----------|------|
| `asset_npc_base` | `SK_NPC_Base.glb` | 人形基础体：头、躯干、四肢、和服下摆，含骨骼 | 高 1.7m | 1,600 | 5 名 NPC 共用，靠材质与配件区分 |
| `asset_npc_hair_variants` | `SM_NPC_Hair_Variants.glb` | 4 种发型网格 | — | 600 | 每款 ≤150 面 |
| `asset_npc_prop_lantern` | `SM_NPC_Prop_Lantern.glb` | 手提灯笼（枫用） | 0.35m | 200 | 带自发光 + OmniLight 挂点 |
| `asset_npc_prop_hammer` | `SM_NPC_Prop_Hammer.glb` | 石匠锤（源藏用） | 0.4m | 140 | 动画驱动 |
| `asset_npc_prop_teacup` | `SM_NPC_Prop_Teacup.glb` | 茶碗（三乃用） | 0.12m | 80 | — |
| `asset_npc_prop_miko_wand` | `SM_NPC_Prop_MikoWand.glb` | 巫女笏（椿用） | 0.5m | 100 | — |
| `asset_enemy_sakura_oni` | `SK_Enemy_SakuraOni.glb` | 樱鬼：矮壮人形、树皮质感、单角、含骨骼 | 高 1.4m | 1,400 | 「兵」「刃」共用网格，配件与材质区分 |
| `asset_enemy_hikabusho` | `SK_Enemy_Hikabusho.glb` | 绯甲武者：全身甲、面具、太刀、含骨骼 | 高 1.9m | 2,600 | 区域守卫，唯一有甲片细节的敌人 |
| `asset_weapon_tachi` | `SM_Weapon_Tachi.glb` | 太刀 | 长 1.05m | 240 | 玩家与绯甲武者共用 |
| `asset_weapon_katana_oni` | `SM_Weapon_OniBlade.glb` | 樱鬼刃的骨刀 | 长 0.8m | 160 | — |

### 2.5 特效与道具

| 资产 ID | 文件名 | 内容 | 面数上限 | 备注 |
|---------|--------|------|----------|------|
| `asset_petal` | `SM_Sakura_Petal.glb` | 单片花瓣：1 个四边形，内嵌 RGBA 贴图 | 2 | `alphaMode: BLEND`，双面 |
| `asset_ground_tile` | `SM_Ground_Tile.glb` | 地面瓦片：可平铺，含参道石板与草地两种顶点色 | 64 | 程序化铺设 |
| `asset_water_surface` | `SM_Water_Surface.glb` | 镜池水面：细分平面，顶点动画 | 800 | 16×16 段 |
| `asset_fog_plane` | `SM_Fog_Plane.glb` | 边界雾片：4 个交叉大面片 | 8 | 顶点色渐变透明 |
| `asset_sky_dome` | `SM_Sky_Dome.glb` | 天空球：程序化渐变，内表面渲染 | 480 | 不用 HDRI |
| `asset_crystal_record` | `SM_Crystal_Record.glb` | 记录结晶：八面体 + 自发光 | 48 | 拾取物 |
| `asset_crystal_corridor` | `SM_Crystal_Corridor.glb` | 回廊结晶：十二面体拉长 | 64 | 传送道具 |
| `asset_item_dango` | `SM_Item_Dango.glb` | 樱饼/团子：3 球串签 | 120 | 商店道具图标兼世界模型 |
| `asset_item_whetstone` | `SM_Item_Whetstone.glb` | 强化石 | 96 | 支线奖励 |

**资产总数：44 个 GLB 文件。场景实例化后的总面数预算见 `08`。**

---

## 三、材质规范

### 3.1 材质策略：单图集 + 顶点色

全部资产共用 **1 张 256×256 调色板纹理** `T_Palette.png`，UV 映射到对应色块。理由：

- Quest 3 上纹理切换是 DrawCall 合批的头号杀手，单图集意味着**理论上全场景可合批为个位数 DrawCall**；
- 明暗变化用**顶点色**承载，不需要逐物体的 AO / Lightmap 纹理，省掉大量内存；
- 程序化生成时，UV 只是「选哪个色块」，比生成合理的手绘 UV 简单一个数量级。

调色板布局（256×256，每格 32×32，8×8 网格）：

| 行\列 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|-------|---|---|---|---|---|---|---|---|
| 0 | 樱 `#F2C6D0` | 樱深 `#D98FA3` | 樱白 `#FAE8EC` | 树皮 `#6E5346` | 树皮暗 `#4A372E` | 木构 `#8B5A3C` | 木构暗 `#5E3A26` | 竹 `#7E9A5B` |
| 1 | 鸟居朱 `#B33A2B` | 朱剥落 `#6E6259` | 瓦 `#4A4E57` | 瓦暗 `#33363D` | 石 `#9A968E` | 石暗 `#6F6C66` | 白川砂 `#E8E4DC` | 苔 `#6B8055` |
| 2 | 草地 `#7C9A5E` | 草暗 `#5C7744` | 水面 `#4E7A82` | 水深 `#33555C` | 布帘 `#C8B79A` | 纸灯 `#F5D9A8` | 冷调 `#5C6B7A` | 冷暗 `#3E4A56` |
| 3 | 绯甲 `#A33B32` | 绯甲暗 `#6E2620` | 金饰 `#C9A24A` | 鬼肌 `#8E6B7A` | 鬼肌暗 `#5E4450` | 角 `#D8CFC0` | 骨白 `#E3DED4` | 墨黑 `#2A2A2E` |
| 4 | 肌 `#E8C4A8` | 发黑 `#2E2A33` | 发红 `#8B3A3A` | 白衣 `#EDEAE3` | 绯袴 `#A8434F` | 青着 `#4A6B82` | 茶着 `#8A7358` | 灰着 `#6E6E72` |
| 5–7 | *预留*（发光色阶、阴影色阶、UI 色） | | | | | | | |

自发光色（灯笼火、结晶、甲胄目）不走调色板，用 `emissiveFactor` 直接给值。

### 3.2 材质参数

| 材质名 | baseColor 来源 | metallic | roughness | alphaMode | doubleSided | emissive |
|--------|---------------|----------|-----------|-----------|-------------|----------|
| `M_Palette_Opaque` | 调色板纹理 | 0.0 | 0.85 | OPAQUE | false | — |
| `M_Palette_Stone` | 调色板纹理 | 0.0 | 0.92 | OPAQUE | false | — |
| `M_Palette_Wood` | 调色板纹理 | 0.0 | 0.78 | OPAQUE | false | — |
| `M_Palette_Metal` | 调色板纹理 | 0.65 | 0.42 | OPAQUE | false | — |
| `M_Water` | 调色板纹理 | 0.0 | 0.12 | OPAQUE | false | — |
| `M_Petal` | `T_Petal_Alpha.png` | 0.0 | 0.70 | BLEND | true | — |
| `M_Foliage_Cutout` | 调色板纹理 | 0.0 | 0.88 | OPAQUE | true | — |
| `M_Lantern_Glow` | 调色板纹理 | 0.0 | 1.0 | OPAQUE | false | `#F5D9A8` ×2.0 |
| `M_Crystal_Glow` | 调色板纹理 | 0.0 | 0.20 | OPAQUE | true | `#8FD3E8` ×2.5 |
| `M_Fog` | 顶点色 | 0.0 | 1.0 | BLEND | true | — |
| `M_Sky` | 顶点色渐变 | 0.0 | 1.0 | OPAQUE | true（内表面） | — |

**全部材质均不带法线贴图、不带 ORM 贴图**。α 阶段的 PBR 只用 baseColor + metallic + roughness 三通道，这是 Quest 3 移动端管线的务实选择。

### 3.3 顶点色使用规则

顶点色（`COLOR_0`，VEC3 float）承载三类信息，与 baseColor 相乘：

| 用途 | 取值范围 | 说明 |
|------|----------|------|
| 环境遮蔽（AO） | 0.55–1.0 | 根部、接缝、内凹处压暗 |
| 高度渐变 | 0.75–1.0 | 树冠上亮下暗、石头上亮下暗 |
| 做旧/剥落 | 双色插值 | 鸟居朱漆剥落处插值到 `朱剥落` 色，权重由噪声决定 |

生成器中实现为 `Mesh.paint_gradient(axis, low, high)` 与 `Mesh.paint_noise(color_a, color_b, weight_fn)`。

---

## 四、场景布局文件格式（引擎无关）

`SceneLayout_SakuraTeien.json` 是坐标的**唯一权威来源**（见 `02` §10）。格式定义：

```json
{
  "meta": {
    "name": "LV_SakuraTeien_Main",
    "version": "0.1.0-alpha",
    "unit": "meter",
    "coordinate": "right-handed, +Y=north, +X=east, +Z=up",
    "generator": "tools/gen_scene_layout.py",
    "source_of_truth": "02_LevelDesign_Hakoniwa.md"
  },
  "zones": [
    {
      "id": "zone_torii_approach",
      "name_cn": "鸟居参道",
      "shape": "rect",
      "size": [4.0, 14.0],
      "center": [0.0, -17.0, 0.0],
      "safe": true,
      "petal_density": 0.3,
      "wind_deg": 180.0,
      "navmesh": false
    }
  ],
  "instances": [
    {
      "id": "torii_gate_main",
      "asset": "asset_torii_main",
      "zone": "zone_torii_approach",
      "position": [0.0, -22.0, 0.0],
      "rotation_deg": [0.0, 0.0, 0.0],
      "scale": [1.0, 1.0, 1.0],
      "collision": "box",
      "destructible": false,
      "tags": ["landmark", "boundary_south"]
    }
  ],
  "lights": [
    {
      "id": "sun_main",
      "type": "directional",
      "rotation_deg": [-52.0, 0.0, 38.0],
      "color": [1.0, 0.95, 0.88],
      "energy": 1.15,
      "shadow": true,
      "shadow_resolution": 2048
    }
  ],
  "spawners": [
    {
      "id": "spawn_grove_oni",
      "zone": "zone_sakura_grove",
      "enemy": "enemy_sakura_oni_grunt",
      "count": 3,
      "respawn_sec": 90,
      "positions": [[2.0, 13.0, 0.6], [4.5, 15.5, 0.6], [1.0, 16.0, 0.6]]
    }
  ],
  "npc_placements": [
    { "id": "npc_sannosuke", "zone": "zone_tea_stall", "position": [-7.0, -13.5, 0.0], "rotation_deg": 15.0 }
  ],
  "volumes": [
    { "id": "vol_safe_torii", "type": "safe_zone", "zone": "zone_torii_approach" },
    { "id": "vol_combat_domain", "type": "combat_domain", "zones": ["zone_ishidoro_path", "zone_sakura_grove", "zone_okunomori"] },
    { "id": "vol_boundary_fog", "type": "fog", "shape": "ring", "inner_radius": 26.0, "outer_radius": 34.0, "density": 1.0 }
  ]
}
```

### 4.1 字段约定

| 字段 | 类型 | 规则 |
|------|------|------|
| `position` | `[x, y, z]` | 米，右手系，见 `00` §4 |
| `rotation_deg` | `[rx, ry, rz]` 或标量 | 度；标量表示绕 Z（上）轴旋转，0° 朝北 |
| `scale` | `[sx, sy, sz]` | 无量纲，默认 `[1,1,1]` |
| `collision` | 枚举 | `none` / `box` / `cylinder` / `heightmap` / `convex` |
| `asset` | string | 必须是 §2 清单中的资产 ID，禁止引用清单外资产 |
| `zone` | string | 必须是 §2.2 分区表中的 zone ID |
| `destructible` | bool | 为 true 时必须在 `07` 中定义破坏行为 |

### 4.2 引擎适配约定

各引擎导入脚本必须自行处理坐标系差异，**JSON 本身不做转换**：

| 引擎 | 转换规则 |
|------|----------|
| Godot | 直接对应（Godot 为右手系 +Y up，但本 JSON 用 +Z up）：`godot_pos = (x, z, -y)` |
| Unreal | 左手系 +Z up，1m = 100uu：`ue_pos = (x*100, y*100, z*100)` |
| Unity | 左手系 +Y up：`unity_pos = (x, z, y)` |

转换表在此登记一次，避免各引擎适配脚本各写一套导致不一致。

---

## 五、确定性与可复现

| 项 | 规定 |
|----|------|
| 随机种子 | 全局 `SEED = 20261113`；每类资产用 `SEED + hash(asset_id) % 10000` 派生子种子 |
| 浮点精度 | 输出 GLB 时顶点坐标保留 float32；JSON 中坐标保留 3 位小数 |
| 时间戳 | **不写入**任何产物（GLB 的 `asset.generator` 只写工具名与版本，不写时间），保证同输入产出字节一致 |
| 排序 | 所有遍历字典/集合的地方必须显式 `sorted()`，不依赖解释器顺序 |
| 校验 | `tools/validate_assets.py` 输出每个 GLB 的字节数与 SHA-256，登记在 `assets/MANIFEST.sha256` |

字节级可复现的实际价值：CI 里可以直接判断「资产是否被意外改动」，不需要人工比对二进制文件。

---

## 六、外部素材的后续替换路径

α 阶段程序化生成是**被迫但合理**的选择。若后续网络恢复，替换路径如下（登记备查，不影响本次交付）：

| 需求 | 建议来源 | 授权 | 替换成本 |
|------|----------|------|----------|
| 樱花树精模 | Sketchfab「Cherry Blossom Trees」(Jagobo) | CC-BY（需署名） | 低：同 ID 替换 GLB，场景布局不变 |
| 鸟居 | Sketchfab「Japanese Torii Gate」(Sahir) | 页面标注为准，⚠️ 需逐个核实 | 低 |
| 石灯笼 | Sketchfab「Japanese Lantern」(GinMichel) | 页面标注为准，⚠️ 需核实 | 低 |
| 神社低模组 | itch.io「SceneForge Studio」5 shrine models | CC0，标注可商用 | 低 |
| 日式街巷模块 | itch.io「AlleyBits」Japanese Back Alley | 免费，⚠️ 授权需核实 | 中：尺度需重对齐 |
| 自然植被基底 | Kenney「Nature Kit」 | CC0 | 低 |
| 低模自然包 | Quaternius「150+ LowPoly Nature」 | CC0 | 低 |
| NPC 角色与动画 | Mixamo（Adobe） | 免费可商用，Royalty-Free | 中：需重绑本包骨骼 |
| CC0 动画角色 | Quaternius「Ultimate Animated Character Pack」 | CC0 | 低 |
| CC0 通用动画库 | Quaternius「Universal Animation Library 2」 | CC0 | 低 |

**注意**：Ready Player Me 已于 2026-01-31 停止服务（被 Netflix 收购），不在候选内。

替换时**必须保持资产 ID 与文件名不变**，这样 `SceneLayout_SakuraTeien.json` 与所有数据表都不需要修改——这正是 ID 间接层的价值。

---

## 七、已知妥协

| 项 | 妥协内容 | 影响 | 处理 |
|----|----------|------|------|
| 水面可行走 | 见 `02` §6.1，水面有碰撞视为地面 | 玩家会"走在水面上"，观感差 | α 接受，⚠️ 后续改为不可行走 + 桥体引导 |
| 无 LOD | 程序化资产单一级别细节 | 远处物体面数不降 | 靠 `08` 的距离剔除（Culling）补偿 |
| 无光照贴图 UV | 只用顶点色 + 单图集 | 烘焙光照质量受限 | α 用烘焙 Lightmap 时按引擎自动展开 UV，或接受动态光 |
| 树冠无碰撞 | 见 `02` §6.1 | 头部可穿过树叶 | VR 中可接受，且省性能 |
| 细节密度低 | 程序化低模无手绘细节 | 近看偏"素" | 与风格化基调一致；靠顶点色与光照补层次 |
