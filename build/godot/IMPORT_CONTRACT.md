# Godot 场景导入契约（占位）

> 状态：**接口契约**。Godot 4.7.x 与 Android 工具链就绪后，按本契约实现 `import_scene.gd`。
> 引擎无关输入：`SceneLayout_SakuraTeien.json` + `assets/models/*.glb` + `DataTables/*.csv`。

---

## 一、坐标转换（权威）

SceneLayout 用右手系 **+X东 +Y北 +Z上**；Godot 用右手系 **+X右 +Y上 +Z前（朝屏幕外）**。

```
godot_pos = (json_x, json_z, -json_y)
```

旋转：JSON 的 `rotation_deg[0]` 为绕世界 +Z（上）轴，对应 Godot 绕 +Y（上）轴，取负：
```
godot_rotation.y = -deg_to_rad(json_rotation_deg[0])
```

依据见 `03` §4.2。导入脚本**必须**用此转换，不得自创。

---

## 二、导入流程

```
1. 读 SceneLayout_SakuraTeien.json
2. 对每个 zone：建 Node3D，设 ground_z
3. 对每个 instance：
   - 加载 assets/models/<asset.file>.glb 为 PackedScene
   - 实例化，应用坐标转换，设 position/rotation/scale
   - 按 collision 字段加 CollisionShape3D（box/cylinder/none）
   - destructible=true 的挂 Area3D + 破坏逻辑（见 07）
4. 对每个 npc_placement：
   - 按 variant 装配（见 §三）
   - 挂 NPC 状态机脚本（见 04 §2）
   - 加交互 Area3D（interact_radius_m）+ 注视检测（04 §2.3）
5. 对每个 spawner：建敌人刷新器（见 07 §7）
6. 对每个 light：建 DirectionalLight3D/OmniLight3D/WorldEnvironment
7. 对每个 petal_emitter：建 GPUParticles3D（见 06 §5.3、08 §6）
8. 对每个 volume：建 Area3D（safe_zone/combat_domain/fog/audio_trigger）
```

---

## 三、NPC variant 装配（04 §1.1）

| variant | 网格 GLB | 发型索引 | 手持配件 GLB | 挂点 | robe/robe2 |
|---------|----------|----------|--------------|------|------------|
| mino | SK_NPC_Base | 0 short | SM_NPC_Prop_Teacup | Hand.L | blue_kimono/white_robe |
| tsubaki | SK_NPC_Base | 3 hood | SM_NPC_Prop_MikoWand | Hand.R | white_robe/red_hakama |
| genzo | SK_NPC_Base | 2 topknot | SM_NPC_Prop_Hammer | Hand.R | brown_kimono/grey_kimono |
| kaede | SK_NPC_Base | 1 long | SM_NPC_Prop_Lantern | Hand.L | grey_kimono/white_robe |
| busho | SK_Enemy_Hikabusho | 2 topknot | SM_Weapon_Tachi | Hand.R | armor_red/armor_dark |

材质色替换：改调色板 UV 或 `baseColorFactor`（单图集，见 `03` §3.1）。
配件挂点：`Hand.R`/`Hand.L` 骨骼（`06` §1.1）。

---

## 四、OpenXR / 渲染配置（08 §7）

```
渲染器：Mobile 或 Compatibility（禁用 Forward+）
XR：OpenXR 启用，Mobile 渲染路径
MSAA 3D：4x
固定注视点渲染 FFR：中档
阴影：主光 2048，级联 2
实时 GI/SDFGI：禁用（烘焙 Lightmap）
SSR：禁用
体积雾：禁用（用 fog_plane 面片）
后期：最小化（α 无色分级）
```

---

## 五、动画集映射（06 §2）

GLB 内置动画名 → 状态机动画节点：

| anim_set | GLB 动画名 | 循环 |
|----------|-----------|------|
| npc_base | A_NPC_Idle/Wave/Talk/Bow/Walk/Sit | idle/talk/walk/sit 循环；wave/bow 单次 |
| sakura_oni | A_Oni_Idle/Walk/Attack/Hit/Die | idle/walk 循环；其余单次 |
| hikabusho | A_Busho_Idle/Walk/Guard/Attack/Hit/Die | idle/walk/guard 循环；其余单次 |

动画事件（打击帧/顿帧/音效）按时间轴标注，见 `06` §4.3。

---

## 六、待实现清单

```
[ ] import_scene.gd        — 读 SceneLayout 搭场景
[ ] npc_controller.gd      — NPC 状态机（04 §2）
[ ] dialogue_runtime.gd    — 对话系统（05，读 dlg_id）
[ ] enemy_ai.gd            — 行为树（07 §2/3/4）
[ ] combat.gd              — 剑技/切换/顿帧（07 §5/6，衔接上游）
[ ] petal_particles.gd     — 樱吹雪（06 §5.3、08 §6）
[ ] openxr_config.tres     — OpenXR + 渲染配置
```
