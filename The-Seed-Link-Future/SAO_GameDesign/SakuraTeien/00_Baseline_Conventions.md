# 基线规范（Baseline Conventions）

> 本文档是「樱庭·离宫」设计包的**唯一事实来源**。其余所有文档中出现的术语、数值口径、命名前缀、数据表格式，均以本文为准；如与本文冲突，以本文为准并回改冲突文档。
>
> 上游基线：`The-Seed-Link-Future/SAO_GameDesign/kemomi/`（剑技系统、切换系统、数值成长、Boss 伊尔方、手势 UI）。本文档**继承**其设定，不推翻。

---

## 一、继承与差异声明

### 1.1 直接继承 kemomi 设计包的内容

下列设定在本设计包中**原样沿用**，不重新定义、不修改数值：

| 系统 | 来源文档 | 继承的关键数值 |
|------|----------|----------------|
| 属性体系 | `StatGrowthSystem.md` | STR / AGI / VIT / SPR 四维；初始 20 点可分配，每级 +3 |
| 派生公式 | `StatGrowthSystem.md` | 物攻 = 武器基础 + STR×2；最大HP = 200 + VIT×10；攻速 +0.5%/点 AGI；剑技能量上限 = 100 + SPR×2 |
| 升级曲线 | `StatGrowthSystem.md` | `EXP_need = floor(100 × level^1.5 + 50)` |
| 熟练度 | `StatGrowthSystem.md` | 区间 0–1000；150 解锁「水平二连斩」，500 解锁「星爆气流斩」 |
| 装备强化 | `StatGrowthSystem.md` | +1～+15，成功率递减（+1:100% … +10:50% … +15:15%）；+4 以下无惩罚，+5~+10 失败等级 −1，+10 以上失败 30% 概率损毁 |
| 回复机制 | `StatGrowthSystem.md` | 脱战 5 秒后每秒回复 (VIT×0.5 + 5)；剑技能量基础 1/秒，普攻命中 +5 |
| 剑技四式 | `SwordSkillSystem.md` | 垂直斩 150%/0.6s/6s、水平斩 120%/0.4s/4s、突刺 200%/0.8s/8s、回旋斩 80%×2/1.0s/12s |
| 剑技触发流程 | `SwordSkillSystem.md` | 准备姿势（静止 0.3s 武器发光）→ 指令识别 → 系统接管动画（0.3–1.2s 不可取消） |
| 切换（Switching） | `SwitchingSystem.md` | 目视 ≤15m；瞬移至队友旁 1m；队友后退 2m；全局冷却 1.5s；仇恨强制转移且原仇恨 −30%；2s 内第三次切换伤害 +50% 并破防；队伍共享 Switch Gauge 上限 5 点，每次 −1，每 8s +1 |
| 手势 UI | `GestureUISystem.md` / `UI_GestureImplementation.md` | 环形菜单与手势规范，本包 NPC 交互沿用其手势语义 |

### 1.2 本设计包新增的内容

kemomi 设计包覆盖的是**战斗与数值层**，缺少**地编层与 NPC 层**。本包补齐：

| 新增系统 | 文档 | 说明 |
|----------|------|------|
| 世界观与地编设定 | `01_WorldSetting.md` | 樱庭·离宫在艾恩葛朗特中的定位、历史、氛围 |
| 箱庭关卡设计 | `02_LevelDesign_Hakoniwa.md` | 8 个分区、尺度、流线、光照与视锥设计 |
| 程序化资产规格 | `03_ArtAssetSpec_Procedural.md` | 全部模型由脚本生成，本文定义几何、面数、材质参数 |
| NPC 系统 | `04_NPC_System.md` | 5 名 NPC 的职能、交互状态机、好感度、日程 |
| NPC 对话脚本 | `05_NPC_Dialogue.md` | 逐句台词、分支条件、语音与字幕规格 |
| 动画规格 | `06_Animation_Spec.md` | 人形骨骼定义、动画片段清单、程序化生成方式 |
| 战斗设计（区域） | `07_Combat_Design.md` | 樱鬼 / 绯甲武者，衔接剑技与切换系统 |
| 性能预算 | `08_Quest3_Perf_Budget.md` | Quest 3 面数、DrawCall、纹理、帧率硬指标 |
| 打包与 Release | `09_Build_Release_Alpha.md` | 导出链路、版本号规则、Release 产物清单 |

### 1.3 明确未定义项（不得凭空补全）

上游 kemomi 文档中以下内容为**空文件或缺失**，本包不代为编造，仅登记缺口：

| 缺口 | 上游状态 | 本包处理方式 |
|------|----------|--------------|
| `BossAI_Phase1_BT.md` | 0 字节空文件 | 本包不涉及 Boss 伊尔方 AI，仅在 `07` 中定义区域级敌人的行为树；Boss 行为树待上游补全 |
| `Boss_Illfang_Attacks.csv` | 0 字节空文件 | 本包不补伊尔方招式表；`DataTables/DT_Enemy_SakuraTeien.csv` 只覆盖樱庭区域敌人 |
| `SkillTree_OneHanded.csv` | 0 字节空文件 | 本包不定义技能树；仅在 `04` 中引用熟练度阈值 |
| `SwordSkillData.csv` | 0 字节空文件 | 剑技参数以 `SwordSkillSystem.md` 正文表格为准，本包 `07` 直接引用不复制 |
| 玩家等级上限 | 上游未提及 | **保持未定义**。本包所有数值按 1–20 级区间给出，超出部分标注「⚠️ 待上游确认」 |

---

## 二、术语表

### 2.1 世界观术语

| 术语 | 英文/罗马音 | 定义 |
|------|-------------|------|
| 艾恩葛朗特 | Aincrad | 100 层浮游城，游戏世界本体 |
| 起始之镇 | Town of Beginnings | 第一层主城镇，玩家初始出生点 |
| 樱庭·离宫 | Sakura Teien | 本设计包的地编对象，第一层独立箱庭区域 |
| 箱庭 | Hakoniwa | 封闭、可一眼看尽、手工雕琢的小型庭院式关卡形态 |
| 樱吹雪 | Sakura Blizzard | 樱花花瓣飘落的持续环境效果，本区域核心视觉符号 |
| 结晶 | Crystal | SAO 通用消耗品载体（回廊结晶、记录结晶等） |

### 2.2 系统术语

| 术语 | 英文 | 定义 |
|------|------|------|
| 剑技 | Sword Skill | 系统辅助的必杀技，见继承表 |
| 剑技能量 | Sword Gauge | 剑技消耗资源，上限 100 + SPR×2 |
| 切换 | Switching | 队友换手连携机制，见继承表 |
| 切换槽 | Switch Gauge | 队伍共享资源，上限 5 点 |
| 硬直 | Recovery Time | 动作后的不可操作时间，受 AGI 削减：`RecoveryTime × (1 - AGI/200)` |
| 顿帧 | Hit Stop | 命中瞬间的时间冻结，上游 Boss 取值 0.05s |
| 交互射线 | Interaction Ray | XR 控制器/手部发出的拾取射线，NPC 交互入口 |
| 世界空间 UI | World-Space UI | 锚定在 3D 物体上的 UI，区别于贴屏 UI；XR 下**强制使用**此项 |

### 2.3 术语标注约定

- 首次出现的专有名词使用「中文（English）」形式，如「剑技（Sword Skill）」；同文档内后续出现只用中文。
- 日式人名采用「汉字（罗马音）」形式，如「樱守·枫（Kaede）」。
- 资源命名一律使用 ASCII，不含中文、不含空格。

---

## 三、命名规范

### 3.1 资产前缀（继承上游 README）

| 前缀 | 用途 | 上游示例 | 本包示例 |
|------|------|----------|----------|
| `DT_` | DataTable 数据表 | `DT_SwordSkills` | `DT_NPC_SakuraTeien` |
| `BT_` | BehaviorTree 行为树 | `BT_Illfang_Phase1` | `BT_SakuraOni_Grunt` |
| `BP_` | Blueprint / 蓝图类 | `BP_GestureHandler` | `BP_NPC_Interactable` |
| `SM_` | StaticMesh 静态网格 | — | `SM_Sakura_Tree_Large` |
| `SK_` | SkeletalMesh 骨骼网格 | — | `SK_NPC_Kaede` |
| `M_` | Material 材质 | — | `M_Sakura_Petal` |
| `MI_` | MaterialInstance 材质实例 | — | `MI_Sakura_Petal_Pink` |
| `T_` | Texture 贴图 | — | `T_Stone_Lantern_N` |
| `A_` | Animation 动画片段 | — | `A_NPC_Idle_Breath` |
| `FX_` | 粒子/特效 | — | `FX_Sakura_Blizzard` |
| `S_` | Sound 音效 | — | `S_ShishiOdoshi_Knock` |
| `LV_` | Level 关卡 | — | `LV_SakuraTeien_Main` |

### 3.2 命名大小写规则

- 资产名：`前缀_PascalCase_下划线分组`，例：`SM_Torii_Gate_Main`
- 数据表文件名：`DT_<内容>_<区域>.csv`，例：`DT_NPC_SakuraTeien.csv`
- 场景节点名：`小写下划线`（用于 JSON 场景布局文件），例：`torii_gate_main`
- ID 字段：全小写下划线，例：`npc_kaede`、`enemy_sakura_oni_grunt`

### 3.3 CSV 数据表规范

上游三个 CSV 均为空文件，故格式由本文档**首次定义**，后续所有数据表必须遵守：

| 项 | 规定 |
|----|------|
| 编码 | UTF-8 **无 BOM**（BOM 会破坏部分引擎的表头解析） |
| 行尾 | LF（`\n`），不使用 CRLF |
| 分隔符 | 英文逗号 `,` |
| 引号 | 字段含逗号/引号/换行时用英文双引号包裹，内部双引号写成两个 `""` |
| 首行 | 表头，**逐字固定**，不得增删列或改列序（新增列一律追加到末尾） |
| 注释 | **不支持**注释行。说明写入 `00_Baseline_Conventions.md` 或对应设计文档，不写进 CSV |
| 空值 | 用空字段表示「无」，不写 `null` / `N/A` / `-` |
| 布尔 | 统一 `true` / `false`，小写 |
| 浮点 | 保留必要小数位，不补零（写 `0.6` 不写 `0.60`）；秒为单位的时间一律带 `s` 语义但**不加单位后缀**，数值即秒 |
| 向量 | 三分量写 `x,y,z` 会被逗号拆列，故统一用分号分隔：`x;y;z` |
| 本地化文本 | CSV 中**不存放**玩家可见台词。台词存放于 `05_NPC_Dialogue.md`，CSV 只存 `dialogue_id` 外键 |

### 3.4 ID 空间

| ID 前缀 | 空间 | 示例 |
|---------|------|------|
| `npc_` | NPC 实例 | `npc_kaede` |
| `dlg_` | 对话节点 | `dlg_kaede_first_meet` |
| `enemy_` | 敌人类型 | `enemy_sakura_oni_grunt` |
| `item_` | 道具 | `item_sakura_dango` |
| `asset_` | 程序化资产 | `asset_sakura_tree_large` |
| `anim_` | 动画片段 | `anim_npc_idle_breath` |
| `zone_` | 关卡分区 | `zone_torii_approach` |
| `quest_` | 任务 | `quest_lantern_lighting` |

---

## 四、单位与坐标系

| 项 | 规定 |
|----|------|
| 长度单位 | **米（m）**。上游未规定，本文档首次统一。引擎侧换算：Unreal 1m = 100uu；Godot 1m = 1 unit |
| 坐标系 | 右手系，+Y 为北，+X 为东，+Z 为上 |
| 角度 | 度（degree），逆时针为正，0° 朝向 +Y（北） |
| 时间 | 秒（s），保留一位小数 |
| 原点 | 樱庭·离宫几何中心 = 世界原点 `(0;0;0)`，即「镜池」圆心 |
| 地面基准 | 参道入口地面高度 = `z:0.0`；亭子地板 = `z:0.45`；地形起伏范围 `z:-0.3 ~ z:1.2` |

场景布局数据见 `SceneLayout_SakuraTeien.json`，该文件为**引擎无关**格式，任何引擎的导入脚本都应以此为唯一坐标来源。

---

## 五、α 阶段范围界定

| 维度 | α 阶段包含 | α 阶段不包含 |
|------|-----------|-------------|
| 地图 | 8 分区全部可通行、有碰撞、有视觉完成度 | 无缝大世界、多层楼层、动态天气系统 |
| NPC | 5 名，基础对话 + 商店 + 强化 + 组队切换教学 | 全语音、动态日程 AI、好感度分支剧情网 |
| 战斗 | 樱鬼（2 变体）+ 绯甲武者（区域守卫），单人可通关 | Boss 伊尔方、多人联机、PvP |
| 平台 | Meta Quest 3 单机构建 | Apple Vision Pro、PC VR、串流优化 |
| 交互 | 控制器射线 + 基础手部追踪 | 全身追踪、眼动、面部表情 |
| 音频 | 环境音 + UI 音 + 命中音（占位素材） | 原创配乐、配音、动态混音 |

α 阶段的**验收判据**见 `09_Build_Release_Alpha.md` 第三节。

---

## 六、文档维护规则

1. 任何数值改动必须**先改本文档**（若属于继承项则改上游文档），再改引用处。
2. 每份文档头部必须标注「上游依赖」与「下游被依赖」，形成可追溯链路。
3. 标注 `⚠️ 待确认` 的条目禁止进入 CSV 数据表，避免脏数据流入引擎。
4. 本包不修改 `kemomi/` 目录下任何文件；如需上游变更，另开 issue 描述，由上游贡献者决定。
