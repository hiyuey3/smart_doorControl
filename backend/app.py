from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import inspect, text
import os
from threading import Lock

# MySQL 数据库驱动
import pymysql
pymysql.install_as_MySQLdb()

# 全局数据库实例
# SQLAlchemy ORM 的核心对象，用于管理数据库会话和模型映射
db = SQLAlchemy()

# 全局快照缓存 - 用于实时视频预览和性能优化
# 结构：{mac_address: {'data': base64字符串, 'timestamp': float}, ...}
# 用途：
#   1. ESP32 主动推送快照到此缓存（通过 POST /api/hardware/snapshot）
#   2. 小程序定期从此缓存拉取（通过 GET /api/device/snapshot）
#   3. 避免每次都从本地ESP32直连获取（性能优化）
#   4. 支持多个小程序客户端共享同一快照
# 缓存有效期：5分钟（通过 proxy_device_snapshot 函数管理）
device_frames = {}
device_frames_lock = Lock()  # 线程安全的读写锁，防止并发冲突


def _ensure_device_columns(app):
    """
    数据库向后兼容性处理函数
    
    功能：为历史数据库的 devices 表补齐可能缺失的列
    场景：系统升级时，如果旧数据库结构不完整，此函数会自动添加新列
    
    补齐的列：
    - location：设备位置描述（字符串）
    - ip_address：设备本地IP地址（用于本地快照降级）
    
    异常处理：
    - 表不存在时跳过
    - 列已存在时跳过
    - SQL 执行失败时回滚，不影响其他操作
    """
    with app.app_context():
        inspector = inspect(db.engine)
        if 'devices' not in inspector.get_table_names():
            return

        existing_columns = {col['name'] for col in inspector.get_columns('devices')}
        ddl_statements = []

        if 'location' not in existing_columns:
            ddl_statements.append("ALTER TABLE devices ADD COLUMN location VARCHAR(100)")
        if 'ip_address' not in existing_columns:
            ddl_statements.append("ALTER TABLE devices ADD COLUMN ip_address VARCHAR(15)")

        for ddl in ddl_statements:
            try:
                db.session.execute(text(ddl))
                db.session.commit()
                print(f"[DB] Applied migration: {ddl}")
            except Exception as migration_error:
                db.session.rollback()
                print(f"[DB] Migration skipped/failed: {migration_error}")


def create_app():
    """
    Flask 应用工厂函数
    
    功能：创建和配置 Flask 应用实例
    返回：Flask 应用对象
    
    初始化流程：
    1. 创建 Flask 实例（指定模板目录和静态文件目录）
    2. 配置反向代理支持（ProxyFix 中间件）
    3. 配置 CORS 跨域支持（小程序和前端可访问）
    4. 加载配置参数（从环境变量或默认值）
    5. 初始化数据库连接
    6. 创建数据库表和默认数据
    7. 注册 API 和管理后台 Blueprint
    8. 初始化 MQTT 连接
    """
    
    # 创建 Flask 应用
    # 模板目录：用于渲染网页管理后台的 HTML 页面
    # 静态文件目录：用于提供 CSS、JavaScript、图片等资源
    template_folder = os.path.join(os.path.dirname(__file__), 'admin', 'templates')
    app = Flask(
        __name__, 
        template_folder=template_folder,
        static_folder='static', 
        static_url_path='/static'
    )

    # 反向代理中间件配置
    # 问题：当应用在 Nginx 反向代理后面时，Flask 获取的 request.remote_addr、request.url 等信息
    # 会是代理服务器的地址，而不是真实客户端的地址
    # 解决：使用 ProxyFix 中间件解析 Nginx 传递的 X-Forwarded-* 请求头
    # 参数说明：
    #   x_for=1：信任 1 层代理，解析 X-Forwarded-For 头（客户端真实IP）
    #   x_proto=1：信任 X-Forwarded-Proto 头（识别 HTTP 或 HTTPS）
    #   x_host=1：信任 X-Forwarded-Host 头（识别真实域名，修复 redirect 到 127.0.0.1 的问题）
    #   x_prefix=1：信任 X-Forwarded-Prefix 头（识别 URL 路径前缀）
    app.wsgi_app = ProxyFix(
        app.wsgi_app, 
        x_for=1, 
        x_proto=1, 
        x_host=1, 
        x_prefix=1
    )

    # JSON 响应配置
    app.config['JSON_AS_ASCII'] = False  # 允许 JSON 中包含中文，不转义为 \uXXXX

    # CORS（跨域资源共享）配置
    # 允许小程序、网页、移动端等不同来源的客户端访问 API
    CORS(app, resources={
        r"/*": {
            "origins": "*",  # 允许所有来源
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # 应用密钥配置
    # 用于 Session 加密、JWT 签名等安全操作
    # 建议在生产环境配置强密钥，通过环境变量设置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'biyeueji-access-control-secret-key-2026')

    # 微信小程序登录配置
    # 获取方式：微信开放平台 -> 管理中心 -> 开发设置
    app.config['WX_APPID'] = 'wxafdb3def456f3bca'
    app.config['WX_APPSECRET'] = '33ee38d82410fc8efbaefa3484e3e91c'
    
    # JWT Token 有效期配置
    # 默认 7 天，用户登录后 7 天内无需重新登录
    # 值得注意：Token 过期后小程序会自动跳转至登录页（request.js 中处理 401 状态）
    app.config['JWT_EXPIRATION'] = int(os.getenv('JWT_EXPIRATION', 7 * 24 * 3600))

    # 数据库连接配置
    # 支持多种数据库：
    #   - SQLite：sqlite:///access_control.db（开发调试）
    #   - MySQL：mysql+pymysql://user:password@host:3306/dbname（生产环境）
    #   - PostgreSQL：postgresql://...（可选）
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///access_control.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 禁用事件系统优化性能

    # MQTT 消息队列配置
    # 用于与 ESP32 硬件通信：发送开锁指令、接收心跳等
    app.config['MQTT_BROKER'] = os.getenv('MQTT_BROKER', 'mqtt.5i03.cn')
    app.config['MQTT_PORT'] = int(os.getenv('MQTT_PORT', 1883))
    app.config['MQTT_USERNAME'] = os.getenv('MQTT_USERNAME', '')
    app.config['MQTT_PASSWORD'] = os.getenv('MQTT_PASSWORD', '')
    app.config['MQTT_CLIENT_ID'] = os.getenv('MQTT_CLIENT_ID', 'access_control_backend')
    app.config['ENABLE_MQTT'] = os.getenv('ENABLE_MQTT', '1') in {'1', 'true', 'yes'}

    # 实时视频/快照代理配置
    # 系统支持三层快照获取策略（优先级递减）：
    #
    # 优先级 1：云端中继地址（推荐生产环境）
    #   - 优点：高可用、低延迟、支持CDN
    #   - 配置：CLOUD_RELAY_SNAPSHOT_URL
    #   - 场景：校园外用户、高并发场景
    #
    # 优先级 2：后端内存缓存
    #   - 优点：减少 ESP32 负载、缓存命中快
    #   - 原理：ESP32 定期推送快照到 device_frames 字典
    #   - 场景：本地MQTT推送模式
    #
    # 优先级 3：本地 ESP32 直连
    #   - 优点：最新画面、无网络延迟
    #   - 配置：DEVICE_SNAPSHOT_URL_TEMPLATE
    #   - 场景：开发调试、局域网环境
    
    app.config['DEVICE_STREAM_URL_TEMPLATE'] = os.getenv(
        'DEVICE_STREAM_URL',
        'http://192.168.3.161:81/stream'
    )
    
    # 云端中继快照地址（推荐生产环境配置）
    # 示例：
    #   - 'https://relay.example.com/snapshot'（公网 HTTPS）
    #   - 'http://210.1.1.1:8080/snapshot'（内网 HTTP）
    #   - 'http://nginx-relay:8080/snapshot'（Docker 网络）
    app.config['CLOUD_RELAY_SNAPSHOT_URL'] = os.getenv(
        'CLOUD_RELAY_SNAPSHOT_URL',
        ''
    )
    
    # 本地 ESP32 快照 URL（仅用于降级和开发）
    app.config['DEVICE_SNAPSHOT_URL_TEMPLATE'] = os.getenv(
        'DEVICE_SNAPSHOT_URL',
        'http://192.168.3.161:81/stream?action=snapshot'
    )
    
    # 小程序前端快照 URL 模板
    # 产生环境可直接配置为云端中继地址，绕过后端代理以提升性能
    # 默认通过后端代理（支持权限检查）
    app.config['CLIENT_SNAPSHOT_URL_TEMPLATE'] = os.getenv(
        'CLIENT_SNAPSHOT_URL',
        '/api/device/snapshot'
    )

    # 初始化 SQLAlchemy 数据库连接
    db.init_app(app)

    # 导入所有数据模型（必须在 create_all 之前）
    from core.models import User, Device, Log, Admin, UserDevicePermission

    with app.app_context():
        # 创建所有数据库表（幂等操作：表存在时不操作）
        db.create_all()
        
        # 向后兼容性：为旧数据库补齐新增列
        _ensure_device_columns(app)

        # 初始化默认管理员账户（开发和部署时使用）
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            admin = Admin(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(' 默认管理员已创建：admin / admin123 ')

    # 注册 API 路由蓝图
    # 包含所有 REST API 端点：/api/login、 /api/devices、/api/logs 等
    from api import bp as api_bp
    app.register_blueprint(api_bp)

    # 注册网页管理后台蓝图
    # 包含所有管理端点：/admin/login、/admin/users、/admin/permissions 等
    from admin import routes as web_routes
    app.register_blueprint(web_routes.web_bp)

    # 初始化 MQTT 消息队列连接
    # 用于与 ESP32 硬件通信
    if app.config.get('ENABLE_MQTT', True):
        from mqtt import init_mqtt, mqtt
        init_mqtt(app)
        
        # 等待 MQTT 连接完成（后台线程）
        import time
        import threading
        
        def wait_mqtt_connected():
            """
            后台线程：等待 MQTT 连接成功
            
            目的：确保应用启动时已连接到 MQTT Broker
            超时：30 秒（超时后继续启动，可能稍后自动连接）
            """
            print("Waiting for MQTT broker connection...")
            timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    if hasattr(mqtt, 'client') and mqtt.client and hasattr(mqtt.client, 'is_connected'):
                        if mqtt.client.is_connected():
                            print("[MQTT] Connected successfully!")
                            return
                except:
                    pass
                time.sleep(0.5)
            
            print("[MQTT] Connection timeout or will connect later")
        
        # 在后台线程中等待连接（不阻塞主启动流程）
        t = threading.Thread(target=wait_mqtt_connected, daemon=True)
        t.start()

    return app
