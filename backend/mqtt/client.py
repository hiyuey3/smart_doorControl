"""使用 Flask-MQTT 扩展实现 MQTT 客户端"""
import json
import time
from datetime import datetime
from flask import current_app
from flask_mqtt import Mqtt
from app import db
from core.models import Log, Device


# 全局 Flask-MQTT 实例
mqtt = Mqtt()


def init_mqtt(app):
    """初始化 Flask-MQTT 扩展"""
    # 配置 MQTT 连接参数（从 Flask 配置读取）
    app.config['MQTT_BROKER_URL'] = app.config.get('MQTT_BROKER', 'mqtt.5i03.cn')
    app.config['MQTT_BROKER_PORT'] = app.config.get('MQTT_PORT', 1883)
    app.config['MQTT_USERNAME'] = app.config.get('MQTT_USERNAME', '')
    app.config['MQTT_PASSWORD'] = app.config.get('MQTT_PASSWORD', '')
    app.config['MQTT_CLIENT_ID'] = app.config.get('MQTT_CLIENT_ID', 'access_control_backend')
    app.config['MQTT_KEEPALIVE'] = 60
    app.config['MQTT_TLS_ENABLED'] = False
    
    # 初始化 MQTT 扩展
    mqtt.init_app(app)
    
    print(f"Flask-MQTT initialized with broker {app.config['MQTT_BROKER_URL']}:{app.config['MQTT_BROKER_PORT']}")


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    """MQTT 连接成功回调"""
    if rc == 0:
        print("[MQTT] OK: Connected to MQTT broker successfully!")
        
        # 订阅设备上行消息主题（与ESP32的topic_pub格式一致）
        # ESP32发布到: /iot/device/{mac}/up
        mqtt.subscribe('/iot/device/+/up', qos=1)
        print("   [OK] Subscribed to: /iot/device/+/up")
        
        # 订阅设备状态主题（用于监听掉电、遗嘱消息）
        # 设备离线时会发布遗嘱到此topic
        mqtt.subscribe('/iot/device/+/status', qos=1)
        print("   [OK] Subscribed to: /iot/device/+/status")
        
        # 兼容旧格式（如果有其他设备使用旧格式）
        mqtt.subscribe('access/control/event/+', qos=1)
        print("   [OK] Also subscribed to: access/control/event/+")
    else:
        print(f"[MQTT] FAIL: Failed to connect to MQTT broker (code: {rc})")


@mqtt.on_disconnect()
def handle_disconnect():
    """MQTT 断开连接回调"""
    print("[MQTT] WARN: Disconnected - attempting to reconnect...")


@mqtt.on_message()
def handle_message(client, userdata, message):
    """
    处理收到的 MQTT 消息
    
    支持的topic格式：
    1. /iot/device/{mac}/up  (ESP32新格式，mac无冒号，如 AABBCCDDEEFF)
    2. /iot/device/{mac}/status  (设备状态/遗嘱，关键离线通知)
    3. access/control/event/{mac}  (旧格式，mac带冒号)
    """
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode('utf-8'))
        print(f"Received MQTT message on {topic}: {payload}")
        
        # 解析MAC地址
        mac_address = None
        
        # 格式1: /iot/device/{mac}/up
        if topic.startswith('/iot/device/'):
            parts = topic.split('/')
            if len(parts) >= 4:
                mac_no_colon = parts[3]  # 获取无冒号的MAC，如 AABBCCDDEEFF
                # 转换为标准格式：AA:BB:CC:DD:EE:FF
                mac_address = ':'.join([mac_no_colon[i:i+2] for i in range(0, 12, 2)]).upper()
        
        # 格式3: access/control/event/{mac}
        elif topic.startswith('access/control/event/'):
            parts = topic.split('/')
            if len(parts) >= 4:
                mac_address = parts[-1].upper()
        
        if not mac_address:
            print(f"Invalid topic format: {topic}")
            return
        
        print(f"Extracted MAC address: {mac_address}")
        
        # 处理设备状态消息 (掉电/离线)        # /iot/device/{mac}/status 通常用于遗嘱或设备主动上报离线状态
        if '/status' in topic:
            device_status = payload.get('status', 'unknown')
            if device_status == 'offline':
                device = Device.query.filter_by(mac_address=mac_address).first()
                if device:
                    device.status = 'offline'
                    device.last_heartbeat = datetime.utcnow()
                    db.session.commit()
                    print(f"[MQTT] OK: Device {mac_address} marked as offline (LWT or status message)")
            return
        
        # 获取或查询设备（更新在线状态时需要）
        device = Device.query.filter_by(mac_address=mac_address).first()
        if not device:
            print(f"Device not found: {mac_address}, skipping status update")
        else:
            # 更新设备在线状态
            # 任何来自设备的消息都表示设备在线
            device.status = 'online'
            device.last_heartbeat = datetime.utcnow()
        
        # 处理不同类型的消息
        msg_type = payload.get('type', 'unknown')
        
        # 心跳包：更新设备状态
        if msg_type == 'heartbeat':
            if device:
                db.session.commit()
                print(f"Updated heartbeat for device: {mac_address}")
        
        # 硬件上报（STM32串口数据）
        elif msg_type == 'hw_report':
            cmd = payload.get('cmd')
            data = payload.get('data')
            print(f"Hardware report from {mac_address}: cmd={cmd}, data={data}")
            if device:
                db.session.commit()
            # TODO: 根据业务需求处理硬件上报
        
        # 通行事件
        elif msg_type == 'pass':
            event_id = payload.get('event_id', f"evt_{int(time.time())}")
            unlock_method = payload.get('method', 'fingerprint')
            
            # 检查日志是否已存在
            existing_log = Log.query.filter_by(event_id=event_id).first()
            if not existing_log:
                log_entry = Log(
                    event_id=event_id,
                    mac_address=mac_address,
                    unlock_method=unlock_method
                )
                db.session.add(log_entry)
                db.session.commit()
                print(f"New access event logged: {event_id}")
            else:
                # 更新已有记录
                existing_log.unlock_method = unlock_method
                db.session.commit()
                print(f"Updated existing log: {event_id}")
        
        # 对于其他消息类型，仍需提交设备状态更新
        else:
            if device:
                db.session.commit()
            print(f"Message type '{msg_type}' processed for device: {mac_address}")
        
    except Exception as e:
        print(f"Error processing MQTT message: {str(e)}")
        import traceback
        traceback.print_exc()


def publish_command(mac_address, command):
    """
    发布控制命令到设备
    
    注意：ESP32订阅的topic格式为 /iot/device/{mac}/down
    其中MAC地址需要去掉冒号，如 AABBCCDDEEFF
    """
    try:
        # 移除MAC地址中的冒号和连字符，统一为大写
        mac_clean = mac_address.replace(':', '').replace('-', '').upper()
        
        # Topic格式与ESP32订阅格式一致
        topic = f"/iot/device/{mac_clean}/down"
        payload = json.dumps(command)
        
        # 检查 MQTT 连接状态
        if not mqtt.client or not mqtt.client.is_connected():
            msg = f"[MQTT] FAIL: Not connected! Topic: {topic}"
            print(msg)
            try:
                current_app.logger.error(msg)
            except:
                pass
            return False
        
        mqtt.publish(topic, payload, qos=1)
        msg = f"[MQTT] OK: Published to {topic}"
        print(msg)
        try:
            current_app.logger.info(msg)
        except:
            pass
        return True
    except Exception as e:
        msg = f"[MQTT] FAIL: Publish error: {str(e)}"
        print(msg)
        try:
            current_app.logger.error(msg)
        except:
            pass
        import traceback
        traceback.print_exc()
        return False