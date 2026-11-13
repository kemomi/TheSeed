# Unreal Engine 场景导入契约（占位）

> 状态：**接口契约**。UE 5.x 与 Android 工具链就绪后，按本契约实现导入。
> 引擎无关输入：`SceneLayout_SakuraTeien.json` + `assets/models/*.glb` + `DataTables/*.csv`。
> 说明：上游 `kemomi/` 设计包以 UE 5.3+ 为名义目标（`00` §1）。本包为**引擎无关**交付，UE 为可选路线之一。

---

## 一、坐标转换（权威）

SceneLayout 用右手系 **+X东 +Y北 +Z上**，单位米；UE 用左手系 **+X前 +Y右 +Z上**，单位厘米（1m=100uu）。

```
ue_pos = (json_x * 100, json_y * 100, json_z * 100)   # 米 -> uu，UE 左手系 +X前 +Y右
```

旋转：JSON `rotation_deg[0]` 为绕 +Z（上）轴，UE 的 Yaw 同为绕 +Z，但左右手系差异使正方向相反：
```
ue_yaw = -json_rotation_deg[0]
```

依据见 `03` §4.2。导入脚本**必须**用此转换。

---

## 二、导入流程

```
1. 启用 glTF Importer 插件，导入 assets/models/*.glb 为 StaticMesh/SkeletalMesh
2. 读 SceneLayout_SakuraTeien.json（用 DataTable/JSON 插件或自定义 C++）
3. 用 Level Blueprint 或 Editor Utility Widget 按 instance 摆放 Actor
4. collision 字段 -> PrimitiveComponent 碰撞预设（box/cylinder/none）
5. npc_placement -> 按 variant 装配 SkeletalMesh + 配件（挂 Hand socket）
6. spawner -> 敌人 AIController + BehaviorTree（07）
7. light -> DirectionalLight/SkyLight/PointLight
8. petal_emitter -> Niagara 粒子系统（06 §5.3、08 §6）
9. volume -> Volume Actor（safe_zone/combat_domain/fog）
```

---

## 三、NPC variant 装配（04 §1.1）

同 Godot 契约 §三的 variant 表。UE 侧配件挂点用 **Socket**：在 Skeleton 的 `Hand_R`/`Hand_L` 骨骼上建 Socket，配件 SkeletalMesh/StaticMesh attach 到 Socket。

材质色替换：用 Material Instance Dynamic 改 baseColor（单图集策略在 UE 侧需确认调色板纹理采样，或改用 Material Parameter）。⚠️ UE 的 glTF 导入对单图集 UV 支持良好，但顶点色需在材质中显式启用（Vertex Color 节点）。

---

## 四、Quest 3 / 渲染配置（08 §7）

```
渲染路径：Mobile（Forward Shading，Quest 3 强制）
VR 插件：OpenXR（UE 内置）+ MetaXR 插件（Meta 特有扩展）
MSAA：4x
固定注视点渲染 FFR：中档（MetaXR 提供）
阴影：主光 2048，级联 2
实时 GI（Lumen）：禁用（Quest 3 不支持，用烘焙光照）
SSR：禁用
体积雾：禁用（用 fog_plane 面片）
后期：最小化
Android 配置：SDK Platform 32+、Build-Tools 34+、target Android 14(API34)
```

> ⚠️ UE 做 Quest 3 推荐用 **Oculus/Meta Fork of UE**（内置 MetaXR，修复更多 Quest 问题），见 `09` §4.1 调研来源。

---

## 五、动画集映射（06 §2）

GLB 内置动画导入为 AnimSequence，按 `06` §2 的 anim_set 组织 AnimBlueprint：

| anim_set | AnimSequence | 循环 |
|----------|-------------|------|
| npc_base | A_NPC_Idle/Wave/Talk/Bow/Walk/Sit | idle/talk/walk/sit Loop；wave/bow 单次 |
| sakura_oni | A_Oni_Idle/Walk/Attack/Hit/Die | idle/walk Loop；其余单次 |
| hikabusho | A_Busho_Idle/Walk/Guard/Attack/Hit/Die | idle/walk/guard Loop；其余单次 |

动画事件（打击帧/顿帧）用 AnimNotify，按 `06` §4.3 时间轴标注。
行为树用上游 `BT_` 命名（`07` §2/3/4）。

---

## 六、数据表导入

`DataTables/*.csv` 直接导入为 UE DataTable（`DT_` 前缀，`00` §3.1）。表头逐字对应 UE Struct 属性名。导入路径建议（沿用上游 README）：
- `DT_NPC_SakuraTeien` -> `Content/GameData/NPC/`
- `DT_Enemy_SakuraTeien` -> `Content/GameData/Enemies/`
- `DT_EnemyAttacks_SakuraTeien` -> `Content/GameData/Enemies/`

---

## 七、待实现清单

```
[ ] 导入 Editor Utility（C++/蓝图）— 读 SceneLayout 摆放 Actor
[ ] NPC AnimBlueprint + 状态机（04 §2）
[ ] 对话运行时（05，读 dlg_id）
[ ] 敌人 BehaviorTree（07，BT_SakuraOni_Grunt/Blade、BT_Hikabusho）
[ ] 战斗系统（剑技/切换/顿帧，衔接上游 SwordSkillSystem/SwitchingSystem）
[ ] Niagara 樱吹雪（06 §5.3、08 §6）
[ ] Quest 3 打包配置（Android SDK/NDK、MetaXR）
```
