
手势识别组件蓝图接口（GestureHandler）:
- Event OnGestureDetected(GestureType Type)
  Switch on Type:
    Case "TwoFingerSwipeDown": ToggleMainMenu()
    Case "Pinch": 如果菜单打开，则执行 PinchDrag 或 PinchConfirm
    Case "HandPalmSwipeIn": NavigateBack()

环形菜单蓝图结构（WBP_MainRingMenu）:
- 使用 Radial Border 放置6个 Button（对应6个方向）。
- 每个 Button 的 OnClicked 事件切换到对应子面板（WBP_Status, WBP_Inventory...）。
- 缩放地图：使用 MapWidget 绑定两个 Pinch 点的距离，驱动 Camera Ortho Width。