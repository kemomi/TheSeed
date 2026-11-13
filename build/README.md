# 构建链路说明（build/）

> 本目录承载 **L2 集成/打包层**（见 `09_Build_Release_Alpha.md` §2）。
> 当前状态：**脚本占位 + 接口契约**。引擎与 Android 工具链就绪后，按本文填充 `godot/` 或 `ue/` 并一条命令导出 APK。

---

## 一、两层交付边界

| 层 | 内容 | 依赖 | 状态 |
|----|------|------|------|
| L1 设计+资产（离线） | 文档、CSV、SceneLayout、43 GLB、tools/ | Python 3.12（已装） | ✅ 已完成并通过校验 |
| L2 集成+打包（需运行时） | 引擎导入、场景搭建、逻辑、OpenXR、APK | Godot/UE + JDK17 + Android SDK35 | ⚠️ 待工具链 |

**L1 已 100% 交付且引擎无关**：无论最终选 Godot 还是 UE，`assets/` 的 glTF 与 `SceneLayout_SakuraTeien.json` 都不作废（ID 间接层，见 `03` §6）。

---

## 二、工具链就绪检查清单

装齐下列项后，L2 才能推进。逐项勾选：

```
[ ] 引擎二选一：
    [ ] Godot 4.7.x stable（推荐，<100MB，OpenXR 已 production-ready）
    [ ] Unreal Engine 5.x（100GB+，画质上限高，单人 α 偏重）
[ ] JDK 17
[ ] Android SDK：Platform 35 + Build-Tools 35.0.1 + Platform-Tools ≥35
[ ] Android NDK r28b（Godot 路线需要）
[ ] Meta 开发者账号 + Quest 3 开发者模式（侧载 APK 用）
[ ] （Godot）编辑器设置启用 Gradle Build + 安装 Android Build Template
[ ] （Godot）OpenXR Vendors 插件 v4+（Meta Passthrough 等扩展，α 可选）
```

> 版本号为公开资料调研值（见 `08` §11、`09` §4.1）。⚠️ 安装前以引擎官方文档复核具体小版本。

---

## 三、构建命令

### L1（现在就能跑，离线确定性）

```bash
python tools/gen_assets.py --outdir assets     # 生成 43 GLB + 2 纹理 + MANIFEST
python tools/gen_scene_layout.py               # 生成 SceneLayout JSON（159 实例）
python tools/validate_assets.py                # 交叉校验，任一 FAIL 则 exit 1
```

### L2（工具链就绪后）

**Godot 路线：**
```bash
# 1. 用 godot/import_scene.gd 读 SceneLayout + assets/models/*.glb 搭场景（待实现）
# 2. 配置 OpenXR（Mobile 渲染，禁用 Forward+，见 08 §7）
# 3. 导出
godot --headless --export-release "Android Quest" build/TheSeed-SakuraTeien.apk
```

**UE 路线：**
```bash
# 1. 导入 GLB + 按 SceneLayout 摆放（待实现）
# 2. 配置 Quest 3（Android SDK/NDK、MetaXR、Mobile 渲染）
# 3. 打包
UnrealBuildTool TheSeed Android Development -project=TheSeed.uproject
```

---

## 四、子目录

| 目录 | 内容 | 状态 |
|------|------|------|
| `godot/` | Godot 场景导入脚本 + OpenXR 配置契约 | 占位（`IMPORT_CONTRACT.md`） |
| `ue/` | UE 场景导入脚本 + Quest 配置契约 | 占位（`IMPORT_CONTRACT.md`） |

引擎适配脚本需引擎运行时才能编写与测试。α 阶段提供**接口契约**：
- 输入格式：`03` §4 的 SceneLayout JSON schema + §4.2 坐标转换表
- 资产路径：`assets/models/<file>.glb`（文件名见 `03` §2 与 `assets/MANIFEST.sha256`）
- 装配规则：NPC variant → 网格/材质/配件（`04` §1.1）；skinned 动画集（`06` §2）

---

## 五、阻塞与解除

| 阻塞 | 解除路径 |
|------|----------|
| 命令行无法联网 | 用户配置代理，或手动下载工具链放入本机 |
| 引擎未选型 | 用户定引擎（Godot 推荐，见 `03`/`08`） |
| JDK/SDK 未装 | 按 §2 清单安装 |
| Quest 3 未连 | 连接头显 + 开发者模式，侧载 APK |

解除任一阻塞后，L2 可立即推进——契约与脚本框架已备好，不需重新设计。
