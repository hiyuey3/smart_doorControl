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

# 保存 Flask app 实例，供后台 MQTT 回调使用（因为回调通常在独立线程）
flask_app = None


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
    # 保存应用实例，供回调使用
    global flask_app
    flask_app = app

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
def _handle_message_impl(client, userdata, message):
    """内部实现：假定已在 Flask 应用上下文中运行"""
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode('utf-8'))
        print(f"Received MQTT message on {topic}: {payload}")

        # 从 topic 提取设备 MAC
        mac_address = None

        # 新主题格式：/iot/device/{mac}/up 或 /iot/device/{mac}/status
        if topic.startswith('/iot/device/'):
            parts = topic.split('/')
            if len(parts) >= 4:
                mac_no_colon = parts[3]  # 例如 AABBCCDDEEFF
                # 统一转成 AA:BB:CC:DD:EE:FF
                mac_address = ':'.join([mac_no_colon[i:i+2] for i in range(0, 12, 2)]).upper()

        # 兼容旧主题格式：access/control/event/{mac}
        elif topic.startswith('access/control/event/'):
            parts = topic.split('/')
            if len(parts) >= 4:
                mac_address = parts[-1].upper()

        if not mac_address:
            print(f"Invalid topic format: {topic}")
            return

        print(f"Extracted MAC address: {mac_address}")

        # 设备上报里可能使用不同字段名，逐个兜底读取
        reported_ip = (
            payload.get('ip_address')
            or payload.get('ip')
            or payload.get('local_ip')
            or (payload.get('network') or {}).get('ip')
        )

        # 状态主题主要处理离线通知（含 LWT）
        if '/status' in topic:
            device_status = payload.get('status', 'unknown')
            if device_status == 'offline':
                device = Device.query.filter_by(mac_address=mac_address).first()
                if device:
                    device.status = 'offline'
                    device.last_heartbeat = datetime.utcnow()
                    db.session.commit()
                    print(f"[MQTT] OK: Device {mac_address} marked as offline from LWT or status message")
            return

        # 更新设备在线状态
        device = Device.query.filter_by(mac_address=mac_address).first()
        if not device:
            print(f"Device not found: {mac_address}, skipping status update")
        else:
            # 判断是否离线恢复
            was_offline = device.status != 'online'
            device.status = 'online'
            device.last_heartbeat = datetime.utcnow()
            if reported_ip:
                device.ip_address = reported_ip
            # 设备刚上线时，用 retained online 覆盖 broker 里的离线状态
            if was_offline:
                publish_device_status(mac_address, 'online', retain=True)
                print(f"[MQTT] Published retained 'online' status for {mac_address}")

        # 处理不同类型的消息
        msg_type = payload.get('type', 'unknown')

        # 心跳包：更新设备状态
        if msg_type == 'heartbeat':
            if device:
                db.session.commit()
                # 读取设备时间戳（如果有）
                device_timestamp = payload.get('timestamp', 'N/A')
                server_timestamp = datetime.utcnow().isoformat()
                print(f"[MQTT] Heartbeat from {mac_address} | "
                      f"Device time: {device_timestamp} | "
                      f"Server time: {server_timestamp} | "
                      f"Last heartbeat: {device.last_heartbeat} | "
                      f"IP: {device.ip_address or 'N/A'}")

        # 硬件上报（STM32串口数据）
        elif msg_type == 'hw_report':
            cmd = payload.get('cmd')
            data = payload.get('data')
            print(f"Hardware report from {mac_address}: cmd={cmd}, data={data}")
            if device:
                db.session.commit()

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
                existing_log.unlock_method = unlock_method
                db.session.commit()
                print(f"Updated existing log: {event_id}")

        else:
            if device:
                db.session.commit()
            print(f"Message type '{msg_type}' processed for device: {mac_address}")

    except Exception as e:
        print(f"Error processing MQTT message: {str(e)}")
        import traceback
        traceback.print_exc()


@mqtt.on_message()
def handle_message(client, userdata, message):
    """外部回调：在没有 Flask 上下文时推入应用上下文再调用实现。"""
    if flask_app:
        with flask_app.app_context():
            _handle_message_impl(client, userdata, message)
    else:
        try:
            # 尝试使用 current_app
            with current_app.app_context():
                _handle_message_impl(client, userdata, message)
        except Exception:
            print("[MQTT] ERROR: no Flask app context available for handling message")


def publish_command(mac_address, command):
    """
    发布控制命令到设备

    ESP32 订阅主题为 /iot/device/{mac}/down，
    所以这里会把 MAC 转成无分隔符格式（如 AABBCCDDEEFF）。
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


def publish_device_status(mac_address, status, retain=True):
    """
    发布设备状态消息（支持 retained 标志）
    
    Args:
        mac_address: 设备 MAC 地址（格式：AA:BB:CC:DD:EE:FF）
        status: 状态字符串（'online' 或 'offline'）
        retain: 是否为 retained 消息（默认 True）
    
    说明：
        - 设备上线时发布 retained "online" 覆盖 LWT
        - 设备断开时发布 retained "offline"
        - broker 会保存 retained 消息，后续订阅者可立即拿到最新状态
    """
    try:
        # 移除 MAC 地址中的冒号，转换为 ESP32 格式
        mac_clean = mac_address.replace(':', '').replace('-', '').upper()
        
        # 发布到设备状态主题
        topic = f"/iot/device/{mac_clean}/status"
        payload = json.dumps({
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 检查 MQTT 连接状态
        if not mqtt.client or not mqtt.client.is_connected():
            msg = f"[MQTT] FAIL: Not connected! Cannot publish status to {topic}"
            print(msg)
            try:
                current_app.logger.error(msg)
            except:
                pass
            return False
        
        # 发布消息（QoS=1, retain 根据参数决定）
        mqtt.publish(topic, payload, qos=1, retain=retain)
        msg = f"[MQTT] OK: Published {'retained' if retain else 'non-retained'} status '{status}' to {topic}"
        print(msg)
        try:
            current_app.logger.info(msg)
        except:
            pass
        return True
    except Exception as e:
        msg = f"[MQTT] FAIL: publish_device_status error: {str(e)}"
        print(msg)
        try:
            current_app.logger.error(msg)
        except:
            pass
        import traceback
        traceback.print_exc()
        return False