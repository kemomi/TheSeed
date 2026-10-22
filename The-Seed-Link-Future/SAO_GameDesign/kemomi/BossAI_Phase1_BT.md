# Boss 行为树设计：伊尔方·阶段一（BT_Illfang_Phase1）
**贡献者：kemomi**

> 配套文档：`BossDesign_Floor1.md`
> 引擎建议路径：`Content/AI/Boss/Illfang/BT_Illfang_Phase1`（行为树资产）
> 黑板资产路径：`Content/AI/Boss/Illfang/BB_Illfang`
> 数据表路径：`Content/GameData/Bosses/Illfang/DT_Attacks`（对应 `Boss_Illfang_Attacks.csv`）

## 设计目标
阶段一（100%–75% HP）伊尔方装备斧与圆盾，动作缓慢、偏防守反击。本行为树负责该阶段的感知、移动、攻击选择与阶段转换检测，需在 UE5.3 的 `UBehaviorTree` / `UBehaviorTreeComponent` 上可直接搭建。

## 黑板键（Blackboard Keys）
| 键名 | 类型 | 说明 |
|------|------|------|
| `TargetActor` | TObjectPtr<AActor> | 当前仇恨目标（玩家） |
| `TargetDistance` | float | 到目标的距离，由 Task 实时刷新 |
| `HPPercent` | float | 当前血量百分比，由 Boss 自身广播 |
| `Phase` | uint8 | 当前阶段（1/2/3），用于互斥运行 |
| `bInAttack` | bool | 是否正在播放攻击动画（锁定选择器） |
| `bInvincible` | bool | 转阶段无敌窗口 |
| `PatrolPoint` | FVector | 巡逻目标点 |
| `AggroLevel` | float | 仇恨值，用于切换目标判定 |

## 行为树结构
```
BT_Illfang_Phase1 (Root)
└── Selector [阶段一专属]
    ├── Sequence [阶段转换检测]            # 优先级最高
    │   ├── Decorator: HPPercent <= 0.75
    │   ├── Task: BTTask_TryPhaseTransition (→ Phase 2)
    │   └── Task: BTTask_PlayPhaseMontage（咆哮+换武器，期间 bInvincible=true）
    ├── Sequence [战斗循环]
    │   ├── Decorator: Phase == 1 && !bInvincible
    │   ├── Selector [感知与接近]
    │   │   ├── Sequence [无目标 → 巡逻]
    │   │   │   ├── Task: BTTask_UpdatePatrolPoint
    │   │   │   └── Task: BTTask_MoveTo(PatrolPoint, accept=1.0m)
    │   │   └── Sequence [有目标 → 接近/攻击]
    │   │       ├── Task: BTTask_UpdateTargetDistance
    │   │       ├── Selector [距离分支]
    │   │       │   ├── Sequence [近身 <2m]
    │   │       │   │   ├── Decorator: TargetDistance < 2.0
    │   │       │   │   └── Task: BTTask_ChooseAttack (权重 50% 横扫 / 50% 盾击)
    │   │       │   ├── Sequence [中距 2–5m]
    │   │       │   │   ├── Decorator: 2.0 <= TargetDistance <= 5.0
    │   │       │   │   └── Task: BTTask_ChooseAttack (权重 60% 跳劈 / 40% 冲刺横斩)
    │   │       │   └── Sequence [远距 >5m → 接近]
    │   │       │       └── Task: BTTask_MoveTo(Target, accept=5.0m)
    │   │       └── Task: BTTask_ExecuteAttack (读 DT_Attacks，播放 Montage，设 bInAttack)
    │   └── Task: BTTask_Wait(0.2s)   # 节拍，避免每帧重选
    └── Task: BTTask_Fail   # 兜底
```

## 自定义 Task 说明
| Task | 职责 | 关键实现 |
|------|------|-----------|
| `BTTask_UpdateTargetDistance` | 刷新 `TargetDistance` | 每次执行取 `TargetActor` 距离写入黑板 |
| `BTTask_ChooseAttack` | 按权重随机选定招式 ID | 读取 `DT_Attacks` 中 `Phase==1` 行，按权重抽样，写入 `PendingAttackID` |
| `BTTask_ExecuteAttack` | 执行招式 | 设 `bInAttack=true`，播放对应 Montage（带根运动），命中判定走 Anim Notify，结束后清 `bInAttack` |
| `BTTask_TryPhaseTransition` | 检测并执行转阶段 | 若 `HPPercent` 跨阈值，置 `Phase=2`、`bInvincible=true`，返回 Success 触发上层 Sequence |
| `BTTask_PlayPhaseMontage` | 播放转阶段演出 | 咆哮→丢弃圆盾→拔太刀，结束回调中 `bInvincible=false` 并重置仇恨 |

## 装饰器与条件
- `Cooldown` 装饰器：限制 `BTTask_ChooseAttack` 最低间隔 1.2s（阶段一偏慢）。
- `ForceSuccess`：巡逻移动失败时不中断整棵树。
- 距离判定优先用黑板 `TargetDistance`，避免每次都走 AI 感知查询的开销。

## 阶段切换衔接
- 转阶段动画期间 `bInvincible=true`，受击不扣血；演出前 0.3s 仍为霸体，之后可被命中但不打断演出。
- 演出结束 → 由 AIController 按 `Phase` 键切换运行 `BT_Illfang_Phase2`，仇恨表清空后重新锁定最近玩家。

## 性能注意（XR / Quest3）
- 感知（`UAIPerceptionComponent`）更新频率设 0.2s，视距 50m，FOV 120°。
- 阶段切换时先 `StopLogic` 再 `RunBehaviorTree`，避免双树并行。
- 攻击命中使用球形 Sweep 而非物理碰撞，降低 Quest3 上的 PhysX 开销。
