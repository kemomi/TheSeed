Root (Priority Selector)
├─ [Service: Check Phase Transition]  // 每0.5秒检测血量，若进入阶段2则跳转
├─ Sequence: 死亡处理 (优先最高)
│   ├─ Decorator: 血量 ≤ 0
│   └─ Task: Play Death Animation & Loot Spawn
├─ Sequence: 反控制处理 (高优先级)
│   ├─ Decorator: 受到眩晕/冻结等
│   ├─ Task: Play Stun Anim
│   └─ Task: Wait (2s)
├─ Sequence: 巡逻/待机 (低优先级)
│   ├─ Selector: 目标选择
│   │   ├─ Decorator: Has Target (黑板变量)
│   │   └─ Task: Find Nearest Player (设置 Target 到黑板)
│   ├─ Decorator: Distance to Target > 1500
│   └─ Task: Move To Target (Speed: Walk)
├─ Sequence: 战斗主循环
│   ├─ Decorator: Has Target
│   ├─ Selector: 距离条件分支
│   │   ├─ [0-250cm] Sequence: 近距离
│   │   │   ├─ Task: Rotate to Face Target
│   │   │   ├─ Random Selector (权重)
│   │   │   │   ├─ (50%) Task: 纵劈 (Attack 101)
│   │   │   │   └─ (50%) Task: 盾击 (Attack 103)
│   │   │   └─ Task: Wait (Cooldown随机1.5-2.5s)
│   │   ├─ [250-500cm] Sequence: 中距离
│   │   │   ├─ Task: Rotate to Face Target
│   │   │   ├─ Random Selector
│   │   │   │   ├─ (60%) Task: 横扫 (Attack 102)
│   │   │   │   └─ (40%) Task: 跳劈 (Attack 105)
│   │   │   └─ Task: Wait (2-3s)
│   │   └─ [>500cm] Sequence: 远距离
│   │       ├─ Task: Move To (Speed: Run, 接近到400cm)
│   │       └─ Task: 咆哮 (Attack 104)
│   └─ Loop (无限)
└─ Service: Update Blackboard (每0.2秒更新 Target、Distance)