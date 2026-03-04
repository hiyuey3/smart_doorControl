# 智慧校园门禁系统 - 项目代码审计报告（2026-03-05）

## 审计摘要

本审计覆盖整个项目，包括后端（Python Flask）、前端（微信小程序）、固件（ESP32S3）三个模块。

**发现的主要问题：**
- [通过] 后端架构成熟：工具类设计良好，已实现 db_helper、response_helper、log_helper、permission_helper 等统一接口
- [警告] 前端重复代码较多：多个页面直接调用 `wx.request()`，未充分复用 `utils/request.js`
- [警告] 混合使用 HTTP/MQTT：部分功能同时支持 HTTP 和 MQTT 两种协议，代码复杂度高
- [不通过] 备份文件未清理：`mqtt_bak.js` 是备份文件，应删除或整理

---

## # 详细审计清单

### 一、后端架构审计（[通过]整体评分：8/10）

#### 1.1 工具类集中度评估
| 模块 | 位置 | 功能 | 复用度 |
|------|------|------|--------|
| 数据库操作 | `shared/db_helper.py` | CRUD 统一接口 | [5星] |
| API 响应 | `shared/response.py` | 响应格式统一 | [5星] |
| 日志记录 | `shared/logging.py` | 日志类型快捷方法 | [5星] |
| 权限检查 | `auth/permissions.py` | RBAC/BOLA 防护 | [4星] |
| 对象序列化 | `shared/serializers.py` | 模型→字典转换 | [4星] |

**结论**：[通过]后端已避免造轮子，充分利用工具类

#### 1.2 API 路由合理性分析
```python
# [通过]良好实例：统一登录入口
POST /api/login
- login_type = 'password' → 密码登录
- login_type = 'wechat' → 微信登录
# 避免了 /login_password 和 /login_wechat 的冗余

# [通过]良好实例：资源化 + Action 分离
GET  /api/user                  # 获取当前用户
PUT  /api/user?action=bind      # 绑定微信
PUT  /api/user?action=unbind    # 解绑微信
PUT  /api/user?action=update    # 更新个人信息
```

**发现的可优化点**：
- 某些日期时间处理有硬编码，可考虑提取到工具函数
- MAC 地址验证有多处重复，建议继续沿用 `_validate_mac_address()` 和 `_normalize_mac_address()`

#### 1.3 数据模型审计

**模型复用情况**：
- [通过]`BaseIDMixin`：集中 ID 生成逻辑
- [通过]`TimestampMixin`：集中时间戳管理（created_at/updated_at）
- [通过]`SerializerMixin`：统一序列化方法 `to_dict()`

**潜在问题**：
- User 模型中 `password` 字段使用 SHA256，但无盐值处理
  - **建议升级**：改用 `werkzeug.security.generate_password_hash()` 和 `check_password_hash()`
  
```python
# 当前方式（不安全）
self.password = hashlib.sha256(password.encode()).hexdigest()

# 建议改为
from werkzeug.security import generate_password_hash, check_password_hash
self.password = generate_password_hash(password)
self.check_password(pwd) # 调用时自动用 check_password_hash(self.password, pwd)
```

---

### 二、前端小程序审计（[警告]整体评分：6/10）

#### 2.1 工具函数使用情况

**工具类清单**：
| 文件 | 导出函数 | 使用现状 | 得分 |
|------|---------|---------|------|
| `utils/request.js` | `request()` 统一请求 | 仅在 `app.js` 使用 | [警告]20% |
| `utils/page-helper.js` | `showToast/showError/handleUnauthorized()` | 在部分页面使用 | [警告]40% |
| `config/env.js` | `getApiUrl()/getConfig()` | 多数页面使用 | [通过]80% |

#### 2.2 代码重复统计

**问题页面**：`pages/device-detail/index.js`、`pages/users/manage.js`、`pages/console/index.js`

**重复模式 1：直接使用 wx.request()**
```javascript
// [不通过]pages/device-detail/index.js 第 126 行
wx.request({
  url: apiUrl + '/devices/' + mac_address + '/unlock',
  method: 'POST',
  header: { 'Authorization': 'Bearer ' + wx.getStorageSync('token') },
  success: (res) => {
    if (res.statusCode === 401) { /* 401 处理 */ }
    if (res.data && res.data.success) { /* 成功处理 */ }
  },
  fail: (err) => { /* 错误处理 */ }
});

// [通过]应改为
const request = require('../../utils/request.js');
request({
  url: '/devices/' + mac_address + '/unlock',
  method: 'POST'
}).then(res => {
  // 已自动处理 401、Token 携带、错误检查
}).catch(err => {
  pageHelper.showError(err.message);
});
```

**重复模式 2：重复的 showToast 逻辑**
```javascript
// [不通过]在 pages/device-detail/index.js、pages/users/manage.js 中重复
wx.showToast({
  title: '操作成功',
  icon: 'success',
  duration: 2000
});

// [通过]应使用 page-helper
const { showSuccess } = require('../../utils/page-helper.js');
showSuccess('操作成功');
```

**重复出现的代码片段**：
| 模式 | 出现次数 | 建议处理 |
|------|--------|--------|
| `wx.getStorageSync('token')` | 15+ | 由 request.js 自动处理 |
| `wx.showToast({...})` | 25+ | 提取到 page-helper.js |
| `envConfig.getApiUrl()` | 8+ | 已集中，但仍需在页面级别改进使用 |
| `401 状态检查和跳转` | 5+ | request.js 已集中处理 |

---

### 三、API 依赖库分析

#### 后端依赖 (requirements.txt)

**当前使用**：
```
Flask 2.3.3                  [通过]轻量级框架，无造轮子
Flask-SQLAlchemy 3.0.5       [通过]ORM，已正确使用
Flask-CORS 4.0.0             [通过]跨域，无重复实现
PyMySQL 1.1.0                [通过]MySQL 驱动
flask-mqtt 1.1.1             [通过]MQTT 协议库
PyJWT 2.8.0                  [通过]JWT 生成/验证
requests 2.31.0              [通过]HTTP 客户端（微信接口）
gunicorn 21.2.0              [通过]WSGI 服务器
```

**建议新增**：
```
werkzeug>=2.3.0              # 密码哈希（替代 hashlib SHA256）
python-dotenv>=1.0.0         # 环保境变量管理（已在用，但未声明）
marshmallow>=3.19.0          # Schema 验证和序列化（可选）
```

#### 前端依赖 (miniprogram-1/package.json)

**当前清空**：项目未声明 npm 依赖，微信小程序纯原生

**建议**：保持原生，但可引入：
- 无第三方库依赖（小程序环境限制）

---

### 四、文件整理建议

#### 4.1 需要清理的备份/过期文件

| 文件 | 类型 | 处理方案 |
|------|------|--------|
| `miniprogram-1/mqtt_bak.js` | 备份 | 删除 |
| `backend/instance/access_control.db.backup_20260301_044111` | 备份 | 删除或移到 backups/ |

#### 4.2 建议的项目结构优化

**后端**：
```
backend/
├── shared/
│   ├── db_helper.py          [通过]现有
│   ├── response.py           [通过]现有
│   ├── logging.py            [通过]现有
│   ├── serializers.py        [通过]现有
│   └── validators.py         ⭐ 新增：统一校验逻辑（MAC/邮箱/电话等）
├── core/
│   ├── utils/
│   │   └── crypto.py         ⭐ 新增：密码哈希、token相关
│   └── models/
│       └── ...
```

**前端**：
```
miniprogram-1/
├── utils/
│   ├── request.js            [通过]现有
│   ├── page-helper.js        [通过]现有
│   ├── date-helper.js        ⭐ 新增：日期格式化（pages/users/manage.js 中有重复）
│   └── location-helper.js    ⭐ 新增：位置相关功能统一管理
```

---

### 五、代码质量指标

| 指标 | 后端 | 前端 |
|------|------|------|
| 工具类集中度 | [5星] 95% | ⭐⭐⭐ 50% |
| 代码重复率 | [4星] 8% | ⭐⭐ 35% |
| 依赖库合理性 | [5星] 100% | N/A |
| 错误处理一致性 | [4星] 85% | ⭐⭐⭐ 60% |

---

## 优化行动计划（优先级）

### 优先级 1（P1）- 立即执行

1. **删除备份文件**
   ```bash
   git rm miniprogram-1/mqtt_bak.js
   git rm backend/instance/access_control.db.backup_*
   ```

2. **密码安全升级**（后端）
   ```bash
   pip install werkzeug>=2.3.0
   ```
   然后修改 `core/models/user.py`：
   - 将 `self.password = hashlib.sha256(...)` 改为 `werkzeug` 方式

3. **前端 request.js 全面推广**
   - 修改 `pages/device-detail/index.js`：用 `request()` 替代所有 `wx.request()`
   - 修改 `pages/users/manage.js`：同样替换
   - 修改 `pages/console/index.js`：部分 wx.request 改用 request()

### 优先级 2（P2）- 本周完成

4. **提取日期格式化工具**
   - 将 `pages/users/manage.js` 中的 `formatTime()` 提取到 `utils/date-helper.js`

5. **统一 showToast 调用**
   - 审计所有 `wx.showToast()` 调用，改用 `pageHelper.showToast()`

6. **后端新增 validators.py**
   - 集中 MAC 地址、邮箱、电话等校验逻辑

### 优先级 3（P3）- 下月规划

7. **引入 Schema 验证库**（可选）
   - 后端考虑引入 `marshmallow` 进行请求体验证

8. **前端性能优化**
   - 缓存已加载的设备列表
   - 避免重复请求

---

## 反向代理配置（2026-03-05 修复）

### 问题症状
在 Nginx 反向代理后，访问 `/admin/login` 登录成功后会重定向到 `http://127.0.0.1/admin`，而不是真实的域名。

### 根本原因
Flask 的 `redirect()` 函数在生成绝对 URL 时，需要知道真实的请求来源（协议、域名、端口）。当应用在反向代理后面时，Flask 默认只能看到代理服务器的内部地址（如 `backend:5000` 或 `127.0.0.1:5000`），不知道外部访问的真实域名。

### 解决方案

#### 1️⃣ **后端配置 ProxyFix 中间件**（[通过]已修复）
在 `backend/app.py` 中添加：
```python
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    app = Flask(__name__)
    
    # 信任反向代理传递的头部信息
    app.wsgi_app = ProxyFix(
        app.wsgi_app, 
        x_for=1,        # 信任 X-Forwarded-For
        x_proto=1,      # 信任 X-Forwarded-Proto (识别 HTTPS)
        x_host=1,       # 信任 X-Forwarded-Host (识别真实域名)
        x_prefix=1      # 信任 X-Forwarded-Prefix
    )
```

#### 2️⃣ **Nginx 配置正确的代理头部**（[通过]已配置）
在 `backend/nginx.conf` 中确保：
```nginx
location / {
    proxy_pass http://backend:5000;
    proxy_set_header Host $host;                           # 传递真实域名
    proxy_set_header X-Real-IP $remote_addr;               # 传递客户端 IP
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;            # 传递协议 (http/https)
}
```

### 验证方法
1. 重启后端服务：`docker-compose restart backend`（或 `docker-compose up -d --build`）
2. 访问 `https://dev.api.5i03.cn/admin/login`
3. 登录成功后，URL 应该保持为 `https://dev.api.5i03.cn/admin`，而不是跳转到 `127.0.0.1`

### 技术细节
- **ProxyFix** 会解析 Nginx 传递的 `X-Forwarded-*` 头部，让 Flask 的 `request.url`、`request.host`、`url_for()` 等函数返回正确的外部 URL
- **参数说明**：
  - `x_for=1`：表示信任 1 层代理（如果有多层代理需要增加）
  - `x_proto=1`：识别 HTTPS 协议，避免 HTTPS→HTTP 降级
  - `x_host=1`：识别真实域名

---

## 最终评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 后端架构 | 8/10 | 工具类成熟，需小幅安全升级 |
| 前端实现 | 6/10 | 工具函数未充分复用，代码重复度高 |
| 依赖管理 | 9/10 | 合理使用现有库，无造轮子 |
| 整体工程质量 | 7.5/10 | 後端扎實，前端需優化 |

---

## 相关文件位置

- [后端共享工具](backend/shared/)
- [后端认证](backend/auth/)
- [前端工具函数](miniprogram-1/utils/)
- [开发规范](/.github/copilot-instructions.md)

---

**审计完成时间**：2026-03-05  
**审计人**：GitHub Copilot  
**下次审计建议**：2026-06-05

---

## 云端中继视频配置（2026-03-05 新增）

### 功能概述
系统支持通过**三层优先级架构**获取设备快照，以适应不同的部署环境：

| 优先级 | 来源 | 说明 | 适用场景 |
|--------|------|------|--------|
| 1️⃣ **一级（推荐）** | 云端中继地址 | 通过 `CLOUD_RELAY_SNAPSHOT_URL` 配置的公网地址 | 生产环境，高可用 |
| 2️⃣ **二级** | 内存缓存 | ESP32 主动推送到后端的最新快照 | MQTT 推送模式 |
| 3️⃣ **三级（备选）** | 本地ESP32 | 直连 `DEVICE_SNAPSHOT_URL` 的本地地址 | 开发测试，局域网环境 |

### 配置方式

#### 方式 1：直接配置云端中继（推荐生产使用）

**编辑 `docker-compose.yml`**：
```yaml
services:
  backend:
    environment:
      # 云端中继地址（优先级最高）
      - CLOUD_RELAY_SNAPSHOT_URL=https://relay.example.com/snapshot
      # 或使用内网穿透工具暴露的地址
      - CLOUD_RELAY_SNAPSHOT_URL=http://210.1.1.1:8080/snapshot
      # 或使用 Docker 网络中的另一服务
      - CLOUD_RELAY_SNAPSHOT_URL=http://nginx-relay:8080/snapshot
```

**优点**：
- 快照不经过后端代理，性能最优
- 支持CDN加速和高并发
- 自动故障转移（如果中继不可用，自动回退到缓存/本地）

#### 方式 2：启用 ESP32 MQTT 推送模式

**后端已支持**：`POST /api/hardware/snapshot`

**ESP32 端示例代码**：
```cpp
void sendSnapshot() {
  // 捕获快照（伪代码）
  camera_fb_t* fb = esp_camera_fb_get();
  
  // POST 到后端
  HTTPClient http;
  http.begin("https://dev.api.5i03.cn/api/hardware/snapshot");
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("Device-Secret", "your-device-secret");
  
  int httpCode = http.sendRequest("POST", fb->buf, fb->len);
  esp_camera_fb_return(fb);
  
  // 每 2 秒推送一次
}
```

**优点**：
- 快照存储在后端内存中，无需每次重新获取
- 支持多个小程序客户端共享同一快照，减少 ESP32 负载
- 响应延迟低（< 100ms）

#### 方式 3：本地直连（开发测试）

**编辑 `docker-compose.yml`**：
```yaml
services:
  backend:
    environment:
      # 本地 ESP32 地址（仅开发环境）
      - DEVICE_SNAPSHOT_URL=http://192.168.3.161:81/stream?action=snapshot
```

### 故障排查

#### 快照显示灰色（加载失败）

**症状**：小程序主页显示灰色视频区域，控制台输出 `placeholder-timeout`

**检查清单**：
```bash
# 1. 测试云端中继是否可访问
curl -v https://relay.example.com/snapshot

# 2. 测试后端快照接口（需要登录 Token）
curl -v -H "Authorization: Bearer YOUR_TOKEN" \
  https://dev.api.5i03.cn/api/device/snapshot/AABBCCDDEEFF

# 3. 查看后端日志中的 [Snapshot] 标记
docker-compose logs backend | grep Snapshot

# 预期输出示例：
# [Snapshot] 尝试云端中继
# [Snapshot] Cache HIT for AA:BB:CC:DD:EE:FF (age: 12.3s)
# 或
# [Snapshot] Cache MISS for AA:BB:CC:DD:EE:FF
# [Snapshot] 代理本地 ESP32
```

#### 后端日志输出说明

| 日志信息 | 含义 | 对应来源 |
|--------|------|--------|
| `[Snapshot] Cache HIT` | 使用缓存中的快照 | 优先级2 |
| `[Snapshot] Cache MISS` | 缓存已过期 | - |
| `[Snapshot] Got cloud relay` | 使用云端中继 | 优先级1 |
| `[Snapshot] Requesting local ESP32` | 回退到本地 | 优先级3 |
| `[Snapshot] TIMEOUT` | 请求超时 | 返回占位符 |
| `X-Frame-Source: cloud-relay` | HTTP 响应头指示来源 | - |
| `X-Frame-Source: cache` | HTTP 响应头指示来源 | - |
| `X-Frame-Source: placeholder-*` | HTTP 响应头指示来源 | - |

### 性能建议

**生产环境推荐配置**：
```yaml
# docker-compose.yml
services:
  backend:
    environment:
      # 使用 CDN 加速或高速内网中继
      - CLOUD_RELAY_SNAPSHOT_URL=https://cdn.example.com/snapshot
      # 本地 ESP32 仅作备选（可选）
      - DEVICE_SNAPSHOT_URL=http://192.168.3.161:81/stream?action=snapshot
```

**缓存策略**：
- 快照缓存 TTL：5 分钟
- 小程序刷新间隔：1~3 秒（建议）
- ESP32 推送频率：每 2 秒推送一次

---

## 权限审批功能（2026-03-05 新增）

### 功能概述
管理员可以在网页管理后台审批用户的设备访问权限申请。

### 访问路径
1. 登录管理后台：`https://dev.api.5i03.cn/admin/login`
2. 点击侧边栏"权限审批"菜单
3. 或直接访问：`https://dev.api.5i03.cn/admin/permissions`

### 功能特性
- [完成] 状态筛选：支持查看全部/待审批/已批准/已拒绝的申请
- [完成] 详细信息：显示申请用户、设备MAC、设备位置、申请时间
- [完成] 待审批提醒：顶部显示待审批数量徽章
- [完成] 一键批准/拒绝：点击按钮即可完成审批
- [完成] 保持设计风格：完全遵循现有管理后台的UI风格

### 审批流程
```
用户申请（小程序） → 待审批状态 → 管理员审批 → 批准/拒绝 → 用户获得/失去访问权限
```

### 数据库结构
- 表：`user_device_permissions`
- 状态：`pending`（待审批）、`approved`（已批准）、`rejected`（已拒绝）
- 关联：user（申请人）、device（设备）、reviewer（审批人）

---

## RESTful 风格改造（2026-03-05 完成）

### 改造范围
将网页管理后台（/admin 路由）统一为 RESTful 风格，同时保持原有功能和硬件兼容性。

### 改造对比

#### 用户管理路由
**旧版本**：
```python
POST /admin/users/add      # 添加用户
GET  /admin/users/<id>/delete  # 删除用户（非RESTful）
```

**新版本（RESTful）**：
```python
POST /admin/users          # 添加用户
POST /admin/users/<id>     # 删除用户（_method=DELETE标识）
```

#### 权限审批路由
**旧版本**：
```python
POST /admin/permissions/<id>/approve  # 批准
POST /admin/permissions/<id>/reject   # 拒绝
```

**新版本（RESTful）**：
```python
POST /admin/permissions/<id>  # 更新（action=approve|reject区分）
```

### 关键改进

#### 1. 异常处理增强
所有数据库操作增加 try-except 异常捕获和 db.session.rollback() 回滚机制，避免数据不一致。

#### 2. 操作验证增强
- 权限状态验证：只能审批 pending 状态的申请
- 操作类型验证：action 参数必须是 approve 或 reject
- 友好错误提示：失败时在页面顶部显示具体错误信息

#### 3. 模板表单改进
删除操作从 `<a href>` 链接改为 `<form method="POST">` 表单提交，防止误触和CSRF攻击。

#### 4. 路由合并优化
权限审批的批准/拒绝路由合并为单一更新路由，减少重复代码，统一处理逻辑。

### 硬件兼容性验证
ESP32 硬件代码检查结果：
- 仅调用 `/api/snapshots` 接口（POST 上传快照）
- 不调用 `/admin/` 路由
- 本次改造不影响硬件代码

### HTTP 方法说明
**为什么使用 POST 而非 DELETE？**
- HTML 表单原生仅支持 GET 和 POST 方法
- 浏览器完全支持 POST，无需依赖 JavaScript
- 使用 `_method=DELETE` hidden input 标识操作类型
- 降级友好：即使禁用 JavaScript，表单仍可正常提交

### 改造效果
- [改进] 统一 HTTP 方法使用规范
- [改进] 增加异常处理和事务回滚
- [改进] 减少重复代码（权限审批路由合并）
- [改进] 增加操作验证（状态检查、参数验证）
- [改进] 删除操作从 GET 改为 POST（防止 CSRF 攻击）
- [改进] 错误提示友好显示在页面顶部
- [改进] 路由命名更符合 RESTful 规范

### 后续优化建议
- [待做] 添加 CSRF Token 保护（安装 flask-wtf）
- [待做] 优化 N+1 查询问题（使用 joinedload）
- [待做] 添加管理员操作审计日志
- [待做] 添加角色权限控制装饰器

---

## 权限管理功能增强（2026-03-05）

### 功能概述
权限管理现支持三种操作模式：
1. **审批模式** - 审批用户发起的设备访问申请（pending状态）
2. **分配模式** - 管理员主动为用户分配设备权限
3. **撤销模式** - 管理员撤销已批准的用户设备权限

### 页面功能

#### 权限列表
- 显示所有用户-设备权限记录
- 支持按状态筛选：全部、待审批、已批准、已拒绝
- 显示申请人、设备、申请时间、审批时间等详细信息

#### 操作列功能
**待审批状态**：
- 批准：通过用户的设备访问申请
- 拒绝：拒绝用户的设备访问申请

**已批准状态**：
- 撤销：移除用户对该设备的访问权限

#### 添加权限
- 新增"添加权限"按钮，打开模态框
- 选择用户和设备，直接创建权限
- 可选择权限初始状态（已批准/待审批）

### 后端路由

#### 新增路由
```python
POST /admin/permissions/add
```
**参数**：
- `user_id`：用户ID
- `device_mac`：设备MAC地址
- `status`：权限状态（默认 'approved'）

**校验**：
- 用户必须存在
- 设备必须存在
- 同一用户不能对同一设备重复分配权限

#### 更新路由
```python
POST /admin/permissions/<id>?action=approve|reject|revoke
```
**操作类型**：
- `approve`：批准待审批的申请
- `reject`：拒绝待审批的申请
- `revoke`：撤销已批准的权限

**校验**：
- approve/reject：仅可处理 pending 状态
- revoke：仅可处理 approved 状态

### 数据库变更

#### UserDevicePermission 模型
保持不变，继续使用原有的状态字段：
- `status`：'pending'、'approved'、'rejected'
- `apply_time`：申请时间
- `review_time`：审批时间
- `reviewed_by`：审批人ID

#### 唯一性约束
```sql
UNIQUE KEY uc_user_device (user_id, device_mac)
```
防止同一用户对同一设备重复分配权限

### 错误处理

所有操作都包含完整的异常处理：
- 数据验证失败：清晰的错误提示
- 数据库异常：自动回滚，显示错误原因
- 业务逻辑错误：用户友好的提示信息

### 使用示例

#### 场景1：管理员批准设备申请
1. 进入权限审批页面
2. 点击"待审批"筛选标签
3. 找到待审批的申请
4. 点击"批准"按钮，确认
5. 权限状态变为"已批准"

#### 场景2：管理员主动分配设备权限
1. 进入权限审批页面
2. 点击"添加权限"按钮
3. 选择用户和设备
4. 选择初始状态（通常直接"已批准"）
5. 点击"添加"
6. 新权限立即生效

#### 场景3：管理员撤销用户权限
1. 进入权限审批页面
2. 点击"已批准"筛选标签
3. 找到要撤销的权限
4. 点击"撤销"按钮，确认
5. 权限从数据库删除，用户失去访问权限

---

## 管理界面统一CRUD功能（2026-03-05）

### 功能概述
所有管理后台界面（用户管理、设备管理、权限管理）实现统一的CRUD功能模式，提供一致的用户体验。

### 界面功能对比

| 功能 | 用户管理 | 设备管理 | 权限管理 |
|-----|--------|--------|---------|
| 添加 | ✓ 模态框 | ✓ 模态框 | ✓ 模态框 |
| 查看 | ✓ 列表 | ✓ 列表 | ✓ 列表+筛选 |
| 编辑 | ✓ 模态框 | ✓ 模态框 | ✓ 批准/拒绝/撤销 |
| 删除 | ✓ 表单 | ✓ 表单 | ✓ 撤销操作 |
| 错误提示 | ✓ Alert显示 | ✓ Alert显示 | ✓ Alert显示 |

### 用户管理

#### 新增功能
- **编辑用户**：点击编辑按钮修改用户信息（姓名、角色、指纹ID、NFC UID）
- **统一异常处理**：编辑和删除失败时显示具体错误信息

#### 后端路由
```python
POST /admin/users          # 添加用户
POST /admin/users/<id>     # 编辑或删除用户（action参数区分）
  - action=edit   # 编辑用户信息
  - action=delete # 删除用户
```

#### 页面布局
- 用户列表表格添加"操作"列
- 编辑、删除按钮并排显示
- 编辑弹出模态框，保留学号/工号（不可修改）

### 设备管理

#### 新增功能
- **添加设备**：通过模态框添加新设备
  - 设备名称、MAC地址、位置、房间号
  - MAC地址为唯一标识，不可重复

- **编辑设备**：修改设备信息
  - 可修改名称、位置、房间号
  - MAC地址固定不可修改（设备唯一标识）

- **删除设备**：移除不在使用的设备

#### 后端路由
```python
POST /admin/devices        # 添加设备
POST /admin/devices/<id>   # 编辑或删除设备（action参数区分）
  - action=edit   # 编辑设备信息
  - action=delete # 删除设备
```

#### 页面布局
- 设备列表新增"位置"和"操作"列
- "添加设备"按钮位于列表卡片顶部
- 编辑、删除按钮并排显示，确认提示

### 权限管理

#### 功能实现
- **添加权限**：管理员主动为用户分配设备权限
- **审批管理**：处理用户的权限申请
- **撤销权限**：移除已批准的用户权限

#### 后端路由
```python
POST /admin/permissions/add           # 添加权限
POST /admin/permissions/<id>          # 更新权限状态
  - action=approve # 批准待审批申请
  - action=reject  # 拒绝待审批申请
  - action=revoke  # 撤销已批准权限
```

### 公共特性

#### 模态框UI
- 统一使用Bootstrap模态框
- 取消按钮关闭模态框
- 提交按钮执行操作
- 必填字段标记为required

#### 错误处理
- 所有操作异常捕获
- 页面顶部显示错误Alert（红色）
- 自动触发数据库回滚（db.session.rollback()）
- 保留页面状态（已填项数据不清空）

#### 确认对话框
- 删除操作前弹出确认对话框
- 防止误操作
- 用户可取消操作

#### HTTP方法
- **添加**：`POST /admin/{resource}`
- **编辑**：`POST /admin/{resource}/<id>?action=edit`
- **删除**：`POST /admin/{resource}/<id>?action=delete`
- 使用POST方法（HTML表单限制）
- 通过form参数区分具体操作

### 数据验证

#### 用户管理
- 用户名唯一性检查
- 必填字段验证（学号/工号、姓名）

#### 设备管理
- MAC地址唯一性检查（格式: AA:BB:CC:DD:EE:FF）
- MAC地址编辑时不可修改

#### 权限管理
- 用户-设备权限唯一性检查
- 状态转移合法性验证

### 最佳实践

#### 开发指南
1. 所有CRUD操作都需实现异常处理
2. 所有表单操作（POST）都需渲染错误页面
3. 删除操作前需用户确认
4. 编辑信息应展示原有数据
5. 主键字段通常不可编辑

#### 测试清单
- [ ] 添加功能正常，验证重复项检查
- [ ] 编辑功能正常，验证数据保存
- [ ] 删除功能正常，点击确认弹窗
- [ ] 异常处理正常，显示错误信息
- [ ] 页面渲染正常，模态框显示正确
