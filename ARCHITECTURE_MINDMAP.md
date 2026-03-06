# 智能门禁系统 - 架构思维导图

## 📊 系统架构思维导图

```mermaid
mindmap
  root((智能门禁系统<br/>云端中枢))
    架构设计
      RESTful分层
        数据层: SQLAlchemy ORM
        业务层: 辅助类设计
        路由层: Flask蓝图
      设计模式
        应用工厂模式
        混入模式Mixin
        代理模式
    数据库设计
      Mixin基类
        BaseIDMixin: 主键
        TimestampMixin: 时间戳
        SerializerMixin: 序列化
      核心模型
        User: 用户模型
        Device: 设备模型
        Permission: 权限模型
        Log: 日志模型
      权限关联
        多对多关系
        枚举状态机
    辅助工具类
      DatabaseHelper
        统一CRUD操作
        自动事务回滚
        错误处理
      ResponseHelper
        标准化响应格式
        HTTP状态码
        错误码定义
      LogHelper
        事件ID生成
        全链路追溯
        多种日志类型
    认证授权
      JWT认证
        密码登录
        微信免密登录
        Token验证装饰器
      BOLA防护
        权限拦截器
        访问控制列表
        防越权攻击
      权限管理
        申请权限
        审批权限
        撤销权限
    REST API
      认证接口
        POST /api/login
      设备管理
        GET /api/devices
        POST /api/devices
        PUT /api/devices/<mac>
        DELETE /api/devices/<mac>
      远程控制
        POST /api/device/unlock
        GET /api/device/snapshot/<mac>
      权限管理
        POST /api/permissions/apply
        GET /api/permissions
        PUT /api/permissions/<id>
        DELETE /api/permissions/<id>
      日志查询
        GET /api/logs
    安全机制
      身份认证
        JWT Token
        HMAC-SHA256
        自动过期
      权限控制
        对象级权限
        角色区分
        动态授权
      数据保护
        事务回滚
        SQL注入防护
        敏感信息加密
      审计日志
        全局事件ID
        操作追溯
        图像关联
```

---

## 🔄 权限状态机流转图

```mermaid
stateDiagram-v2
    [*] --> pending: 用户申请权限
    pending --> approved: 管理员批准
    pending --> rejected: 管理员拒绝
    approved --> [*]: 权限撤销
    rejected --> [*]: 权限撤销

    note right of pending
        待审批状态
        用户已发起申请
        等待管理员审批
    end note

    note right of approved
        已批准状态
        用户可访问设备
        可执行远程开锁
    end note

    note right of rejected
        已拒绝状态
        用户无权访问
        可重新申请
    end note
```

---

## 🔐 认证授权流程图

```mermaid
sequenceDiagram
    participant 小程序
    participant 云端API
    participant JWT中间件
    participant 权限拦截器
    participant 数据库

    小程序->>云端API: POST /api/login<br/>{login_type, code/username/password}
    云端API->>数据库: 验证用户身份
    数据库-->>云端API: 返回用户信息
    云端API->>云端API: 签发JWT Token
    云端API-->>小程序: 返回Token

    Note over 小程序,云端API: 后续请求携带Token

    小程序->>云端API: POST /api/device/unlock<br/>Authorization: Bearer <token>
    云端API->>JWT中间件: 验证Token
    JWT中间件->>JWT中间件: 解码JWT<br/>验证签名<br/>检查过期
    JWT中间件->>数据库: 加载用户信息
    数据库-->>JWT中间件: 返回用户对象
    JWT中间件->>云端API: g.current_user = user

    云端API->>权限拦截器: 检查设备访问权限
    权限拦截器->>数据库: 查询权限表
    数据库-->>权限拦截器: 返回权限状态
    alt 权限不足
        权限拦截器-->>小程序: 403 Forbidden
    else 权限验证通过
        权限拦截器->>云端API: 允许访问
        云端API->>云端API: 执行开锁指令
        云端API->>数据库: 记录操作日志
        云端API-->>小程序: 200 OK
    end
```

---

## 📊 数据库关系图

```mermaid
erDiagram
    USER ||--o{ USER_DEVICE_PERMISSION : "申请"
    USER ||--o{ USER_DEVICE_PERMISSION : "审批"
    USER ||--o{ LOG : "操作"
    DEVICE ||--o{ USER_DEVICE_PERMISSION : "授权"
    DEVICE ||--o{ LOG : "记录"

    USER {
        int id PK
        string openid UK "微信OpenID"
        string username UK "用户名"
        string password "密码哈希"
        enum role "角色"
        string fingerprint_id "指纹ID"
        string nfc_uid "NFC卡UID"
    }

    DEVICE {
        string mac_address PK "设备MAC地址"
        string name "设备名称"
        string room_number "房间号"
        string location "位置"
        enum status "在线状态"
        datetime last_heartbeat "最后心跳"
    }

    USER_DEVICE_PERMISSION {
        int id PK
        int user_id FK "用户ID"
        string device_mac FK "设备MAC"
        enum status "权限状态"
        datetime apply_time "申请时间"
        datetime review_time "审批时间"
        int reviewed_by FK "审批人ID"
    }

    LOG {
        string event_id PK "事件ID"
        string mac_address FK "设备MAC"
        int user_id FK "用户ID"
        enum unlock_method "开锁方式"
        string snapshot_url "快照URL"
        datetime create_time "创建时间"
    }
```

---

## 🏗️ 系统架构层次图

```mermaid
graph TB
    subgraph "客户端层"
        A[微信小程序]
    end

    subgraph "API网关层"
        B[Nginx反向代理]
    end

    subgraph "应用服务层 - Flask"
        C[REST API路由]
        D[JWT认证中间件]
        E[权限拦截器]
        F[业务逻辑处理]
    end

    subgraph "辅助工具层"
        G[DatabaseHelper<br/>统一数据访问]
        H[ResponseHelper<br/>响应格式化]
        I[LogHelper<br/>日志记录]
        J[PermissionHelper<br/>权限检查]
    end

    subgraph "数据持久层"
        K[(MySQL数据库)]
        L[User模型]
        M[Device模型]
        N[Permission模型]
        O[Log模型]
    end

    subgraph "通信层"
        P[MQTT Broker]
        Q[ESP32设备]
    end

    A -->|HTTPS| B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    F --> J

    G --> K
    G --> L
    G --> M
    G --> N
    G --> O

    F -->|MQTT| P
    P <-->|MQTT| Q

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#e8f5e9
    style D fill:#f3e5f5
    style E fill:#ffebee
    style F fill:#e8f5e9
    style G fill:#f1f8e9
    style H fill:#f1f8e9
    style I fill:#f1f8e9
    style J fill:#f1f8e9
    style K fill:#fff9c4
    style P fill:#e0f2f1
    style Q fill:#e0f2f1
```

---

## 📡 MQTT通信流程图

```mermaid
sequenceDiagram
    participant 小程序
    participant Flask后端
    participant MQTT Broker
    participant ESP32设备

    小程序->>Flask后端: POST /api/device/unlock<br/>{mac_address: "AA:BB:CC:DD:EE:FF"}

    Note over Flask后端: 1. JWT认证<br/>2. 权限检查<br/>3. 记录日志

    Flask后端->>MQTT Broker: 发布消息<br/>Topic: device/{mac}/command<br/>Payload: {"action": "unlock"}

    MQTT Broker->>ESP32设备: 推送开锁指令

    ESP32设备->>ESP32设备: 执行开锁动作

    ESP32设备->>MQTT Broker: 发布状态更新<br/>Topic: device/{mac}/status

    MQTT Broker->>Flask后端: 订阅状态更新

    Flask后端->>Flask后端: 更新设备在线状态

    ESP32设备->>Flask后端: 上传快照图像<br/>POST /api/device/upload_snapshot

    Flask后端->>ESP32设备: 返回上传成功
```

---

## 🎯 核心代码文件映射

```mermaid
graph LR
    A[app.py<br/>应用工厂] --> B[api/routes.py<br/>REST API]
    A --> C[core/models/<br/>数据模型]

    C --> D[mixins.py<br/>基类Mixin]
    C --> E[user.py<br/>用户模型]
    C --> F[device.py<br/>设备模型]
    C --> G[permission.py<br/>权限模型]
    C --> H[log.py<br/>日志模型]

    B --> I[auth/<br/>认证授权]
    B --> J[shared/<br/>辅助工具]

    I --> K[decorators.py<br/>JWT装饰器]
    I --> L[permissions.py<br/>权限检查]

    J --> M[db_helper.py<br/>数据库操作]
    J --> N[response.py<br/>响应格式化]
    J --> O[logging.py<br/>日志记录]

    style A fill:#e3f2fd
    style B fill:#e8f5e9
    style C fill:#fff3e0
    style I fill:#fce4ec
    style J fill:#f3e5f5
```

---

## 🔒 安全防护机制图

```mermaid
graph TB
    A[客户端请求] --> B{JWT认证}
    B -->|Token无效| C[401 Unauthorized]
    B -->|Token有效| D{权限检查}

    D -->|无权限| E[403 Forbidden<br/>BOLA防护]
    D -->|有权限| F{业务逻辑}

    F --> G[数据库操作]
    G --> H{事务状态}
    H -->|成功| I[提交事务]
    H -->|失败| J[回滚事务<br/>保护数据一致性]

    I --> K[记录日志]
    J --> L[返回错误]

    K --> M[返回响应]
    L --> M

    M --> N[客户端接收]

    style B fill:#ffebee
    style D fill:#fff3e0
    style H fill:#e8f5e9
    style J fill:#ffcdd2
    style I fill:#c8e6c9
```

---

## 📈 使用流程图

```mermaid
flowchart TD
    Start([用户打开小程序]) --> Login{是否登录?}
    Login -->|否| Auth[选择登录方式]
    Auth --> Pwd[密码登录]
    Auth --> Wx[微信登录]
    Pwd --> Token[获取JWT Token]
    Wx --> Token
    Login -->|是| Home[进入首页]

    Token --> Home

    Home --> Action{选择操作}
    Action --> ViewDevices[查看设备列表]
    Action --> ApplyPerm[申请设备权限]
    Action --> RemoteUnlock[远程开锁]
    Action --> ViewLogs[查看日志]

    ViewDevices --> DeviceList[仅显示有权限的设备]
    ApplyPerm --> Pending[状态: 待审批]
    Pending --> AdminApprove[管理员审批]
    AdminApprove --> Approved[状态: 已批准]
    Approved --> DeviceList

    RemoteUnlock --> CheckPerm{检查权限}
    CheckPerm -->|无权限| Deny[403 禁止访问]
    CheckPerm -->|有权限| Unlock[发送开锁指令]
    Unlock --> RecordLog[记录日志]
    RecordLog --> Success[开锁成功]

    ViewLogs --> LogList[显示操作日志]

    style Start fill:#e1f5fe
    style Success fill:#c8e6c9
    style Deny fill:#ffcdd2
    style Approved fill:#c8e6c9
    style Pending fill:#fff9c4
```

---

**文档版本**: 1.0
**创建时间**: 2026-03-06
**作者**: Claude Code Analysis
