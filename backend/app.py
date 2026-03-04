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

db = SQLAlchemy()

# # 全局快照缓存 - 用于 HTTP 推送模型的视频预览系统
# # 结构：{mac_address: {'data': bytes, 'timestamp': float}, ...}
# 用途：ESP32 主动推送最新快照到此字典，前端定期从此字典拉取
device_frames = {}
device_frames_lock = Lock()  # 线程安全的写入锁


def _ensure_device_columns(app):
    """为历史数据库补齐 devices 表缺失字段。"""
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
    # 指定模板目录（相对于当前文件）
    template_folder = os.path.join(os.path.dirname(__file__), 'admin', 'templates')
    app = Flask(
        __name__, 
        template_folder=template_folder,
        static_folder='static', 
        static_url_path='/static'
    )

    # 🔧 反向代理支持 - 修复 redirect 重定向到 127.0.0.1 的问题
    # x_for=1: 信任 1 层代理的 X-Forwarded-For
    # x_proto=1: 信任 X-Forwarded-Proto（识别 HTTPS）
    # x_host=1: 信任 X-Forwarded-Host（识别真实域名）
    # x_prefix=1: 信任 X-Forwarded-Prefix（识别 URL 前缀）
    app.wsgi_app = ProxyFix(
        app.wsgi_app, 
        x_for=1, 
        x_proto=1, 
        x_host=1, 
        x_prefix=1
    )

    # JSON 支持中文
    app.config['JSON_AS_ASCII'] = False

    # 允许小程序跨域访问
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # 密钥配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'biyeueji-access-control-secret-key-2026')

    # 微信小程序登录配置
    app.config['WX_APPID'] = 'wxafdb3def456f3bca'
    app.config['WX_APPSECRET'] = '33ee38d82410fc8efbaefa3484e3e91c'
    
    # Token 有效期（秒）
    app.config['JWT_EXPIRATION'] = int(os.getenv('JWT_EXPIRATION', 7 * 24 * 3600))

    # 数据库配置
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///access_control.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # MQTT 配置
    app.config['MQTT_BROKER'] = os.getenv('MQTT_BROKER', 'mqtt.5i03.cn')
    app.config['MQTT_PORT'] = int(os.getenv('MQTT_PORT', 1883))
    app.config['MQTT_USERNAME'] = os.getenv('MQTT_USERNAME', '')
    app.config['MQTT_PASSWORD'] = os.getenv('MQTT_PASSWORD', '')
    app.config['MQTT_CLIENT_ID'] = os.getenv('MQTT_CLIENT_ID', 'access_control_backend')
    app.config['ENABLE_MQTT'] = os.getenv('ENABLE_MQTT', '1') in {'1', 'true', 'yes'}

    # 实时视频流代理配置 - 支持三层优先级
    # 优先级1：云端中继地址（推荐用于生产环境）
    # 优先级2：设备数据库配置的stream_url字段
    # 优先级3：本地ESP32直连地址（仅用于开发调试）
    app.config['DEVICE_STREAM_URL_TEMPLATE'] = os.getenv(
        'DEVICE_STREAM_URL',
        'http://192.168.3.161:81/stream'  # 本地ESP32视频流地址（降级方案）
    )
    
    # 云端中继视频快照地址（推荐配置此项以替代本地ESP32）
    # 示例：'https://relay.example.com/snapshot' 或 'http://210.1.1.1:8080/snapshot'
    app.config['CLOUD_RELAY_SNAPSHOT_URL'] = os.getenv(
        'CLOUD_RELAY_SNAPSHOT_URL',
        ''  # 如配置此项，则优先使用云端中继而非本地ESP32
    )
    
    # 快照URL模板（作为降级方案，仅在云端中继不可用时使用）
    app.config['DEVICE_SNAPSHOT_URL_TEMPLATE'] = os.getenv(
        'DEVICE_SNAPSHOT_URL',
        'http://192.168.3.161:81/stream?action=snapshot'  # 本地ESP32快照地址
    )
    
    # 小程序前端使用的快照访问地址
    # 生产环境推荐直接配置为云端中继地址（绕过后端代理以提升性能）
    app.config['CLIENT_SNAPSHOT_URL_TEMPLATE'] = os.getenv(
        'CLIENT_SNAPSHOT_URL',
        '/api/device/snapshot'  # 默认通过后端代理，支持权限检查
    )

    db.init_app(app)

    # 导入数据模型
    from core.models import User, Device, Log, Admin, UserDevicePermission

    with app.app_context():
        # 安全的表初始化：仅创建不存在的表，不删除现有数据
        db.create_all()
        _ensure_device_columns(app)

        # 创建默认管理员（仅在不存在时创建）
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            admin = Admin(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(' 默认管理员：admin / admin123 ')

    # 注册路由蓝图
    from api import bp as api_bp
    app.register_blueprint(api_bp)

    # 注册网页管理后台
    from admin import routes as web_routes
    app.register_blueprint(web_routes.web_bp)

    # 初始化 MQTT（需要在蓝图注册之后）
    if app.config.get('ENABLE_MQTT', True):
        from mqtt import init_mqtt, mqtt
        init_mqtt(app)
        
        # 等待 MQTT 连接完成（确保后端启动时已连接）
        import time
        import threading
        
        def wait_mqtt_connected():
            """等待 MQTT 连接成功"""
            print("Waiting for MQTT broker connection...")
            timeout = 30  # 30秒超时
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # 检查 MQTT 客户端是否已连接
                try:
                    if hasattr(mqtt, 'client') and mqtt.client and hasattr(mqtt.client, 'is_connected'):
                        if mqtt.client.is_connected():
                            print("[MQTT] OK: Connected successfully!")
                            return
                except:
                    pass
                time.sleep(0.5)
            
            print("[MQTT] WARN: Connection timeout (may connect later)")
        
        # 在后台线程中等待连接
        t = threading.Thread(target=wait_mqtt_connected, daemon=True)
        t.start()

    return app
