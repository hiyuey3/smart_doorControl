"""
Flask 配置文件示例
复制此文件为 config.py 并修改相关配置
"""
import os

class Config:
    """基础配置"""
    
    # 数据库配置    
    # SQLALCHEMY_DATABASE_URI = os.getenv(
        # 'DATABASE_URL',
        # 'sqlite:///instance/access_control.db'
    # )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT 配置    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_EXPIRATION = int(os.getenv('JWT_EXPIRATION', 7 * 24 * 3600))  # 7天
    
    # 设备认证配置    DEVICE_SECRET = os.getenv('DEVICE_SECRET', 'esp32_demo_secret')
    
    # MQTT 配置    MQTT_BROKER = os.getenv('MQTT_BROKER', 'mqtt.5i03.cn')
    MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', '')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'access_control_backend')
    ENABLE_MQTT = os.getenv('ENABLE_MQTT', '1') in {'1', 'true', 'yes'}
    
    # 实时视频流配置
    # 架构优先级：
    # 1) 云端中继地址（CLOUD_RELAY_SNAPSHOT_URL）- 最优，推荐生产环境
    # 2) 内存缓存（由 POST /api/hardware/snapshot ESP32推送）- 次优
    # 3) 本地ESP32直连（DEVICE_SNAPSHOT_URL）- 备选，仅用于开发
    
    # 方式1：云端中继配置（推荐用于生产环境）
    # 如果配置此项，后端优先使用云端中继而非本地ESP32
    # 示例值：
    #   - 'https://relay.example.com/snapshot' （通过CDN加速）
    #   - 'http://210.1.1.1:8080/snapshot' （内网穿透地址）
    #   - 'http://nginx-relay:8080/snapshot' （Docker网络中的Nginx反向代理）
    CLOUD_RELAY_SNAPSHOT_URL = os.getenv(
        'CLOUD_RELAY_SNAPSHOT_URL',
        ''  # 为空则不使用云端中继
    )
    
    # 方式2：设备流地址（作为本地ESP32直连的备选）
    DEVICE_STREAM_URL_TEMPLATE = os.getenv(
        'DEVICE_STREAM_URL',
        'http://192.168.3.161:81/stream'  # 本地ESP32视频流地址（仅供开发测试）
    )
    
    # 快照URL（在云端中继和缓存都不可用时使用）
    DEVICE_SNAPSHOT_URL_TEMPLATE = os.getenv(
        'DEVICE_SNAPSHOT_URL',
        'http://192.168.3.161:81/stream?action=snapshot'  # 本地ESP32快照地址（仅供开发测试）
    )
    
    # 小程序客户端使用的快照URL
    # 生产环境建议直接配置为云端中继地址以提升性能
    CLIENT_SNAPSHOT_URL_TEMPLATE = os.getenv(
        'CLIENT_SNAPSHOT_URL',
        '/api/device/snapshot'  # 默认通过后端代理，支持权限检查
    )
    
    # 微信小程序配置    WECHAT_APP_ID = os.getenv('WECHAT_APP_ID', '')
    WECHAT_APP_SECRET = os.getenv('WECHAT_APP_SECRET', '')
    
    # 日志配置    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # 其他配置    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传16MB


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境必须设置强密钥
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("生产环境必须设置 SECRET_KEY 环境变量")


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# 根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
