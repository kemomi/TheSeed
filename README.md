# TheSeed

  
---

```markdown
# The Seed

基于 **Unreal Engine 5.3+** 的 XR（VR+MR）动作游戏开发模板，  
面向 **Meta Quest 3** 与 **Apple Vision Pro**，灵感来自《刀剑神域》中的“The Seed”。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Unreal Engine](https://img.shields.io/badge/UE-5.3%2B-orange)](https://www.unrealengine.com)

## 项目愿景

让每一个人都能创造属于自己的 **3A 级 XR 世界**。  
通过 **WorldModel** 提供的开源框架、原创美术资产与 AIGC 能力，本项目致力于：  
- 大幅降低 XR 动作游戏开发门槛  
- 为 **SAO AI** 提供官方教程与最佳实践案例  
- 构建一个类 SAO 风格的、支持多人联机的 XR MMO 动作游戏原型

## 灵感来源

项目名称“The Seed”来源于川原砾著作《Sword Art Online》中，  
那个能够制作、管理 VRMMO 世界的免费软件。  
我们希望通过这个项目，把“让所有人都能成为世界创造者”的理念带入现实。

## 核心开发与学习内容

- 构建支持 Meta Quest 等 XR 一体机应用的开发与设置环境  
- VR 场景性能优化与渲染处理  
- 带有物理反馈的冷兵器刀剑战斗、魔法战斗与枪械战斗  
- 敌人物理打击感模拟（打击特效、音效、顿帧）  
- 多种可拓展的敌人行为树 AI（技能、距离控制、动画调度）  
- XR 设备粒子特效系统的处理与优化  
- XR 原生的手势追踪 UI 交互与 UI 动画构建  
- MR 场景下与环境相融合的阴影处理  
- XR 设备串流调试与开发  
- 提供数种武器道具、十几种不同风格的士兵级/领主级/Boss 级敌人美术资产  
- 使用 AI 生成配音、音乐、3D 模型、UI 等 AIGC 功能辅助开发

## 仓库结构

```
TheSeed/
├── Source/                    # 项目核心 C++/蓝图框架
├── Content/                   # 美术资产、关卡、数据表
│   ├── GameData/
│   │   ├── DataTables/        # 技能、属性、招式等 CSV 数据表
│   │   ├── Skills/            # 技能 DataAsset
│   │   └── Bosses/            # Boss 招式与阶段配置
│   ├── AI/
│   │   ├── BehaviorTrees/     # 敌人行为树蓝图
│   │   ├── Blackboards/       # AI 黑板定义
│   │   └── Tasks/             # 自定义行为树 Task
│   └── Characters/            # 角色与敌人模型
├── The-Seed-Link-Future/
│   └── SAO_GameDesign/        # 社区设计提交目录
│       └── kemomi/            # 示例贡献者文件夹
│           ├── README.md
│           ├── SwordSkillSystem_kemomi.md
│           ├── SwitchingSystem_kemomi.md
│           ├── BossDesign_Floor1_kemomi.md
│           ├── StatGrowthSystem_kemomi.md
│           ├── GestureUISystem_kemomi.md
│           └── ... (CSV 数据表)
└── README.md
```

## 社区贡献指南（SAO_GameDesign）

我们欢迎每一位社区成员提交自己对 SAO 游戏的设计，  
所有合理的设计都有可能被采纳，并计入 **游戏制作人员名单**。

### 贡献流程

1. 在 `The-Seed-Link-Future/SAO_GameDesign/` 下，以你的 **User 代号** 新建文件夹  
2. 在该文件夹中提交你的设计文档（Markdown 格式，`*.md`）  
3. 可提交的内容包括但不限于：  
   - 数值系统设计  
   - 战斗系统机制  
   - Boss 战斗逻辑与招式表  
   - 玩法设计  
   - UI/UX 设计  
   - 技能树与行为树节点设定  
4. 说明文档需要阐述设计思路，格式清晰  
5. 若设计被采纳，贡献者 ID 将被记录在制作人员名单中

### 设计文档与引擎数据对接建议

为了让你的设计可以直接被开发团队使用，我们推荐同时提供 **UE 可导入的 DataTable 描述或 CSV 文件**，并注明在引擎中的建议导入路径。  

示例结构（来自贡献者 **kemomi** 的提交）：  
- 技能树数据表 → `Content/GameData/Skills/DT_SkillTree_1HSword`  
- 剑技详细参数 → `Content/GameData/Skills/DT_SwordSkills`  
- Boss 招式表 → `Content/GameData/Bosses/Illfang/DT_Attacks`  
- AI 行为树说明 → `Content/AI/Boss/Illfang/BT_Illfang_Phase1`（蓝图描述）  
- UI 手势识别蓝图接口说明 → `Content/UI/BP_GestureHandler`  

## 贡献者展示：kemomi 的设计包

作为社区贡献的完整示例，**kemomi** 提交了一套涵盖 5 大核心系统的设计文档与数据表：  
1. **剑技系统** – 手势触发、剑技能量、技能列表与冷却  
2. **切换（Switching）战斗连携** – 队友换手、仇恨转移与切换能量  
3. **第一层 Boss 狗头人霸主·伊尔方** – 三阶段招式、AI 行为树与弱点设计  
4. **数值与成长体系** – 属性、熟练度、等级曲线、装备强化  
5. **XR 手势 UI 交互系统** – 环形菜单、手势规范、蓝图实现要点  

所有文档均遵循 UE5.3 规范，附带了可直接导入引擎的 CSV 数据表样本。  
你可以在 `The-Seed-Link-Future/SAO_GameDesign/kemomi/` 中查看全部内容，并以此为模板提交自己的设计。

## 版权与使用说明

本项目所有原创美术资源、代码、特效、UI 等均已获得商业使用授权，  
或为 WorldModel 原创开源内容，**可用于二次开发，不涉及任何版权归属问题**。  
使用本模板开发的项目需遵循项目所附的 MIT 许可证。

## 快速开始

1. 克隆仓库：

   ```bash
   git clone https://github.com/kemomi/TheSeed.git
   ```

2. 使用 **Unreal Engine 5.3 或更高版本** 打开 `TheSeed.uproject`  
3. 根据目标设备（Quest 3 / Vision Pro）配置项目设置  
4. 导入社区提供的 DataTable CSV 文件至对应路径，即可开始调试  
5. 参考 `The-Seed-Link-Future/SAO_GameDesign/` 中的设计文档理解游戏系统意图  

---

*“这个世界的种子，现在就在你的手中。”*
```

---
