# TheSeed — 樱庭·离宫（工作副本）

> **本副本状态**：因本机命令行无法联网（GitHub 连接超时、curl TLS 凭据失败），未能 clone 原仓库 `kemomi/TheSeed`。本副本为**本地初始化的工作仓库**（`git init`，分支 `main`，远程 `origin` 待网络恢复后关联）。
>
> 本副本聚焦「樱庭·离宫」箱庭地编场景的 **α 阶段全套设计文档 + 程序化资产**，是原仓库 SAO 设计体系下的一个地编贡献包。

---

## 与原仓库的关系

原仓库 `kemomi/TheSeed` 的 `The-Seed-Link-Future/SAO_GameDesign/kemomi/` 是战斗/数值/Boss 设计包。本副本在同一目录结构下新增 **`SakuraTeien/`** 设计包，补齐原仓库缺失的**地编层与 NPC 层**（原仓库无场景、无 NPC、无可运行工程，仅设计文档 + 空 CSV，见 `SakuraTeien/00_Baseline_Conventions.md` §1.1/§1.3）。

本包**继承**上游剑技/切换/数值/Boss 设定，**不修改** `kemomi/` 任何文件。网络恢复后，`SakuraTeien/` 可作为独立贡献包提交至原仓库对应目录。

---

## 快速开始（L1，离线可跑）

```bash
# 生成全部资产（43 GLB + 2 纹理 + MANIFEST）
python tools/gen_assets.py --outdir assets

# 生成场景布局（159 实例，8 分区）
python tools/gen_scene_layout.py

# 交叉校验（质量门，任一 FAIL 则 exit 1）
python tools/validate_assets.py
```

纯 Python 3 标准库，零第三方依赖，零联网，字节级可复现。

---

## 目录结构

```
TheSeed/
├── README.md                          # 本文件（工作副本说明）
├── .gitignore
├── The-Seed-Link-Future/SAO_GameDesign/
│   └── SakuraTeien/                   # 樱庭·离宫设计包（本次交付）
│       ├── 00_Baseline_Conventions.md # 基线规范（唯一事实来源）
│       ├── 01_WorldSetting.md         # 世界观与地编设定
│       ├── 02_LevelDesign_Hakoniwa.md # 箱庭关卡设计（8 分区）
│       ├── 03_ArtAssetSpec_Procedural.md # 程序化资产规格（43 资产）
│       ├── 04_NPC_System.md           # NPC 系统（5 NPC，交互状态机）
│       ├── 05_NPC_Dialogue.md         # NPC 对话脚本（台词唯一来源）
│       ├── 06_Animation_Spec.md       # 动画规格（16 骨骼，动画集）
│       ├── 07_Combat_Design.md        # 战斗设计（3 敌人，衔接上游）
│       ├── 08_Quest3_Perf_Budget.md   # Quest 3 性能预算
│       ├── 09_Build_Release_Alpha.md  # 打包与 Release（L1/L2 分层）
│       ├── SceneLayout_SakuraTeien.json # 场景布局（引擎无关，坐标权威）
│       └── DataTables/                # 数据表（UTF-8 无 BOM，LF）
│           ├── DT_NPC_SakuraTeien.csv
│           ├── DT_Enemy_SakuraTeien.csv
│           └── DT_EnemyAttacks_SakuraTeien.csv
├── tools/                             # 程序化生成工具链（纯标准库）
│   ├── theseed_geo.py                 # 几何库 + glTF/GLB 写入器 + PNG 编码
│   ├── theseed_flora.py               # 植被（9 资产）
│   ├── theseed_props.py               # 庭院小品（9 资产）
│   ├── theseed_fx.py                  # 特效与道具（9 资产）
│   ├── theseed_arch.py                # 建筑结构（6 资产）
│   ├── theseed_char.py                # 角色与敌人（10 资产，骨骼蒙皮+动画）
│   ├── gen_assets.py                  # 资产生成主程序
│   ├── gen_scene_layout.py            # 场景布局生成器
│   └── validate_assets.py             # 交叉校验器（α 质量门）
├── assets/                            # L1 产物（可复现）
│   ├── models/                        # 43 个 .glb
│   ├── textures/                      # T_Palette.png, T_Petal_Alpha.png
│   └── MANIFEST.sha256                # 逐资产 sha256 + 字节数
└── build/                             # L2 构建链路（占位，待引擎）
    ├── README.md                      # 构建说明 + 工具链清单
    ├── godot/IMPORT_CONTRACT.md       # Godot 导入契约
    └── ue/IMPORT_CONTRACT.md          # UE 导入契约
```

---

## 交付状态（α 阶段）

| 层 | 内容 | 状态 |
|----|------|------|
| L1 设计 | 10 份设计文档 | ✅ |
| L1 数据 | 3 份 CSV 数据表 | ✅ |
| L1 资产 | 43 GLB + 2 纹理（含骨骼动画角色） | ✅ 校验通过 |
| L1 布局 | SceneLayout（159 实例） | ✅ 校验通过 |
| L1 校验 | 交叉校验器 29 项 | ✅ ALL PASS |
| L2 集成 | 引擎导入 + 场景 + 逻辑 | ⚠️ 待引擎 |
| L2 打包 | Quest 3 APK | ⚠️ 待工具链 |

详见 `SakuraTeien/09_Build_Release_Alpha.md`。

---

## 阻塞项

1. **命令行无法联网**：GitHub 超时 + curl TLS 凭据失败（`SEC_E_NO_CREDENTIALS`）。无法 clone 原仓库、下载引擎/素材、推送 Release。
2. **引擎未选型**：用户选择「先不定，只做引擎无关的产出」。
3. **工具链未装**：Godot/UE、JDK17、Android SDK35 均未安装。

解除任一路径见 `build/README.md` §五。

---

## 许可

沿用原仓库 MIT 许可（见 `03` §6 与上游 README）。程序化资产为本项目原创生成，无外部素材版权问题。
