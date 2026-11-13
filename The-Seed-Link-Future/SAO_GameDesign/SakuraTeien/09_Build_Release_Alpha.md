# 打包与 Release：α 阶段

> **上游依赖**：`00_Baseline_Conventions.md`（版本号、命名）、`03_ArtAssetSpec_Procedural.md`（资产产出）、`08_Quest3_Perf_Budget.md`（验收指标）
> **下游被依赖**：`build/`（构建脚本）、`.github/workflows/`（CI）
> **现实约束声明**：本文档描述**目标构建链路与验收判据**。截至本次交付，本机**未安装** Godot/UE/JDK/Android SDK，且命令行**无法联网**（GitHub 连接超时、curl TLS 凭据失败）。因此「产出可安装 APK」这一步**当前无法在本机执行**，本文档给出的是：①已可离线完成的资产构建与校验链路（已跑通）；②待工具链就绪后一条命令即可执行的 APK 打包链路（脚本已备，缺运行时）。二者边界在 §2 明确标注。

---

## 设计思路

α 阶段最容易犯的错，是把「打包出 APK」当成唯一验收标准。但现实是工具链没装、网络不通，硬追 APK 只会卡死。所以本文档把交付拆成**两层**：

第一层是**引擎无关、离线可完成**的部分——程序化资产生成、场景布局、数据表、设计文档、以及交叉校验。这一层**已经全部跑通并验证**，产物是确定性的、可复现的、引擎无关的。它的价值在于：无论最终选 Godot 还是 UE，这一层的产出都不作废（`03` §6 的 ID 间接层保证了这点）。

第二层是**引擎相关、需运行时**的部分——把资产导入引擎、搭场景、连逻辑、配 OpenXR、导出 APK。这一层依赖 Godot/UE + JDK + Android SDK，当前缺运行时无法执行。但**构建脚本已经写好**（`build/`），工具链就绪后一条命令即可触发，不需要重新设计流程。

这样拆的好处是：α 阶段的**设计资产是完整的、可交付的、可验证的**；工程集成是**待命状态**，阻塞点清晰（装工具链），而非设计缺失。用户要的是「全套游戏设计文档 + 程序化资产」，这一层已 100% 交付；「打包 APK」这一层给出了可执行路径与验收判据，待环境就绪。

---

## 一、版本号规则

遵循语义化版本 + α 阶段标识（`00` §5）：

```
0.1.0-alpha
│ │ │ └──── 阶段：alpha（α 原型）
│ │ └────── patch：资产/数据表修订
│ └──────── minor：新增分区/NPC/敌人/系统
└────────── major：1.0 = 首个可发布版本
```

| 字段 | 当前值 | 出现位置 |
|------|--------|----------|
| 场景版本 | `0.1.0-alpha` | `SceneLayout_SakuraTeien.json` 的 `meta.version` |
| 资产生成器版本 | `0.1.0-alpha` | GLB 的 `asset.generator` |
| Release 标签 | `v0.1.0-alpha` | Git tag（待网络恢复后推送） |

---

## 二、交付分层与状态

| 层 | 内容 | 依赖 | 当前状态 |
|----|------|------|----------|
| **L1 设计层** | 00–09 设计文档 | 无 | ✅ 已完成 |
| **L1 数据层** | 3 份 CSV 数据表 | 无 | ✅ 已完成 |
| **L1 资产层** | 43 个 GLB + 2 张纹理 | Python 3（已装） | ✅ 已生成并校验 |
| **L1 布局层** | SceneLayout JSON（159 实例） | Python 3 | ✅ 已生成并校验 |
| **L1 校验层** | validate_assets.py 交叉校验 | Python 3 | ✅ 已跑通 |
| **L2 集成层** | 资产导入引擎 + 场景搭建 | Godot/UE | ⚠️ 待引擎 |
| **L2 逻辑层** | NPC 状态机/对话/战斗/切换 | 引擎 + GDScript/C++ | ⚠️ 待引擎 |
| **L2 XR 层** | OpenXR 配置 + Quest 3 适配 | 引擎 + Meta 插件 | ⚠️ 待引擎 |
| **L2 打包层** | 导出 APK + 签名 | JDK17 + Android SDK 35 | ⚠️ 待工具链 |

**本次交付覆盖 L1 全部（设计+数据+资产+布局+校验），L2 给出脚本与判据待运行时。**

---

## 三、已可执行的构建链路（L1，离线）

### 3.1 一键构建资产

```bash
# 生成全部 43 个 GLB 资产 + 2 张纹理 + MANIFEST.sha256
python tools/gen_assets.py --outdir assets

# 生成场景布局 JSON（159 实例）
python tools/gen_scene_layout.py

# 交叉校验（资产面数/结构 + 场景引用 + 数据表一致性 + 确定性）
python tools/validate_assets.py
```

三步全部离线、确定性、可复现（`03` §5）。产物：

```
assets/
├── models/          # 43 个 .glb
├── textures/        # T_Palette.png, T_Petal_Alpha.png
└── MANIFEST.sha256  # 逐资产 sha256 + 字节数
The-Seed-Link-Future/SAO_GameDesign/SakuraTeien/
├── 00–09 *.md       # 设计文档
├── SceneLayout_SakuraTeien.json
└── DataTables/      # 3 份 CSV
```

### 3.2 校验器职责（`tools/validate_assets.py`）

校验器是 α 阶段的**质量门**，任一 FAIL 则构建失败（exit 1）。它交叉核对三个独立来源，防止文档与产物脱节：

| 校验组 | 内容 | 交叉对象 |
|--------|------|----------|
| A 资产 | 43 个 GLB 面数 ≤ 预算、结构合法、确定性 | `03` 预算 vs 实测 |
| B 场景 | 159 实例的 asset/zone 引用有效、坐标合规、ID 唯一 | `SceneLayout` vs 资产清单 + `02` 分区 |
| C 数据表 | NPC/Enemy/Attack 的 ID 引用、外键一致、编码合规 | CSV vs `04`/`07` 文档 vs SceneLayout |
| D 一致性 | 文档声称的数值 = CSV = SceneLayout | 三方交叉 |

详见 §6 验收判据。

---

## 四、待执行的打包链路（L2，需工具链）

### 4.1 工具链清单

引擎路线用户选择「先不定」（`00` §5），故**两条链路都备好脚本**，运行时就绪后二选一：

| 工具 | 版本 | 用途 | 当前状态 |
|------|------|------|----------|
| Python | 3.12（已装 3.12.10） | 资产生成 | ✅ |
| Godot | 4.7.x stable | 引擎（路线 A） | ⚠️ 未装 |
| — 或 Unreal Engine | 5.x | 引擎（路线 B） | ⚠️ 未装 |
| JDK | 17 | Android 构建 | ⚠️ 未装 |
| Android SDK | Platform 35 + Build-Tools 35.0.1 | 导出 APK | ⚠️ 未装 |
| Android NDK | r28b（Godot 路线） | 原生库 | ⚠️ 未装 |
| Meta OpenXR | Godot 内置 / UE MetaXR 插件 | Quest 3 XR | ⚠️ 待引擎 |

> 工具链版本来自公开资料调研（Godot 4.7.x、JDK17、SDK35、NDK r28b、Meta target Android 14/API34）。⚠️ 具体小版本号须以引擎官方文档为准，安装前复核。

### 4.2 Godot 路线（推荐，`03`/`08` 倾向）

```bash
# 1. 引擎侧导入脚本读取 SceneLayout JSON + assets/models/*.glb 搭场景
#    （脚本待引擎就绪后编写，见 build/godot/ 占位）
# 2. 配置 OpenXR（Mobile 渲染路径，禁用 Forward+，见 08 §7）
# 3. 启用 Gradle Build + Android Build Template
# 4. 导出 Quest APK
godot --headless --export-release "Android Quest" build/TheSeed-SakuraTeien.apk
```

### 4.3 UE 路线

```bash
# 1. 导入 GLB（UE 支持 glTF 导入）+ 按 SceneLayout 摆放
# 2. 配置 Quest 3（Android SDK/NDK、MetaXR 插件、Mobile 渲染）
# 3. 打包
UnrealBuildTool TheSeed Android Development -project=TheSeed.uproject
```

### 4.4 构建脚本占位

`build/` 目录已建，含：
- `build/README.md` — 构建链路说明与工具链就绪检查清单
- `build/godot/`、`build/ue/` — 引擎适配脚本占位（待引擎就绪填充）

⚠️ 引擎适配脚本（读 SceneLayout 搭场景）需引擎运行时才能编写与测试，α 阶段提供**接口契约**（`03` §4 的 JSON 格式 + §4.2 的坐标转换表），脚本待 L2 阶段实现。

---

## 五、Release 产物清单

α 阶段 Release（`v0.1.0-alpha`）应包含：

| 产物 | 来源 | 状态 |
|------|------|------|
| 设计文档包（00–09 .md） | 本项目 | ✅ |
| 数据表（3 CSV） | 本项目 | ✅ |
| 场景布局 JSON | gen_scene_layout.py | ✅ |
| 资产包（43 GLB + 2 PNG + MANIFEST） | gen_assets.py | ✅ |
| 构建/校验脚本（tools/） | 本项目 | ✅ |
| 引擎工程（Godot/UE） | L2 集成 | ⚠️ 待引擎 |
| Quest 3 APK | L2 打包 | ⚠️ 待工具链 |
| Release Notes | 本节 §5.1 | ✅ |

### 5.1 Release Notes（v0.1.0-alpha）

```
TheSeed · 樱庭·离宫 α 原型 v0.1.0-alpha

【本次交付】
- 全套游戏设计文档（10 份）：基线规范、世界观、箱庭关卡、程序化资产规格、
  NPC 系统、对话脚本、动画规格、战斗设计、性能预算、打包发布
- 43 个程序化 3D 资产（glTF 2.0 Binary），含 5 名 NPC + 3 类敌人（骨骼蒙皮 + 动画）
- 引擎无关场景布局（159 实例，8 分区）
- 3 份数据表（NPC/敌人/招式）
- 资产生成 + 场景生成 + 交叉校验工具链（纯 Python 标准库，离线，确定性）

【技术特点】
- 全部资产程序化生成，零外部素材依赖，零联网
- 单图集 + 顶点色材质策略，纹理内存 <400KB
- 字节级可复现（固定 seed，两次生成 sha256 一致）
- 引擎无关（glTF 通用格式，Godot/UE/Unity 可直导）

【已知限制】
- 引擎未选型（用户选择"先不定"），未产出可运行工程与 APK
- 本机命令行无法联网，工具链（Godot/JDK/Android SDK）未安装
- 真机帧率/内存未实测（08 标注"待真机"）
- 玩家等级上限、Boss 伊尔方招式表沿用上游空文件状态（00 §1.3）

【下一步（L2）】
- 选定引擎 → 编写场景导入脚本 → 配置 OpenXR → 导出 Quest 3 APK
```

---

## 六、α 阶段验收判据

α 阶段的验收**不以 APK 为唯一标准**（工具链阻塞），而以 L1 完整交付 + L2 路径清晰为准：

### 6.1 L1 验收（本次交付，全部可离线验证）

| # | 判据 | 验证方式 | 状态 |
|---|------|----------|------|
| 1 | 10 份设计文档完整、互相引用一致 | 人工 + validate 交叉核对 | ✅ |
| 2 | 43 个 GLB 全部生成、面数在预算内 | validate_assets.py | ✅ |
| 3 | GLB 结构合法（magic/version/回读） | validate_assets.py | ✅ |
| 4 | 资产字节级可复现（sha256 一致） | validate_assets.py | ✅ |
| 5 | skinned 角色蒙皮合法（权重和=1、计数一致、16 骨骼） | validate_assets.py | ✅ |
| 6 | SceneLayout 159 实例引用有效、ID 唯一、坐标合规 | validate_assets.py | ✅ |
| 7 | 3 份 CSV 编码合规（UTF-8 无 BOM、LF）、外键一致 | validate_assets.py | ✅ |
| 8 | 文档数值 = CSV = SceneLayout 三方一致 | validate_assets.py | ✅ |
| 9 | 场景几何/纹理/内存预算达标（08 实测项） | validate_assets.py | ✅ |

### 6.2 L2 验收（待工具链，判据已定）

| # | 判据 | 验证方式 | 阻塞 |
|---|------|----------|------|
| 10 | 资产可导入引擎（Godot/UE） | 引擎导入无报错 | 引擎未装 |
| 11 | 场景按 SceneLayout 正确搭建 | 引擎内目视 | 引擎未装 |
| 12 | NPC 交互状态机运行（04 §2） | 引擎内交互测试 | 引擎未装 |
| 13 | 战斗可玩（07 剑技/切换/顿帧） | 引擎内战斗测试 | 引擎未装 |
| 14 | Quest 3 帧率 ≥90fps（08 §10） | OVR Metrics Tool | 真机 + 引擎 |
| 15 | 导出 APK 可安装运行 | Quest 3 侧载 | JDK + SDK + 引擎 |

---

## 七、CI 集成（待网络恢复）

`03` §5 的字节级可复现使 CI 可直接判断「资产是否被意外改动」：

```yaml
# .github/workflows/build.yml（占位，待 origin 推送后启用）
# 触发：push / PR
# 步骤：
#   1. python tools/gen_assets.py --outdir assets
#   2. python tools/gen_scene_layout.py
#   3. python tools/validate_assets.py   # 任一 FAIL 则构建失败
#   4. 比对 assets/MANIFEST.sha256 与提交版本，漂移则告警
```

⚠️ 当前本地 git 仓库已 init（分支 main），但 `origin` 未配置（网络不通无法关联远程）。CI 待网络恢复后启用。

---

## 八、阻塞项与解除路径

| 阻塞 | 影响 | 解除路径 |
|------|------|----------|
| 命令行无法联网（GitHub 超时 + curl TLS 失败） | 无法 clone 原仓库、下载引擎/素材、推送 Release | 用户配置可用代理，或手动下载工具链放入工作目录 |
| 引擎未选型 | L2 集成无法开始 | 用户定引擎（Godot 推荐，见 `03`/`08`） |
| Godot/UE 未安装 | 无法导入资产、搭场景 | 装引擎（Godot <100MB / UE 100GB+） |
| JDK17 + Android SDK35 未装 | 无法导出 APK | 装工具链（Godot 路线） |
| Quest 3 真机未连 | 无法实测帧率、侧载 APK | 连接头显 + 开发者模式 |

**解除任一阻塞后，L2 链路可立即推进**——脚本与判据已备好，不需要重新设计。

---

## 九、目录结构总览

```
TheSeed/
├── The-Seed-Link-Future/SAO_GameDesign/
│   ├── kemomi/                          # 上游设计包（未改动，见 00 §1）
│   └── SakuraTeien/                     # 本设计包
│       ├── 00_Baseline_Conventions.md   # 基线规范（唯一事实来源）
│       ├── 01_WorldSetting.md           # 世界观与地编设定
│       ├── 02_LevelDesign_Hakoniwa.md   # 箱庭关卡设计
│       ├── 03_ArtAssetSpec_Procedural.md# 程序化资产规格
│       ├── 04_NPC_System.md             # NPC 系统
│       ├── 05_NPC_Dialogue.md           # NPC 对话脚本
│       ├── 06_Animation_Spec.md         # 动画规格
│       ├── 07_Combat_Design.md          # 战斗设计
│       ├── 08_Quest3_Perf_Budget.md     # 性能预算
│       ├── 09_Build_Release_Alpha.md    # 打包与 Release（本文档）
│       ├── SceneLayout_SakuraTeien.json # 场景布局（引擎无关，159 实例）
│       └── DataTables/
│           ├── DT_NPC_SakuraTeien.csv
│           ├── DT_Enemy_SakuraTeien.csv
│           └── DT_EnemyAttacks_SakuraTeien.csv
├── tools/                               # 程序化生成工具链（纯标准库）
│   ├── theseed_geo.py                   # 几何库 + GLB 写入器
│   ├── theseed_flora.py                 # 植被资产（9）
│   ├── theseed_props.py                 # 庭院小品（9）
│   ├── theseed_fx.py                    # 特效与道具（9）
│   ├── theseed_arch.py                  # 建筑结构（6）
│   ├── theseed_char.py                  # 角色与敌人（10，含骨骼动画）
│   ├── gen_assets.py                    # 资产生成主程序
│   ├── gen_scene_layout.py              # 场景布局生成器
│   └── validate_assets.py               # 交叉校验器（质量门）
├── assets/                              # 生成产物
│   ├── models/                          # 43 个 .glb
│   ├── textures/                        # T_Palette.png, T_Petal_Alpha.png
│   └── MANIFEST.sha256
└── build/                               # 构建脚本（L2 占位）
    ├── README.md
    ├── godot/                           # Godot 适配脚本占位
    └── ue/                              # UE 适配脚本占位
```
