# 动画规格：樱庭·离宫

> **上游依赖**：`00_Baseline_Conventions.md`（命名 `A_`/`anim_`）、`03_ArtAssetSpec_Procedural.md` §2.4（角色资产）、`04_NPC_System.md`（状态机用到的动画）
> **下游被依赖**：`07_Combat_Design.md`、`tools/theseed_char.py`（实现）、`SceneLayout_SakuraTeien.json`
> **实现状态**：本文档描述的骨骼、动画片段、蒙皮方式**已在 `tools/theseed_char.py` 中实现并通过校验**（16 骨骼、权重和=1、GLB 回读合法）。本文档是该实现的设计说明与对接契约。

---

## 设计思路

VR 里角色动画的评判标准和屏幕游戏不同。屏幕游戏看剪影和节奏，VR 看**「这个东西在我面前是不是活的」**——玩家会把头凑到 NPC 脸前 30 厘米打量，任何一个关节穿模、任何一次脚底打滑都会被放大成「假」。所以本项目的动画原则是：**宁可幅度小、不可穿帮**。

第二个约束来自资产生成方式。所有角色是程序化生成的低模，没有动捕数据、没有 Mixamo 绑定（网络不可用，见 `03` §1）。这意味着动画只能**程序化生成**——用正弦摆动叠加关键帧。好处是完全可控、可复现、零外部依赖；代价是动作偏「机械」，没有动捕的自然重量感。对此的补偿是：把功夫下在**呼吸、重心微移、注视转向**这些「活着」的信号上，而不是追求华丽的招式表演。低模风格化本身也降低了玩家对动作精度的期待，两者是自洽的。

第三，骨骼数量必须克制。Quest 3 上每个 skinned draw call 的骨骼矩阵上传是实打实的开销，16 根是「够表达人形 + 不拖累性能」的平衡点（对比：Mixamo 标准骨架 65 根，UE Mannequin 70+）。本文档的 16 骨骼足以支撑待机、行走、挥手、鞠躬、挥砍、倒地——覆盖 α 阶段全部需求。

---

## 一、骨骼层级（16 根）

bind pose 为直立、双臂自然下垂（沿 −Z）、面向 +Y（北）。所有骨骼旋转轴以 bind pose 为准。

```
Hips (0)                      world z=0.90   根，重心
├─ Spine (1)                  world z=1.06
│  └─ Chest (2)               world z=1.26   胸腔，呼吸/扭转主骨骼
│     ├─ Head (3)             world z=1.50   头部，注视 IK 目标
│     ├─ UpperArm.R (4)       肩 +X 侧        world z=1.40
│     │  └─ LowerArm.R (5)    肘
│     │     └─ Hand.R (6)     腕，右手配件挂点
│     └─ UpperArm.L (7)       肩 −X 侧
│        └─ LowerArm.L (8)    肘
│           └─ Hand.L (9)     腕，左手配件挂点
├─ UpperLeg.R (10)            髋 +X 侧        world z=0.88
│  └─ LowerLeg.R (11)         膝
│     └─ Foot.R (12)          踝              world z=0.06
└─ UpperLeg.L (13)            髋 −X 侧
   └─ LowerLeg.L (14)         膝
      └─ Foot.L (15)          踝
```

### 1.1 骨骼约定

| 约定 | 规则 |
|------|------|
| 命名后缀 | `.R` = 角色右手侧（+X），`.L` = 左手侧（−X）。从角色自身视角，非玩家视角 |
| 配件挂点 | `Hand.R`（右手持物：锤、笏、太刀）、`Hand.L`（左手持物：灯笼） |
| 旋转轴 | 所有动画只写 `rotation`（四元数），不写 translation/scale，避免骨骼长度变化 |
| bind 朝向 | 四肢沿 −Z（下垂），故「抬臂」= 绕 X 轴正向旋转 |
| 身高缩放 | 通过根节点 scale 整体缩放（樱鬼 1.4m = 0.82×，武者 1.9m = 1.12×），骨骼比例不变 |

### 1.2 蒙皮方式

| 部位 | 绑定方式 | 说明 |
|------|----------|------|
| 头、手、脚、角、配件 | 刚性绑定（单骨骼 100%） | 低模无需平滑过渡 |
| 上臂/前臂、大腿/小腿 | 刚性绑定到对应段骨骼 | 每段独立 |
| 躯干（胸腹） | 按 z 在 Hips/Spine/Chest 间线性混合 | 弯腰/转身自然 |
| 和服下摆（袴） | 按 z 在 Hips/Spine 间混合 | 随髋摆动 |

刚性绑定是低模角色的通行做法：关节处不做平滑权重，靠几何分块掩盖。实现见 `theseed_char.py` 的 `bind_rigid()` 与 `rebind_by_z()`。

---

## 二、动画片段清单

命名遵循 `A_<对象>_<动作>`（资产前缀），运行时 ID 为 `anim_<对象>_<动作>`。所有片段以「循环 / 单次」标注——引擎侧据此决定是否 loop。

### 2.1 NPC 动画集（`anim_set = npc_base`）

| 动画 ID | glTF 名 | 时长 | 循环 | 主要骨骼 | 用途（状态机） |
|---------|---------|------|------|----------|----------------|
| `anim_npc_idle` | `A_NPC_Idle` | 3.0s | 是 | Chest/Spine/Head/UpperArm | `Idle`/`Aware` 待机呼吸 |
| `anim_npc_wave` | `A_NPC_Wave` | 2.4s | 否 | UpperArm.R/LowerArm.R/Head | `Greet`（三乃/枫） |
| `anim_npc_talk` | `A_NPC_Talk` | 2.0s | 是 | Head/UpperArm.R/Chest | `Talk` 说话 |
| `anim_npc_bow` | `A_NPC_Bow` | 2.2s | 否 | Spine/Chest/Head | `Greet`（椿/源藏）鞠躬 |
| `anim_npc_walk` | `A_NPC_Walk` | 1.0s | 是 | 四肢交替 + Hips | `Patrol`（枫） |
| `anim_npc_sit` | `A_NPC_Sit` | 3.0s | 是 | 髋膝弯曲保持 + Spine | 源藏坐缘侧凿石 |

### 2.2 樱鬼动画集（`anim_set = sakura_oni`）

| 动画 ID | glTF 名 | 时长 | 循环 | 用途 |
|---------|---------|------|------|------|
| `anim_oni_idle` | `A_Oni_Idle` | 2.2s | 是 | 待机（幅度比 NPC 大，显躁动） |
| `anim_oni_walk` | `A_Oni_Walk` | 0.9s | 是 | 逼近玩家 |
| `anim_oni_attack` | `A_Oni_Attack` | 1.1s | 否 | 挥砍（举→劈，含前摇） |
| `anim_oni_hit` | `A_Oni_Hit` | 0.4s | 否 | 受击后仰 |
| `anim_oni_die` | `A_Oni_Die` | 1.3s | 否 | 倒地（末帧保持） |

### 2.3 绯甲武者动画集（`anim_set = hikabusho`）

| 动画 ID | glTF 名 | 时长 | 循环 | 用途 |
|---------|---------|------|------|------|
| `anim_busho_idle` | `A_Busho_Idle` | 2.2s | 是 | 待机（fierce，幅度大） |
| `anim_busho_walk` | `A_Busho_Walk` | 0.9s | 是 | 逼近 |
| `anim_busho_guard` | `A_Busho_Guard` | 2.5s | 是 | 双手持刀警戒（非战斗） |
| `anim_busho_attack` | `A_Busho_Attack` | 1.1s | 否 | 挥砍 |
| `anim_busho_hit` | `A_Busho_Hit` | 0.4s | 否 | 受击 |
| `anim_busho_die` | `A_Busho_Die` | 1.3s | 否 | 倒地 |

### 2.4 环境动画（非骨骼，见 §5）

| 动画 | 对象 | 类型 | 说明 |
|------|------|------|------|
| 鹿威し摆动 | `asset_shishiodoshi` 竹筒 | 程序化（引擎侧） | 周期 18–32s，绕支点摆动敲石，触发音（`01` §3） |
| 水面波动 | `asset_water_surface` | 顶点动画 shader | 16×16 段正弦叠加 |
| 花瓣飘落 | `asset_petal` | 粒子系统 | 见 `02` §7 与本文 §5 |
| 树冠摇曳 | 樱花树冠 | 顶点动画 shader（风） | α 可选，见 §6 |

---

## 三、动画生成方式

全部为**程序化生成**，无外部动捕。实现见 `theseed_char.py`。三种基元：

### 3.1 正弦摆动（循环动画）

用于呼吸、待机、行走等循环动作。绕指定轴做正弦摆动：

```
angle(t) = base + amp × sin(2π × t/period + phase)
```

- `amp`：幅度（度）。待机呼吸 1–2°，行走摆臂 18–24°。
- `period`：周期。左右交替的肢体用 `phase = π` 反相。
- 采样 13 帧/周期（LINEAR 插值），足够平滑且数据小。

行走示例（`anim_npc_walk`）：右腿 `phase=0`、左腿 `phase=π` 反相摆动 ±24°，手臂与同侧腿反相（右臂配左腿），Hips 做上下 ±1.5° 与左右 ±2.5° 的重心移动。

### 3.2 关键帧序列（单次动画）

用于挥手、鞠躬、攻击、倒地等非循环动作。手动定义时间点与四元数，LINEAR 插值。

攻击示例（`anim_enemy_attack`，1.1s）：
| t | 动作 | UpperArm.R |
|---|------|-----------|
| 0.0 | 起始 | 0° |
| 0.35×dur | **举刀过顶**（前摇，可读招） | 绕 X +150° |
| 0.50×dur | 蓄力微转 | 绕 Y −20° |
| 0.62×dur | **劈下**（打击帧） | 绕 X −55° |
| 1.0×dur | 收势 | 0° |

前摇（0→0.35）刻意拉长到约 0.39s，给玩家读招与闪避/切换的反应窗口——这与 `07` 的战斗节奏设计一致。

### 3.3 静止保持（姿势锁定）

用于坐姿、持刀警戒等需长时间维持固定姿势的动画。用 2 帧相同四元数「锁定」目标骨骼，叠加其他骨骼的微小正弦摆动（呼吸）避免完全僵死。

坐姿示例（`anim_npc_sit`）：大腿绕 X −80°（前抬）、小腿绕 X +75°（后折）锁定，Spine/Chest 叠加 ±3° 呼吸。

### 3.4 四元数与插值

- 所有旋转用四元数（`quat_from_axis_angle`），避免欧拉角万向锁。
- glTF 动画采样器用 LINEAR 插值（四元数在引擎侧做球面归一化）。
- 采样率：循环动画 13 帧/周期，单次动画 4–7 关键帧。

---

## 四、动画状态机对接

引擎侧动画控制器按下表组织（`04` §2 状态机的动画落地）。这些状态机**不在 GLB 内**（glTF 动画不含状态机逻辑），由引擎侧 AnimationTree/Animator 实现，本文档定义其契约。

### 4.1 NPC 动画控制器

```
状态            动画                  过渡条件
─────────────────────────────────────────────────────
Idle      →  anim_npc_idle (loop)   玩家<8m或注视 → Aware
Aware     →  anim_npc_idle (loop)   首次<4m → Greet ; 交互 → Talk
             + Head IK 注视          玩家远离 → Idle
Greet     →  anim_npc_wave/bow(1次) 播完 → Aware
Talk      →  anim_npc_talk (loop)   对话结束 → Aware
Trade     →  anim_npc_idle + 臂IK   关闭 → Talk
Service   →  anim_npc_sit + 臂IK    关闭 → Talk
Patrol    →  anim_npc_walk (loop)   玩家在分区 → Aware（仅枫）
```

### 4.2 敌人动画控制器（樱鬼/武者共用结构）

```
状态            动画                  过渡条件
─────────────────────────────────────────────────────
Idle      →  anim_*_idle (loop)     发现玩家 → Chase
Chase     →  anim_*_walk (loop)     进入攻击距离 → Attack
Attack    →  anim_*_attack (1次)    打击帧触发伤害判定；播完 → Chase/Cooldown
Hit       →  anim_*_hit (1次)       受击打断；播完 → Chase
Die       →  anim_*_die (1次)       HP≤0；末帧保持 → 尸体淡出
（武者额外）
Guard     →  anim_busho_guard(loop) 非战斗警戒；玩家拔刀 → Idle(敌对)
```

攻击动画的**打击帧**（约 0.62×dur）是伤害判定与顿帧（Hit Stop）的触发点，见 `07`。

### 4.3 动画事件

GLB 不含事件轨道，事件由引擎侧按时间轴标注。契约如下：

| 动画 | 事件时间点 | 事件 | 消费方 |
|------|-----------|------|--------|
| `anim_*_attack` | 0.62×dur | `damage_frame`（伤害判定） | 战斗系统 |
| `anim_*_attack` | 0.62×dur | `hit_stop`（顿帧 0.05s） | 战斗系统（上游 Boss 取值） |
| `anim_*_attack` | 0.35×dur | `sfx_swing`（挥空音） | 音频 |
| `anim_*_die` | 0.7×dur | `sfx_death` + `vfx_dissolve` | 音频/特效 |
| `anim_npc_bow` | 0.35×dur | `dialogue_start` | 对话系统 |
| 鹿威し | 敲石帧 | `sfx_shishiodoshi` | 音频 |

---

## 五、非骨骼动画

### 5.1 鹿威し（Shishi-odoshi）

日式庭园的竹筒敲石装置，靠水力周期摆动。这是本区域**最重要的听觉点睛**（`01` §3）。

| 参数 | 值 |
|------|-----|
| 摆动轴 | 竹筒中段支点（`asset_shishiodoshi` 的 `tube` 部件，见 `03` §2.2 parts） |
| 周期 | 18–32s 随机（非固定，避免机械感） |
| 摆动曲线 | 缓慢充水（0–80% 周期，倾斜 −15°）→ 快速倒水回弹（80–85%，+25°）→ 敲石（85%）→ 静止余韵 |
| 触发音 | 敲石帧播放 `S_ShishiOdoshi_Knock`，音量随玩家距离衰减 |
| 位置 | 镜池东南岸（`SceneLayout` 实例 `shishiodoshi_001`，坐标 `(4.2;3.0;0)`） |

实现：引擎侧 Tween/AnimationPlayer 驱动 `tube` 节点旋转，非 GLB 内置动画。

### 5.2 水面波动

`asset_water_surface`（16×16 段平面）用顶点着色器做正弦叠加：

```
z(x,y,t) = A1·sin(k1·x + ω1·t) + A2·sin(k2·y + ω2·t)
A1=0.02m, A2=0.015m, ω 使周期约 4s
```

花瓣落水时在落点产生环形涟漪（局部振幅叠加，衰减 1.5s）。

### 5.3 樱吹雪粒子

花瓣粒子系统，参数按分区密度（`02` §7 与 `SceneLayout` 的 `petal_emitters`）：

| 参数 | 值 |
|------|-----|
| 网格 | `asset_petal`（单四边形，2 三角，BLEND 双面） |
| 生命周期 | 生成 → 飘落 6–9s → 落地 → 停留 12s → 淡出 1.5s |
| 飘落 | 重力 + 横向风力（按 `wind_deg`）+ 正弦摇摆（模拟飘落不规则） |
| 密度 | 按分区 `petal_density`（0.2–1.0），交战中 ×0.4 |
| 堆积 | **不堆积**（落地后定时淡出），避免透明排序开销 |
| 单区粒子上限 | 见 `08` 性能预算 |

---

## 六、可选增强（α 不强制）

| 增强 | 说明 | 成本 | α 状态 |
|------|------|------|--------|
| 树冠风摇 | 顶点着色器按风场偏移树冠顶点 | 低（shader） | ⚠️ 可选，未实现 |
| 头部注视 IK | NPC 头部实时朝向玩家（`04` §2.3） | 中（引擎侧 IK） | 设计已定义，引擎侧实现 |
| 布料模拟 | 和服下摆物理摆动 | 高 | ✗ α 不做 |
| 面部表情 | 低模无面骨骼 | — | ✗ 见 `04` §8 |
| 手势 IK | 持物手精确贴合配件 | 中 | ⚠️ β |

---

## 七、与外部动画的替换路径

若后续网络恢复（`03` §6），可替换为 Mixamo / Quaternius 动画：

| 需求 | 来源 | 授权 | 重定向 |
|------|------|------|--------|
| 类人基础动画 | Mixamo | 免费可商用 | 需重定向到本 16 骨骼（Mixamo 65 骨→16 骨映射） |
| CC0 动画角色 | Quaternius Ultimate Animated Character | CC0 | 骨骼命名需对齐 |
| CC0 通用动画库 | Quaternius Universal Animation Library 2 | CC0 | 130+ 动画，可重定向 |

重定向的关键是**骨骼命名映射表**——把外部骨架的 Hips/Spine/... 映射到本 16 骨骼。替换动画**不需要改状态机契约**（§4），只要片段名对齐 `anim_*` ID 即可。这正是把动画集名与状态机解耦的价值。

---

## 八、实现校验状态

本文档描述的动画已全部在 `tools/theseed_char.py` 实现，并通过：

| 校验项 | 结果 |
|--------|------|
| 骨骼数 = 16，IBM 矩阵 = 16 | ✓ |
| 蒙皮顶点 JOINTS_0/WEIGHTS_0 计数与 POSITION 一致 | ✓ |
| 每顶点权重和 = 1（误差 <0.02） | ✓ |
| 动画 target 节点索引有效 | ✓ |
| GLB 回读结构合法（magic/version/length） | ✓ |
| 确定性（两次生成字节一致） | ✓ |
| 面数在预算内（NPC 508、樱鬼 554、武者 636） | ✓ |

校验脚本见 `tools/validate_assets.py`（`09` §构建流程）。
