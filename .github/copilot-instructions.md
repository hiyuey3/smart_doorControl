# 智慧校园门禁系统 - 开发规范
所有的改动必须只写到README.md和这个文件里，不许生成其他md文件
## UI/UX 设计规范

> 规范冲突处理：若本文前后章节存在冲突，以“核心设计原则与实施指南”章节为最高优先级。

### 设计系统 - 小米米家工业极简风格

#### 色彩方案
- **主色调（Primary）**：`#1989FA` (品牌蓝) / `#007AFF` (iOS 蓝)
- **成功色（Success）**：`#07C160` (微信绿)
- **警告色（Warning）**：`#FF9500` (橙色)
- **错误色（Error）**：`#EE0A24` (红色)
- **背景色（Background）**：`#F7F8FA` (极浅灰)
- **文字颜色**：
  - 主要文字：`#0F172A` / `#1E293B`
  - 次要文字：`#334155` / `#64748B`
  - 辅助文字：`#94A3B8`
- **边框颜色（Border）**：`#E2E8F0`

#### 圆角规范
- **卡片/容器**：`28rpx` ~ `32rpx`
- **按钮**：胶囊 `100rpx` / 常规 `16rpx`
- **输入框**：`16rpx`
- **标签/徽章**：`100rpx`（药丸形）

#### 阴影规范
- **轻量阴影**：`0 4rpx 12rpx rgba(0, 0, 0, 0.03)`
- **卡片阴影**：`0 4rpx 12rpx rgba(0, 0, 0, 0.03)`
- **按钮阴影**：`0 2rpx 8rpx rgba(25, 137, 250, 0.15)`
- **禁止使用**：过重的阴影（超过 16rpx blur）

#### 间距规范
- **基础单位**：`8rpx` 的倍数
- **内边距（Padding）**：`24rpx`, `32rpx`, `48rpx`
- **外边距（Margin）**：`16rpx`, `24rpx`, `32rpx`
- **元素间距（Gap）**：`12rpx`, `16rpx`, `24rpx`

#### 字体规范
- **页面标题**：`56rpx` ~ `60rpx`, font-weight: `700`
- **区块标题**：`36rpx` ~ `40rpx`, font-weight: `600`
- **正文内容**：`28rpx` ~ `32rpx`, font-weight: `400`
- **辅助说明**：`24rpx` ~ `26rpx`, font-weight: `400`

### 按钮层级规范

#### 主按钮（Primary Button）
- **用途**：主要操作（登录、提交、确认）
- **样式**：纯色背景 `#1989FA`，白色文字，极轻阴影或无阴影
- **高度**：`96rpx` ~ `108rpx`
- **禁止**：渐变背景、过重阴影

#### 次要按钮（Secondary Button）
- **用途**：次要操作（取消、返回、辅助功能）
- **样式**：镂空设计，白色背景，彩色边框和文字，无阴影
- **高度**：`88rpx` ~ `96rpx`

#### 文字按钮（Text Button）
- **用途**：最轻量操作（查看详情、了解更多）
- **样式**：无背景，仅文字，颜色 `#1989FA`

### 图标规范

#### **禁止使用 Emoji 图标**
- **原因**：Emoji 在不同设备/系统上显示不一致，缺乏专业感
- **替代方案**：
  1. **纯文字**：如"显示"/"隐藏"、"绑定"/"解绑"
  2. **CSS 伪元素**：使用 `::before` / `::after` 绘制简单图标（圆点、箭头）
  3. **图标字体**：使用 iconfont 或 WeChat 内置图标
  4. **SVG 图标**：小程序支持的 SVG 路径

#### CSS 图标示例
```css
/* 圆点图标 */
.icon-dot::before {
  content: '';
  width: 6rpx;
  height: 6rpx;
  border-radius: 50%;
  background: #cccccc;
  display: inline-block;
  margin-right: 12rpx;
}

/* 箭头图标 */
.icon-arrow::after {
  content: '';
  width: 12rpx;
  height: 12rpx;
  border-top: 2rpx solid #999;
  border-right: 2rpx solid #999;
  transform: rotate(45deg);
  display: inline-block;
}
```

### 交互规范

#### 动画时长
- **快速响应**：`200ms` ~ `250ms` (按钮点击、输入框聚焦)
- **标准过渡**：`300ms` ~ `350ms` (页面切换、列表展开)
- **慢速动画**：`400ms` ~ `500ms` (模态框弹出)

#### Hover / Active 状态
- **按钮点击**：`opacity: 0.85`, `transform: translateY(1rpx)`
- **卡片悬停**：轻微提升阴影
- **输入框聚焦**：边框高亮 `#007AFF`，外发光 `0 0 0 4rpx rgba(0, 122, 255, 0.08)`

### 表单规范

#### 输入框
- **高度**：`96rpx` ~ `108rpx`
- **默认背景**：`#F8F9FA`
- **默认边框**：`2rpx solid #E2E8F0`
- **聚焦状态**：背景 `#ffffff`，边框 `#1989FA`，外发光
- **圆角**：`16rpx`

#### 标签（Label）
- **位置**：输入框上方，间距 `16rpx`
- **字号**：`28rpx`
- **颜色**：`#334155`
- **字重**：`500`

#### 提示文字
- **位置**：表单下方或右侧
- **字号**：`24rpx`
- **颜色**：`#64748B` (说明) / `#EE0A24` (错误)

---

## 🎨 核心设计原则与实施指南

### 设计哲学：信息降噪与状态驱动

作为资深移动端 UI/UX 设计师，在修改或生成小程序页面时，必须严格遵循以下视觉规范，确保整体风格呈现"工业级严谨"且"极简清爽"的质感。

### 1. 全局色彩与布局规范

#### 页面背景 (Background)
- **统一底色**：`#f7f8fa` (极浅灰)
- **严禁**：纯白底色 `#ffffff`（纯白仅用于卡片容器）

#### 容器规范 (Container)
- **卡片化设计**：所有功能模块必须包裹在纯白 `#ffffff` 的独立圆角卡片中
- **层次分明**：通过卡片与背景的对比形成视觉层次

#### 圆角规范 (Border Radius)
- **卡片圆角**：`28rpx` ~ `32rpx`（大圆角，柔和现代）
- **按钮圆角**：
  - 胶囊型按钮：`100rpx`（完全圆角）
  - 常规按钮：`16rpx`
- **输入框圆角**：`16rpx`

#### 阴影规范 (Shadow)
- **严禁**：深重、大范围的阴影
- **允许**：透明度 `3%` ~ `5%` 的极微弱扩散投影
- **标准阴影**：`box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.03)`
- **最大阴影**：`box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.05)`

### 2. 文字层级与引导规范

#### 视觉重心
- **主标题/姓名**：
  - 字号：`36rpx` ~ `40rpx`
  - 字重：`bold` / `700`
  - 颜色：`#1a1a1a`（深黑）
  - 用途：用户姓名、页面主标题、重要信息

#### 辅助信息
- **次要信息**（学号、ID、提示文字）：
  - 字号：`24rpx` ~ `28rpx`
  - 字重：`400` / `500`
  - 颜色：`#888888` / `#999999`（中灰/浅灰）
  - 用途：补充说明、标识符、时间戳

#### 列表引导元素
- **左侧引导**：必须包含视觉引导元素
  - 蓝色小圆点（直径 `6rpx` ~ `8rpx`，颜色 `#1989fa`）
  - 或简洁的语义化图标
- **右侧箭头**：必须包含暗示点击的灰色箭头图标 `›`
  - 颜色：`#cccccc` / `#d0d0d0`
  - 字号：`32rpx` ~ `36rpx`

### 3. 交互组件规范

#### 按钮权重分级

**主按钮 (Primary Button)**
- **样式**：
  - 背景色：品牌蓝 `#1989fa` 或 `#007aff`
  - 文字颜色：纯白 `#ffffff`
  - 阴影：无阴影或极淡发光阴影 `0 2rpx 8rpx rgba(25, 137, 250, 0.15)`
- **用途**：登录、提交、确认等主要操作
- **优先级**：最高

**次要按钮 (Secondary Button)**
- **样式**：
  - 背景：透明或纯白 `#ffffff`
  - 边框：`2rpx solid #1989fa` 或 `2rpx solid #07c160`
  - 文字颜色：与边框同色
  - 阴影：无
- **用途**：取消、返回、辅助功能
- **优先级**：中等

**危险按钮 (Danger Button)**
- **样式**：
  - 背景色：`#ee0a24` 或 `#ff4444`
  - 文字颜色：纯白 `#ffffff`
  - 阴影：无或极淡红色阴影
- **用途**：仅限退出登录、删除、解绑等危险操作
- **位置**：应靠后放置（页面底部或操作列表末尾）
- **原则**：避免误触，必须明确提示

#### 状态标签 (Status Tags)

采用**"药丸"造型**（胶囊形状）：

**在线/已绑定状态**
- **背景色**：浅绿 `#e8f5e9`
- **文字颜色**：深绿 `#07c160`
- **字号**：`24rpx`
- **内边距**：`6rpx 16rpx`
- **圆角**：`100rpx`

**离线/待审批状态**
- **背景色**：浅灰 `#f5f5f5`
- **文字颜色**：深灰 `#999999`
- **字号**：`24rpx`
- **内边距**：`6rpx 16rpx`
- **圆角**：`100rpx`

**警告/异常状态**
- **背景色**：浅橙 `#fff7e6`
- **文字颜色**：深橙 `#ff9500`
- **字号**：`24rpx`
- **内边距**：`6rpx 16rpx`
- **圆角**：`100rpx`

**拒绝/错误状态**
- **背景色**：浅红 `#ffebee`
- **文字颜色**：深红 `#ee0a24`
- **字号**：`24rpx`
- **内边距**：`6rpx 16rpx`
- **圆角**：`100rpx`

#### 输入框规范 (Input Fields)

**基础样式**
- **背景色**：浅灰 `#f8f9fa`
- **边框**：默认透明或极浅灰 `#e2e8f0`
- **内边距**：宽绰舒适 `24rpx` ~ `32rpx`
- **圆角**：`12rpx` ~ `16rpx`

**交互增强**
- **清除按钮**：输入内容后显示右侧清除图标
- **密码切换**：提供"显示"/"隐藏"文字按钮（颜色 `#007aff`）
- **聚焦状态**：边框高亮为品牌蓝 `#007aff`，背景变为纯白

### 4. 列表与卡片规范

#### 列表项样式
- **背景**：纯白 `#ffffff`
- **内边距**：`30rpx` ~ `40rpx`
- **分隔线**：`1rpx solid #f0f0f0`（仅在必要时使用）
- **最小高度**：`96rpx`（确保点击区域舒适）

#### 卡片间距
- **卡片外边距**：`24rpx` ~ `32rpx`
- **卡片内边距**：`32rpx` ~ `40rpx`
- **元素间距**：`16rpx` ~ `24rpx`

### 5. 空间留白与呼吸感

#### 页面边距
- **页面 Padding**：至少 `30rpx`，推荐 `40rpx`
- **禁止**：内容紧贴屏幕边缘

#### 栅格系统
- **基础单位**：`8rpx`
- **所有间距**：必须是 `8rpx` 的倍数
- **常用值**：`16rpx`, `24rpx`, `32rpx`, `40rpx`, `48rpx`

---

## 🚀 AI 修改话术模板

当需要修改特定页面时，请使用以下标准化话术：

### 通用重构指令模板

```
请按照『智慧校园极简风 UI 规范』帮我修改 [XX 页面]：

1. 卡片化重构
   - 将页面内容块全部改为带有 28rpx 圆角和微阴影的白色卡片
   - 页面背景使用 #f7f8fa

2. 视觉权重调整
   - 主操作按钮：品牌蓝 #1989fa 实色，96rpx 高度，无阴影
   - 次要操作：镂空边框设计，白底蓝字或绿字
   - 危险操作：移到底部，红色 #ee0a24

3. 列表优化
   - 每个列表行增加左侧蓝色圆点引导（6rpx，#1989fa）
   - 右侧添加灰色点击箭头（›，#cccccc）
   - 最小点击区域 96rpx

4. 状态映射
   - 所有状态显示改为"药丸"标签
   - 在线/绑定：浅绿底深绿字（#e8f5e9 / #07c160）
   - 离线/待审：浅灰底深灰字（#f5f5f5 / #999999）

5. 空间留白
   - 页面 Padding 增加到 40rpx
   - 卡片内边距 32rpx ~ 40rpx
   - 元素间距至少 16rpx
```

### 特定场景指令

**修改表单页面**
```
优化 [XX 表单页面]：
- 输入框背景改为 #f8f9fa
- 添加密码可见性切换（纯文字"显示"/"隐藏"）
- 主按钮改为品牌蓝 #007aff，96rpx 高度
- 增加表单提示文字（灰色 #64748B，24rpx）
```

**修改列表页面**
```
优化 [XX 列表页面]：
- 每个列表项改为独立白色卡片，28rpx 圆角
- 左侧添加蓝色圆点（6rpx，#1989fa）
- 右侧添加箭头图标（›，#cccccc）
- 状态标签改为药丸形状
- 卡片间距 24rpx
```

**修改详情页面**
```
优化 [XX 详情页面]：
- 顶部添加用户信息卡片（头像 + 姓名 + 学号）
- 主标题 40rpx bold #1a1a1a
- 次要信息 28rpx regular #888888
- 操作按钮区域：主按钮在上，危险按钮在底部
```

---

## 代码规范

### 微信小程序规范

#### 文件命名
- **页面**：全小写，下划线分隔（`device_detail`, `user_manage`）
- **组件**：驼峰命名（`deviceCard`, `logItem`）

#### WXML 规范
- **缩进**：2 空格
- **属性换行**：超过 3 个属性时换行
- **注释**：关键区块添加注释，使用 `<!-- 描述 -->`

#### WXSS 规范
- **单位**：使用 `rpx`（响应式像素）
- **顺序**：按功能分组（布局 → 尺寸 → 外观 → 文字 → 其他）
- **命名**：BEM 风格（`.block__element--modifier`）

#### JS 规范
- **缩进**：2 空格
- **分号**：必须使用
- **注释**：函数上方添加 JSDoc 风格注释
- **命名**：
  - 变量/函数：驼峰命名（`getUserInfo`）
  - 常量：全大写下划线（`API_BASE_URL`）
  - 私有方法：下划线前缀（`_handleError`）

### 后端规范

#### Python 代码规范
- **风格**：遵循 PEP 8
- **缩进**：4 空格
- **命名**：
  - 函数/变量：蛇形命名（`get_user_info`）
  - 类名：大驼峰命名（`UserModel`）
  - 常量：全大写下划线（`MAX_RETRY_COUNT`）

#### API 规范
- **响应格式**：
```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```
- **状态码**：
  - `200`：成功
  - `400`：请求错误
  - `401`：未授权
  - `403`：权限不足
  - `404`：资源不存在
  - `500`：服务器错误

## Git 规范

### Commit Message 格式
```
<type>(<scope>): <subject>

<body>
```

#### Type 类型
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链相关

#### 示例
```
feat(login): 重构登录页面 UI 为极简风格

- 移除渐变背景，改用纯色
- 优化按钮层级（主按钮蓝色，次要按钮镂空）
- 新增密码可见性切换功能
- 添加页脚帮助文字
```

## 项目特定规范

### 权限隔离
- **原则**：用户只能访问自己有权限的设备
- **实现**：所有设备查询必须关联 `UserDevicePermission` 表
- **检查点**：控制台、日志查询、设备操作

### 日志记录
- **分类**：通行日志（AccessLog）、申请日志（ApplicationLog）
- **必记字段**：`user_id`, `device_id`, `action`, `timestamp`
- **展示**：统一为"最近动作"，区分日志类型

### 微信登录
- **流程**：`wx.login()` → 后端 `code2session` → 返回 token
- **绑定**：首次登录需绑定学号/工号
- **解绑**：个人设置页面支持一键解绑

## 后端高级规范

### V3.0 后端工具类架构（重构规范）

#### 设计理念
- **降低重复**：提取通用的数据库、权限、响应、日志操作到工具类
- **统一标准**：确保所有API响应格式、错误处理、权限检查一致
- **易于维护**：修改逻辑时只需更新工具类，不影响所有路由

#### 核心工具类

**1. DatabaseHelper** (`utils/db_helper.py`)
- 统一数据库CRUD操作，避免直接调用ORM
- 所有方法都返回 `(result, error)` 元组，便于统一错误处理
- 支持事务装饰器 `@with_transaction`

常用方法：
```python
db_helper.get_by_filter(Model, **filters)  # 单条查询
db_helper.get_by_id(Model, id)             # 主键查询
db_helper.add_and_commit(instance)         # 新增并提交
db_helper.update_and_commit(instance, **updates)  # 更新并提交
db_helper.delete_and_commit(instance)      # 删除并提交
```

**2. PermissionHelper** (`utils/permission_helper.py`)
- 统一权限检查逻辑，包括admin校验和设备权限验证
- 实现BOLA防护（Broken Object Level Authorization）

常用方法：
```python
permission_helper.require_admin(user)           # admin权限检查
permission_helper.check_device_access(user, mac)  # 设备访问权限检查
permission_helper.has_device_permission(user_id, device_mac)  # 权限查询
```

**3. ResponseHelper** (`utils/response_helper.py`)
- 统一API响应格式，所有响应都通过此类生成
- 确保前端能一致处理所有API返回

常用方法：
```python
response_helper.success(data, message)  # 成功响应
response_helper.error(message, error_code, status_code)  # 错误响应
response_helper.bad_request/unauthorized/forbidden/not_found(...)  # 快捷方法
response_helper.list_response(items, count)  # 列表响应
response_helper.paginated(items, page, per_page, total)  # 分页响应
```

**4. LogHelper** (`utils/log_helper.py`)
- 统一日志记录流程，支持多种日志类型
- 自动生成唯一事件ID和时间戳

常用方法：
```python
log_helper.create_access_log(mac_address, user_id, unlock_method)
log_helper.create_remote_unlock_log(mac_address, user_id)  # 远程开锁
log_helper.create_fingerprint_log(mac_address, user_id, success)  # 指纹
log_helper.get_logs_by_user/device(user_id/mac_address)
```

#### 重构原则

1. **替换直接ORM调用**
   ```python
   # 旧：Device.query.filter_by(mac_address=mac).first()
   # 新：device, error = db_helper.get_by_filter(Device, mac_address=mac)
   ```

2. **统一错误返回**
   ```python
   # 旧：jsonify({'success': False, 'message': '...'}), 400
   # 新：response_helper.bad_request('...')
   ```

3. **简化权限检查**
   ```python
   # 旧：if current_user.role != 'admin': return jsonify(...)
   # 新：error = permission_helper.require_admin()
   #     if error: return jsonify(error[0]), error[1]
   ```

4. **规范日志记录**
   ```python
   # 旧：大量手动构造Log对象，添加到session
   # 新：log_entry, error = log_helper.create_remote_unlock_log(...)
   ```

#### 渐进式重构指南

- 优先级1：关键路由（login, unlock, user/* 等）
- 优先级2：管理接口（/admin/* 等）
- 优先级3：日志查询接口
- 优先级4：其他辅助接口

每次重构一个路由时：
1. 导入所需工具类
2. 替换数据库查询为 `db_helper` 调用
3. 替换响应返回为 `response_helper` 调用
4. 替换权限检查为 `permission_helper` 调用
5. 替换日志记录为 `log_helper` 调用
6. 运行测试验证功能

#### 响应格式标准

所有API返回格式必须遵循此标准：

**成功响应** (HTTP 200/201)：
```json
{
  "success": true,
  "message": "操作成功",
  "data": { /* 可选的返回数据 */ }
}
```

**错误响应** (HTTP 40x/50x)：
```json
{
  "success": false,
  "message": "错误描述",
  "error_code": "ERROR_CODE",
  "data": null  /* 可选的错误详情 */
}
```

**分页响应**：
```json
{
  "success": true,
  "message": "查询成功",
  "data": [/* 数据列表 */],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

#### 权限检查规范

- **Admin权限**：仅允许admin角色的用户操作
- **设备权限**：需要UserDevicePermission记录（status='approved'）
- **二次验证**：敏感操作需要旧密码或额外确认
- **日志审计**：所有操作必须记录到Log表

---

**最后更新**：2026年3月2日
**重构状态**：*[完成]*核心工具类已创建，示例路由已重构
## 更新日志

### 2026年3月5日（上午更新）
- *[完成]***功能优化**：快照加载逻辑改进 - 本地ESP32优先策略
  - **优先级调整**：
    * 优先级1（首选）：本地 ESP32 直连 - 超时3秒快速失败
    * 优先级2（备选）：后端代理 - 超时8秒兜底方案
    * 优先级3（最后）：占位符 - 显示离线提示
  - **核心改进**：
    * 当`device.ip_address`可用时，直接尝试本地源
    * 本地源失败自动降级到后端代理（不用等待超时）
    * 后端代理失败显示离线提示而不是黑屏
  - **优势**：
    * 校园内用户得到快速的本地快照（低延迟）
    * 校园外用户自动在后端代理和本地源间切换
    * 网络异常时显示明确的离线提示
  - **技术实现**：
    * 拆分为 `loadFromLocalESP32()` 和 `loadFromBackendProxy()` 两个函数
    * 实现智能降级策略
    * 保留了 Base64 换行符清理机制

- *[完成]***Bug修复**：修复Log日志记录中的字段错误
  - **问题**：`LogHelper.create_access_log()` 试图赋值 `success`, `failure_reason`, `image_path`，但Log模型不存在这些字段
  - **解决**：
    * 移除无效字段参数
    * 仅使用Log模型实际支持的字段
    * 将 `image_path` 映射到 `snapshot_url` 字段
  - **效果**：开锁接口不再返回"'success' is an invalid keyword argument"错误

### 2026年3月5日（凌晨更新）
- *[完成]***重要修复**：小程序开锁接口兼容性问题
  - **问题描述**：小程序调用开锁接口时，MAC地址带冒号（如 `AC:A7:04:26:0C:FC`）导致URL路由问题
  - **修复内容**：
    * **小程序端**：`pages/console/index.js` 的 `onUnlockDevice` 函数
      - 在构造URL前移除MAC地址中的冒号：`mac.replace(/:/g, '')`
      - 统一使用无冒号格式调用接口：`/devices/ACA704260CFC/unlock`
    * **后端接口**：`backend/api/routes.py` 的 `unlock_device` 函数
      - 添加MAC地址标准化处理：使用 `normalize_mac()` 函数
      - 支持接收带冒号和不带冒号的MAC地址输入
      - 标准化为统一格式后再进行权限检查和设备查询
  - **技术细节**：
    * 小程序统一发送无冒号MAC：`ACA704260CFC`
    * 后端接收后通过 `normalize_mac()` 转换为标准格式：`AC:A7:04:26:0C:FC`
    * 确保与数据库中存储的MAC地址格式一致
  - **解决效果**：
    * 开锁接口不再返回500错误（原因：旧代码错误处理tuple unpacking）
    * MAC地址格式兼容性增强，支持多种输入格式
    * 与快照接口的MAC地址处理逻辑保持一致

### 2026年3月5日（深夜更新）
- *[完成]***重大修复**：解决微信小程序快照渲染黑屏问题
  - **架构变更**：后端快照接口从返回二进制数据改为返回 JSON 格式的 Base64 编码数据
  - **新增工具函数**：`normalize_mac()` 统一全栈 MAC 地址格式（避免 Cache MISS）
    * 支持任意格式输入：`AA:BB:CC:DD:EE:FF`、`AABBCCDDEEFF`、`AA-BB-CC-DD-EE-FF`
    * 统一输出格式：`AA:BB:CC:DD:EE:FF`（全大写带冒号）
    * 完整的错误处理和验证逻辑
  - **后端修改**：
    * 修改 `POST /api/device/upload_snapshot`：使用 `normalize_mac()` 标准化 MAC 地址
    * 修改 `GET /api/device/snapshot/<mac>`：返回格式改为 JSON
      ```json
      {
        "success": true,
        "data": {
          "image_base64": "...",  // 纯净的Base64字符串（无换行符）
          "source": "cache",      // 数据来源
          "frame_age": 1.2        // 快照年龄（秒）
        }
      }
      ```
    * 使用 `base64.b64encode().decode('utf-8')` 确保 Base64 字符串无换行符
    * 所有快照源（云端中继、内存缓存、本地ESP32、占位符）统一返回格式
  - **小程序修改**：
    * 修改 `pages/device-detail/index.js` 的 `loadDeviceSnapshot()` 函数
    * 改为接收 JSON 格式数据（`responseType: 'text'`）
    * 解析 `data.image_base64` 字段
    * **核心修复**：强制执行 `.replace(/[\r\n]/g, "")` 清理所有换行符
    * 双重保险机制：后端去除换行符 + 前端额外清理
  - **问题根因**：
    * 微信小程序的 `<image>` 标签对 Base64 字符串非常严格
    * Base64 字符串中的 `\r` 或 `\n` 会导致图片渲染为灰块或黑屏
    * 原架构使用 `wx.arrayBufferToBase64()` 可能在某些情况下产生带换行符的字符串
  - **兼容性**：
    * 保持本地 ESP32 直连模式的 arraybuffer 方式不变（仅在前端额外清理）
    * 后端代理模式完全切换为 JSON Base64 响应
    * 所有三层快照源（云端中继、内存缓存、本地）统一返回格式

### 2026年3月5日（晚间更新）
- *[完成]***新增功能**：云端中继视频支持
  - 后端支持三层优先级快照获取架构：
    * 优先级1（推荐）：云端中继地址（`CLOUD_RELAY_SNAPSHOT_URL`）
    * 优先级2：内存缓存（ESP32推送快照）
    * 优先级3（备选）：本地ESP32直连（`DEVICE_SNAPSHOT_URL`）
  - 新增 `CLOUD_RELAY_SNAPSHOT_URL` 环境变量支持
  - 新增 `CLIENT_SNAPSHOT_URL_TEMPLATE` 客户端快照URL配置
  - 修改 `proxy_device_snapshot()` 函数实现三层架构逻辑
  - 更新 docker-compose.yml 添加云端中继配置说明
  - 更新 config.example.py 添加详细配置文档
  - 在 README.md 添加完整的云端中继视频使用指南
  - 支持 CDN 加速、内网穿透、Docker 网络等多种部署方式
  - 自动故障转移：中继不可用时自动降级到缓存和本地方案
  - 性能提升：云端快照不走后端代理，响应延迟低于 100ms

### 2026年3月5日（早间更新）
- *[完成]***新增功能**：网页管理后台增加权限审批模块
  - 新增 `/admin/permissions` 路由和页面
  - 支持待审批、已批准、已拒绝状态筛选
  - 实现批准和拒绝操作
  - 在 UserDevicePermission 模型中添加 relationship 关系
  - 侧边栏导航菜单增加"权限审批"入口
  - 保持现有管理后台设计风格
- *[完成]***修复问题**：Nginx 反向代理重定向到 127.0.0.1
  - 添加 ProxyFix 中间件支持反向代理
  - 配置信任 X-Forwarded-* 请求头
- *[完成]***架构优化**：统一 admin 路由为 RESTful 风格
  - 用户删除路由改为 `POST /admin/users/<id>`（HTML表单限制）
  - 权限审批合并为 `POST /admin/permissions/<id>` + action参数
  - 用户添加路由优化为 `POST /admin/users`
  - 所有数据库操作增加异常处理和回滚机制
  - 模板表单改为POST提交，避免GET方法误触
  - 新增错误提示显示功能（页面顶部alert）
  - 验证硬件代码兼容性（ESP32仅调用/api接口，不受影响）
- *[完成]***功能增强**：权限管理功能优化 - 支持添加和修改权限
  - 新增添加权限功能：管理员可主动为用户分配设备访问权限
  - 新增撤销权限功能：允许管理员撤销已批准的用户设备权限
  - 优化权限审批页面：添加用户/设备选择下拉框的模态框
  - 统一权限管理流程：pending（审批）、approved（批准）、revoke（撤销）三种操作
  - 权限页面传递users和devices列表用于模态框选择
  - 已批准权限现在支持撤销操作（点击撤销按钮删除权限）
- *[完成]***界面统一**：统一所有管理界面的CRUD功能
  - 设备管理：添加设备添加、编辑、删除功能
  - 用户管理：增加编辑用户功能（原有删除功能保留）
  - 所有页面添加错误提示显示（页面顶部alert）
  - 统一使用模态框处理添加和编辑操作
  - 所有操作都支持异常处理和数据库回滚
  - 保持uniform UI/UX风格和RESTful路由设计

### 2026年3月2日（历史记录）
- *[完成]*核心工具类已创建，示例路由已重构
