"""
Flask 配置文件示例
复制此文件为 config.py 并修改相关配置
"""
import os

class Config:
    """基础配置"""
    
    # 数据库配置    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///instance/access_control.db'
    )
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
    
    # 实时视频流配置    # 注意：这里配置的是ESP32设备的实际IP和端口
    # Flask后端会作为反向代理，转发ESP32的视频流给小程序
    
    # 方式1：单设备静态配置（适合开发测试）
    DEVICE_STREAM_URL_TEMPLATE = os.getenv(
        'DEVICE_STREAM_URL',
        'http://192.168.3.161:81/stream'
    )
    
    DEVICE_SNAPSHOT_URL_TEMPLATE = os.getenv(
        'DEVICE_SNAPSHOT_URL',
        'http://192.168.3.161:81/stream?action=snapshot'
    )
    
    # 方式2：多设备动态配置（生产环境推荐）
    # 在Device表中添加stream_url字段，每个设备配置独立的视频流地址
    # 示例SQL：ALTER TABLE devices ADD COLUMN stream_url VARCHAR(255);
    # 然后在代码中使用：device.stream_url
    
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
