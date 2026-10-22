# kemomi 的 SAO 设计包
**贡献者：kemomi**

本目录是 `TheSeed` 社区贡献的完整示例，涵盖 5 大核心系统的设计文档与可直接导入 UE5.3 的 CSV 数据表。
可作为其他贡献者提交设计的模板。

## 文档清单
| 文档 | 系统 | 说明 |
|------|------|------|
| `SwordSkillSystem.md` | 剑技系统 | 手势触发、剑技能量、技能列表与冷却 |
| `SwitchingSystem.md` | 切换连携 | 队友换手、仇恨转移与切换能量 |
| `BossDesign_Floor1.md` | 第一层 Boss | 伊尔方三阶段招式、弱点与数值 |
| `BossAI_Phase1_BT.md` | Boss 行为树 | 阶段一行为树节点、黑板与自定义 Task |
| `StatGrowthSystem.md` | 数值与成长 | 属性、熟练度、等级曲线、装备强化 |
| `StatGrowth_Extended.md` | 数值扩展 | 成长体系补充细则 |
| `GestureUISystem.md` | 手势 UI | 环形菜单、手势规范 |
| `UI_GestureImplementation.md` | UI 实现 | 手势蓝图实现要点 |

## 数据表（可直接导入 UE5.3 DataTable）
| CSV 文件 | 建议导入路径 | 说明 |
|----------|--------------|------|
| `SwordSkillData.csv` | `Content/GameData/Skills/DT_SwordSkills` | 剑技数值表 |
| `SkillTree_OneHanded.csv` | `Content/GameData/Skills/DT_SkillTree_1HSword` | 单手剑技能树 |
| `Boss_Illfang_Attacks.csv` | `Content/GameData/Bosses/Illfang/DT_Attacks` | 伊尔方招式表 |

## 引擎对接建议
- 技能树 → `Content/GameData/Skills/DT_SkillTree_1HSword`
- 剑技参数 → `Content/GameData/Skills/DT_SwordSkills`
- Boss 招式 → `Content/GameData/Bosses/Illfang/DT_Attacks`
- AI 行为树 → `Content/AI/Boss/Illfang/BT_Illfang_Phase1`（蓝图描述见 `BossAI_Phase1_BT.md`）
- UI 手势接口 → `Content/UI/BP_GestureHandler`

## 使用方式
1. 将 CSV 导入 UE5.3 对应路径的 DataTable（结构体字段需与表头一致）。
2. 参考各 `.md` 文档理解设计意图与实现要点。
3. 以本目录为模板，在 `SAO_GameDesign/<你的代号>/` 下提交自己的设计。
