from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
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

    # 实时视频流代理配置（纯转发，不存数据库）
    app.config['DEVICE_STREAM_URL_TEMPLATE'] = os.getenv(
        'DEVICE_STREAM_URL',
        'http://192.168.3.161:81/stream'  # ESP32视频流地址
    )
    app.config['DEVICE_SNAPSHOT_URL_TEMPLATE'] = os.getenv(
        'DEVICE_SNAPSHOT_URL',
        'http://192.168.3.161:81/stream?action=snapshot'  # ESP32快照地址
    )

    db.init_app(app)

    # 导入数据模型
    from core.models import User, Device, Log, Admin, UserDevicePermission

    with app.app_context():
        # 安全的表初始化：仅创建不存在的表，不删除现有数据
        db.create_all()

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
