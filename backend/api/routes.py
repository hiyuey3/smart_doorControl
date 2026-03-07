from flask import jsonify, request, current_app, g, Response, stream_with_context
from app import db
from core.models import Log, Device, User, UserDevicePermission, DeviceApplication
from mqtt import publish_command
from auth import token_required, permission_helper
from core.database import db_helper
from shared import response_helper, log_helper
from . import bp
import time
import requests
import jwt
import re
from datetime import datetime, timedelta
import os

# MAC 地址正则（全局编译，避免重复）
MAC_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')


def normalize_mac(mac_raw):
    """
    统一 MAC 地址格式。

    支持输入：AA:BB:CC:DD:EE:FF / AA-BB-CC-DD-EE-FF / AABBCCDDEEFF。
    返回标准格式：AA:BB:CC:DD:EE:FF。
    """
    if not mac_raw:
        return None, '缺少 MAC 地址'
    
    # 移除所有分隔符，转为大写
    mac_clean = mac_raw.replace(':', '').replace('-', '').replace(' ', '').upper()
    
    # 验证长度
    if len(mac_clean) != 12:
        return None, f'MAC 地址长度无效（期望 12 位，实际 {len(mac_clean)} 位）'
    
    # 验证是否为16进制字符
    if not all(c in '0123456789ABCDEF' for c in mac_clean):
        return None, 'MAC 地址包含非法字符'
    
    # 转换为标准格式（带冒号）
    mac_standard = ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)])
    
    return mac_standard, None


# 路由设计：按资源收敛接口，按角色过滤数据，敏感动作默认鉴权。
# 工具函数：减少重复校验与格式处理。
def _validate_mac_address(mac_address):
    """
    验证 MAC 地址格式。
    返回：(是否有效, 错误响应)
    """
    if not mac_address or not mac_address.strip():
        return False, response_helper.bad_request('MAC 地址不能为空', 'MAC_ADDRESS_REQUIRED')
    
    mac = mac_address.strip().upper()
    if not MAC_PATTERN.match(mac):
        return False, response_helper.bad_request('MAC 地址格式无效', 'INVALID_MAC_FORMAT')
    
    return True, None


def _normalize_mac_address(mac_address):
    """
    归一化 MAC 地址。
    支持输入格式：
    - AA:BB:CC:DD:EE:FF
    - AA-BB-CC-DD-EE-FF
    - AABBCCDDEEFF
    返回标准格式：AA:BB:CC:DD:EE:FF
    """
    if not mac_address:
        return None

    mac_clean = str(mac_address).strip().replace(':', '').replace('-', '').upper()
    if len(mac_clean) != 12 or not re.fullmatch(r'[0-9A-F]{12}', mac_clean):
        return None

    return ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)])


# 配置和授权函数


def _build_system_config():
    """
    统一返回系统基础配置。
    """
    return {
        'app': {
            'name': 'ESP32门禁系统',
            'version': '3.0.0',
            'description': '智慧校园门禁系统后端 V3.0'
        },
        'api': {
            'timeout': 10000,
            'debug': True,
            'retry_count': 3
        },
        'features': {
            'fingerprint': True,
            'nfc': True,
            'remote_unlock': True,
            'capture_image': True,
            'activity_log': True
        },
        'security': {
            'require_login': True,
            'token_refresh_interval': 3600
        }
    }


def _issue_jwt(user):
    """
    统一 JWT 签发逻辑。
    """
    jwt_expiration_seconds = current_app.config.get('JWT_EXPIRATION', 7 * 24 * 3600)
    exp_time = datetime.utcnow() + timedelta(seconds=jwt_expiration_seconds)

    payload = {
        'user_id': user.id,
        'role': user.role,
        'exp': exp_time,
        'iat': datetime.utcnow()
    }

    secret_key = current_app.config.get('SECRET_KEY')
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token, jwt_expiration_seconds


def _wechat_code_to_openid(code):
    """
    用微信 code 换 openid。
    """
    wx_appid = current_app.config.get('WX_APPID')
    wx_appsecret = current_app.config.get('WX_APPSECRET')

    if not wx_appid or not wx_appsecret:
        return None, ('WX_CONFIG_MISSING', '微信配置缺失')

    wechat_api_url = 'https://api.weixin.qq.com/sns/jscode2session'
    params = {
        'appid': wx_appid,
        'secret': wx_appsecret,
        'js_code': code,
        'grant_type': 'authorization_code'
    }

    try:
        response = requests.get(wechat_api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return None, ('WECHAT_API_ERROR', f'微信接口请求失败: {str(e)}')
    except ValueError:
        return None, ('INVALID_RESPONSE', '微信响应格式错误')

    if 'errcode' in data:
        errcode = data.get('errcode')
        errmsg = data.get('errmsg', 'Unknown error')
        return None, (f'WX_ERR_{errcode}', f'WeChat authorization failed: {errmsg}')

    openid = data.get('openid')
    if not openid:
        return None, ('NO_OPENID', 'No openid in WeChat response')

    return openid, None


# 0) 系统配置接口（公开，不需要认证）
# GET /api/config
@bp.route('/config', methods=['GET'])
def get_system_config():
    """
    获取系统配置信息（公开接口）。

    该接口用于前端启动阶段拉取基础配置。
    """
    return response_helper.success(
        data=_build_system_config(),
        message='获取配置成功'
    )


# 1) 统一登录入口
# POST /api/login
@bp.route('/login', methods=['POST'])
def login():
    """
    统一登录入口。
    通过 login_type 区分微信登录和账号密码登录，前端统一调用一个接口。
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            'success': False,
            'message': 'Invalid JSON body',
            'error_code': 'INVALID_JSON'
        }), 400

    login_type = (data.get('login_type') or '').strip().lower()

    # 账号密码登录
    if login_type == 'password':
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        if not username:
            return jsonify({'success': False, 'message': '请输入账号', 'error_code': 'MISSING_USERNAME'}), 400
        if not password:
            return jsonify({'success': False, 'message': '请输入密码', 'error_code': 'MISSING_PASSWORD'}), 400

        user, error = db_helper.get_by_filter(User, username=username)
        if error:
            return response_helper.unauthorized('登录失败')
        
        if user:
            if not user.check_password(password):
                return response_helper.unauthorized('密码错误')
        else:
            user = User(username=username, name=username, role='student')
            user.set_password(password)
            user.generate_token()
            user, error = db_helper.add_and_commit(user)
            if error:
                return response_helper.internal_error('创建用户失败')

        token, expires_in = _issue_jwt(user)
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'expires_in': expires_in,
                'user': user.to_dict()
            },
            'message': '登录成功'
        }), 200

    # 微信登录流程
    if login_type == 'wechat':
        code = (data.get('code') or '').strip()
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        if not code:
            return jsonify({'success': False, 'message': 'Missing code parameter', 'error_code': 'MISSING_CODE'}), 400

        openid, err = _wechat_code_to_openid(code)
        if err:
            err_code, err_msg = err
            status = 401 if err_code.startswith('WX_ERR_') else 500
            return jsonify({'success': False, 'message': err_msg, 'error_code': err_code}), status

        # 先看这个 openid 是否已经绑定过账号
        user = User.query.filter_by(openid=openid).first()

        # 如果没绑定过，再尝试把微信绑定到现有账号
        if not user and username and password:
            existing_user = User.query.filter_by(username=username).first()

            if not existing_user:
                return jsonify({
                    'success': False,
                    'message': '账号不存在，无法绑定，请先账号密码登录创建账号',
                    'error_code': 'BIND_USER_NOT_FOUND'
                }), 404

            if not existing_user.check_password(password):
                return jsonify({
                    'success': False,
                    'message': '账号密码错误，微信绑定失败',
                    'error_code': 'BIND_PASSWORD_INCORRECT'
                }), 401

            if existing_user.openid and existing_user.openid != openid:
                return jsonify({
                    'success': False,
                    'message': '该账号已绑定其他微信，请联系管理员处理',
                    'error_code': 'BIND_CONFLICT'
                }), 409

            existing_user.openid = openid
            user = existing_user
            db.session.commit()

        # 还找不到就自动创建一个微信用户
        if not user:
            user = User(
                openid=openid,
                name='微信新用户',
                role='student'
            )
            db.session.add(user)
            db.session.commit()

        token, expires_in = _issue_jwt(user)
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'expires_in': expires_in,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'openid': user.openid,
                    'name': user.name,
                    'role': user.role,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }
            },
            'message': '微信登录成功'
        }), 200

    return jsonify({
        'success': False,
        'message': 'login_type 必须为 wechat 或 password',
        'error_code': 'INVALID_LOGIN_TYPE'
    }), 400


# 个人资源中心
# GET /api/user
# PUT /api/user
@bp.route('/user', methods=['GET'])
@token_required
def get_user_resource():
    """
    获取当前用户聚合资源：用户信息 + 微信绑定状态 + 系统配置。
    """
    current_user = g.current_user

    return jsonify({
        'success': True,
        'data': {
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'name': current_user.name,
                'role': current_user.role,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'wechat': {
                'is_bound': bool(current_user.openid),
                'openid': current_user.openid
            },
            'config': _build_system_config()
        }
    }), 200


@bp.route('/user', methods=['PUT'])
@token_required
def update_user_resource():
    """
    当前用户资料修改入口。
    通过 action 区分微信绑定、资料更新和密码修改。
    """
    data = request.get_json(silent=True)
    if data is None:
        return response_helper.bad_request('Invalid JSON body', 'INVALID_JSON')

    action = (data.get('action') or '').strip()
    current_user = g.current_user

    # 绑定微信
    if action == 'bind_wechat':
        # 已经绑定过就直接返回
        if current_user.openid:
            return response_helper.bad_request('当前账号已绑定微信', 'ALREADY_BOUND')

        # 读取并校验 wx.login() 返回的 code
        code = (data.get('code') or '').strip()
        if not code:
            return response_helper.bad_request('Missing code parameter', 'MISSING_CODE')

        # 用 code 换 openid
        openid, err = _wechat_code_to_openid(code)
        if err:
            err_code, err_msg = err
            status = 401 if err_code.startswith('WX_ERR_') else 500
            return response_helper.error(err_msg, err_code, status)

        # 同一个 openid 只能对应一个账号
        occupied, _ = db_helper.get_by_filter(
            User, 
            **{'openid': openid}
        )
        if occupied and occupied.id != current_user.id:
            return response_helper.conflict('该微信已绑定其他账号', 'OPENID_OCCUPIED')

        # 写入绑定关系
        _, error = db_helper.update_and_commit(current_user, openid=openid)
        if error:
            return response_helper.internal_error(f'绑定失败: {error}')
        
        # 返回最新绑定状态，前端可直接刷新展示
        return response_helper.success(
            data={
                'is_bound': True,
                'openid': openid
            },
            message='微信绑定成功'
        )

    # 解绑微信
    if action == 'unbind_wechat':
        # 原本就没绑定时直接返回
        if not current_user.openid:
            return response_helper.bad_request('当前账号未绑定微信', 'NOT_BOUND')

        # 清除 openid
        _, error = db_helper.update_and_commit(current_user, openid=None)
        if error:
            return response_helper.internal_error(f'解绑失败: {error}')
        
        # 返回解绑后的状态
        return response_helper.success(
            data={
                'is_bound': False,
                'openid': None
            },
            message='微信解绑成功'
        )

    # 更新基础资料
    if action == 'update_info':
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return response_helper.bad_request('name 不能为空', 'MISSING_NAME')

        _, error = db_helper.update_and_commit(current_user, name=new_name)
        if error:
            return response_helper.internal_error(f'更新失败: {error}')
        
        return response_helper.success(
            data={'name': current_user.name},
            message='资料更新成功'
        )

    # 修改密码
    if action == 'change_password':
        old_password = (data.get('old_password') or '').strip()
        new_password = (data.get('new_password') or '').strip()

        if not new_password:
            return response_helper.bad_request('新密码不能为空', 'MISSING_NEW_PASSWORD')

        if len(new_password) < 6:
            return response_helper.bad_request('新密码长度不能少于6位', 'WEAK_NEW_PASSWORD')

        # 有旧密码时要先校验
        if current_user.password:
            if not old_password:
                return response_helper.bad_request('请输入旧密码', 'MISSING_OLD_PASSWORD')
            if not current_user.check_password(old_password):
                return response_helper.bad_request('旧密码错误', 'INVALID_OLD_PASSWORD')

        current_user.set_password(new_password)
        _, error = db_helper.commit_changes()
        if error:
            return response_helper.internal_error(f'密码修改失败: {error}')
        
        return response_helper.success(message='密码修改成功')

    return response_helper.bad_request('不支持的 action', 'INVALID_ACTION')


# 设备管控
# GET /api/devices
# POST /api/devices/<mac_address>/unlock
@bp.route('/devices', methods=['GET'])
@token_required
def get_devices():
    """
    设备列表接口。
    admin 返回全部设备，普通用户只返回已授权设备。
    """
    current_user = g.current_user

    try:
        # 管理员看全量设备
        if current_user.role == 'admin':
            devices, error = db_helper.get_all(Device, order_by=Device.mac_address.asc())
            if error:
                return response_helper.internal_error(f'Query devices failed: {error}')
        # 非管理员只看自己已批准的设备
        else:
            devices = (
                db.session.query(Device)
                .join(UserDevicePermission, UserDevicePermission.device_mac == Device.mac_address)
                .filter(
                    UserDevicePermission.user_id == current_user.id,
                    UserDevicePermission.status == 'approved'
                )
                .order_by(Device.mac_address.asc())
                .all()
            )

        # 返回设备列表
        return response_helper.list_response(
            items=[d.to_dict() for d in devices],
            message='设备列表查询成功'
        )
    except Exception as e:
        return response_helper.internal_error(f'Get devices failed: {str(e)}')


@bp.route('/devices/<string:mac_address>/unlock', methods=['POST'])
@token_required
def unlock_device(mac_address):
    """
    RESTful 远程开锁接口。

    安全策略（BOLA 二次校验）：
    - admin 可直接操作任意设备。
    - 非 admin 必须验证 UserDevicePermission(user_id, device_mac) 存在。

    设备标识走 URL，鉴权通过后再下发 MQTT 并写日志。
    """
    current_user = g.current_user

    # 标准化 MAC 地址格式（支持带冒号和不带冒号的输入）
    mac_normalized, error = normalize_mac(mac_address)
    if error:
        return response_helper.bad_request(f'MAC 地址格式错误: {error}')
    
    # 使用标准化后的 MAC 地址
    mac_address = mac_normalized

    # 使用工具类进行权限检查
    error_result, error_code = permission_helper.check_device_access(current_user, mac_address)
    if error_result:
        return response_helper.error(error_result['message'], error_result['error_code'], error_code)

    # 使用工具类获取设备
    device, error = db_helper.get_by_filter(Device, mac_address=mac_address)
    if error:
        return response_helper.internal_error(f'Query device failed: {error}')
    if not device:
        return response_helper.not_found('Device not found', 'DEVICE_NOT_FOUND')

    try:
        command = {
            'cmd': 'open',
            'user_id': current_user.id,
            'timestamp': int(time.time())
        }

        success = publish_command(mac_address, command)
        if not success:
            return response_helper.error('Failed to publish MQTT command', 'MQTT_ERROR', 500)

        # 使用工具类记录开锁日志
        log_entry, log_error = log_helper.create_remote_unlock_log(
            mac_address=mac_address,
            user_id=current_user.id,
            device_name=device.name or device.room_number
        )
        
        if log_error:
            current_app.logger.error(f'Failed to create log: {log_error}')

        return response_helper.success(
            data={
                'device_name': device.name or device.room_number,
                'device_mac': mac_address
            },
            message='Unlock command sent successfully'
        )

    except Exception as e:
        return response_helper.error(f'Unlock failed: {str(e)}', 'UNLOCK_ERROR', 500)


@bp.route('/devices/bind', methods=['POST'])
@token_required
def bind_device():
    """用户绑定设备接口。"""
    current_user = g.current_user
    data = request.get_json()
    
    if not data:
        return response_helper.bad_request('请求体无效', 'INVALID_REQUEST')
    
    mac_address = (data.get('mac_address') or '').strip().upper()
    device_name = (data.get('device_name') or '').strip()
    
    # 验证 MAC 地址
    valid, error_resp = _validate_mac_address(mac_address)
    if not valid:
        return error_resp
    
    try:
        # 检查设备是否已存在
        device, error = db_helper.get_by_filter(Device, mac_address=mac_address)
        if not device:
            device = Device(
                mac_address=mac_address,
                name=device_name or f'设备_{mac_address[-8:]}',
                status='offline'
            )
            device, error = db_helper.add_and_commit(device)
            if error:
                return response_helper.internal_error(f'创建设备失败: {error}')
        
        # 检查用户是否已绑定
        existing_perm, _ = db_helper.get_by_filter(
            UserDevicePermission,
            user_id=current_user.id,
            device_mac=mac_address
        )
        if existing_perm:
            return response_helper.bad_request('已绑定该设备', 'ALREADY_BOUND')
        
        # 创建权限记录
        permission = UserDevicePermission(
            user_id=current_user.id,
            device_mac=mac_address,
            status='approved'
        )
        permission, error = db_helper.add_and_commit(permission)
        if error:
            return response_helper.internal_error(f'绑定失败: {error}')
        
        return response_helper.success(
            data={'device_mac': mac_address, 'device_name': device.name},
            message='设备绑定成功'
        )
    except Exception as e:
        current_app.logger.error(f'Bind device error: {e}')
        return response_helper.internal_error(f'绑定失败: {str(e)}')


# 3.1) 设备申请-审批工作流
# POST /api/user/apply_device - 学生申请绑定设备
# GET /api/user/applications - 查询自己的申请记录
# GET /api/admin/applications - 管理员查看所有待审批申请
# PUT /api/admin/applications/<id> - 管理员审批申请
@bp.route('/user/apply_device', methods=['POST'])
@token_required
def apply_device():
    """学生申请绑定设备。"""
    current_user = g.current_user
    data = request.get_json()
    
    if not data:
        return response_helper.bad_request('请求体无效', 'INVALID_REQUEST')
    
    mac_address = (data.get('mac_address') or '').strip().upper()
    reason = (data.get('reason') or '').strip()
    
    # 验证 MAC 地址
    valid, error_resp = _validate_mac_address(mac_address)
    if not valid:
        return error_resp
    
    try:
        # 检查设备是否存在，不存在则创建
        device, error = db_helper.get_by_filter(Device, mac_address=mac_address)
        if not device:
            device = Device(
                mac_address=mac_address,
                name=f'设备_{mac_address[-8:]}',
                status='offline'
            )
            device, error = db_helper.add_and_commit(device)
            if error:
                return response_helper.internal_error(f'创建设备失败: {error}')
        
        # 检查是否已有权限
        existing_perm, _ = db_helper.get_by_filter(
            UserDevicePermission,
            user_id=current_user.id,
            device_mac=mac_address
        )
        if existing_perm:
            return response_helper.bad_request('已有该设备访问权限', 'ALREADY_BOUND')
        
        # 检查是否有待审批申请
        pending_app, _ = db_helper.get_by_filter(
            DeviceApplication,
            user_id=current_user.id,
            device_mac=mac_address,
            status='pending'
        )
        if pending_app:
            return response_helper.bad_request('申请审批中，请勿重复提交', 'DUPLICATE_APPLICATION')
        
        # 创建申请
        application = DeviceApplication(
            user_id=current_user.id,
            device_mac=mac_address,
            reason=reason or '申请绑定设备',
            status='pending'
        )
        application, error = db_helper.add_and_commit(application)
        if error:
            return response_helper.internal_error(f'提交申请失败: {error}')
        
        return response_helper.success(
            data={'application_id': application.id, 'status': 'pending'},
            message='申请已提交，等待管理员审批'
        )
    except Exception as e:
        current_app.logger.error(f'Apply device error: {e}')
        return response_helper.internal_error(f'申请失败: {str(e)}')


@bp.route('/user/devices', methods=['GET'])
@token_required
def get_user_approved_devices():
    """
    获取当前用户所有已批准的设备列表。
    
    需要的 API 之一：用于前端展示用户可控制的所有设备。
    
    返回格式（Array of Objects）：
    {
      "success": true,
      "data": [
        {
          "mac_address": "AA:BB:CC:DD:EE:FF",
          "name": "教室1门禁",
          "room_number": "101",
          "status": "online",          # 设备实时在线状态
          "last_heartbeat": "2026-03-01T10:30:00",
          "created_at": "2026-02-01T00:00:00"
        },
        {
          "mac_address": "AA:BB:CC:DD:EE:01",
          "name": "宿舍楼门禁",
          "room_number": "宿舍楼",
          "status": "offline",
          "last_heartbeat": null,
          "created_at": "2026-02-01T00:00:00"
        }
      ],
      "count": 2
    }
    """
    current_user = g.current_user
    
    try:
        # 以权限表为主做左连接，避免设备主表缺记录时列表被内连接过滤为空
        permission_rows = (
            db.session.query(UserDevicePermission, Device)
            .outerjoin(Device, UserDevicePermission.device_mac == Device.mac_address)
            .filter(
                UserDevicePermission.user_id == current_user.id,
                UserDevicePermission.status == 'approved'
            )
            .order_by(UserDevicePermission.device_mac.asc())
            .all()
        )

        items = []
        for perm, device in permission_rows:
            if device:
                items.append(device.to_dict())
            else:
                mac_no_colon = (perm.device_mac or '').replace(':', '').replace('-', '').upper()
                items.append({
                    'mac_address': perm.device_mac,
                    'name': f'设备_{mac_no_colon[-8:]}' if mac_no_colon else '设备_Unknown',
                    'room_number': None,
                    'status': 'offline',
                    'last_heartbeat': None,
                    'created_at': perm.created_at.isoformat() if perm.created_at else None
                })

        return response_helper.list_response(
            items=items,
            message='设备列表查询成功'
        )
        
    except Exception as e:
        current_app.logger.error(f'Get user devices error: {e}')
        return response_helper.internal_error(f'Failed to get your devices: {str(e)}')


@bp.route('/user/applications', methods=['GET'])
@token_required
def get_user_applications():
    """
    查询当前用户的申请记录。
    
    返回：
    - 当前用户提交的所有申请记录（待审批、已批准、已拒绝）
    """
    current_user = g.current_user
    
    try:
        applications, error = db_helper.get_all(
            DeviceApplication,
            order_by=DeviceApplication.created_at.desc(),
            user_id=current_user.id
        )
        if error:
            return response_helper.internal_error(f'Query applications failed: {error}')
        
        return response_helper.list_response(
            items=[app.to_dict() for app in (applications or [])],
            message='申请记录查询成功'
        )
        
    except Exception as e:
        current_app.logger.error(f'Get user applications error: {e}')
        return response_helper.internal_error(f'Failed to get applications: {str(e)}')


@bp.route('/admin/applications', methods=['GET'])
@token_required
def get_admin_applications():
    """
    管理员查看所有待审批申请。
    
    权限要求：
    - 仅 admin 角色可访问
    
    返回：
    - 所有 status='pending' 的申请记录
    """
    current_user = g.current_user
    
    # 权限检查
    error = permission_helper.require_admin(current_user)
    if error:
        return response_helper.error(error[0]['message'], error[0]['error_code'], error[1])
    
    try:
        # 获取状态筛选参数
        status = request.args.get('status', 'pending')
        
        filters = {}
        if status:
            filters['status'] = status
        
        applications, error = db_helper.get_all(
            DeviceApplication,
            order_by=DeviceApplication.created_at.desc(),
            **filters
        )
        if error:
            return response_helper.internal_error(f'Query applications failed: {error}')
        
        return response_helper.list_response(
            items=[app.to_dict() for app in (applications or [])],
            message='申请记录查询成功'
        )
        
    except Exception as e:
        current_app.logger.error(f'Get admin applications error: {e}')
        return response_helper.internal_error(f'Failed to get applications: {str(e)}')


@bp.route('/admin/applications/<int:application_id>', methods=['PUT'])
@token_required
def review_application(application_id):
    """
    管理员审批申请。
    
    权限要求：
    - 仅 admin 角色可访问
    
    请求参数：
    - action: 'approve' 或 'reject'
    - comment: 审批备注（可选）
    
    业务逻辑：
    - approve: 创建 UserDevicePermission 记录，更新申请状态为 approved
    - reject: 仅更新申请状态为 rejected
    """
    current_user = g.current_user
    
    current_user = g.current_user
    
    # 权限检查
    error = permission_helper.require_admin(current_user)
    if error:
        return response_helper.error(error[0]['message'], error[0]['error_code'], error[1])
    
    data = request.get_json()
    if not data:
        return response_helper.bad_request('Request body is required', 'INVALID_REQUEST')
    
    action = data.get('action', '').lower()
    comment = data.get('comment', '').strip()
    
    if action not in ['approve', 'reject']:
        return response_helper.bad_request('Invalid action. Must be "approve" or "reject"', 'INVALID_ACTION')
    
    try:
        # 查找申请记录
        application, error = db_helper.get_by_id(DeviceApplication, application_id)
        if error:
            return response_helper.internal_error(f'Query application failed: {error}')
        if not application:
            return response_helper.not_found('Application not found', 'APPLICATION_NOT_FOUND')
        
        # 检查申请状态
        if application.status != 'pending':
            return response_helper.bad_request(f'Application already {application.status}', 'INVALID_STATUS')
        
        # 处理审批
        if action == 'approve':
            # 创建权限记录（必须设置 status='approved'）
            permission = UserDevicePermission(
                user_id=application.user_id,
                device_mac=application.device_mac,
                status='approved'
            )
            permission, error = db_helper.add_and_commit(permission)
            if error:
                return response_helper.internal_error(f'Create permission failed: {error}')
            
            # 更新申请状态
            application.status = 'approved'
            application.admin_comment = comment if comment else '已批准'
            application.reviewed_by = current_user.id
            application.reviewed_at = datetime.utcnow()
            
            application, error = db_helper.update_and_commit(
                application,
                status='approved',
                admin_comment=application.admin_comment,
                reviewed_by=current_user.id,
                reviewed_at=application.reviewed_at
            )
            if error:
                return response_helper.internal_error(f'Update application failed: {error}')
            
            # 【钩子位置】触发 MQTT 指令：将用户的开锁凭证同步到硬件侧
            # 调用方式：
            #   mqtt_command = {
            #       'cmd': 'grant_user_access',
            #       'user_id': application.user_id,
            #       'device_mac': application.device_mac,
            #       'timestamp': int(time.time())
            #   }
            #   publish_command(application.device_mac, mqtt_command)
            
            current_app.logger.info(f'Admin {current_user.id} approved device access for User {application.user_id} -> Device {application.device_mac}')
            
            return response_helper.success(
                data=application.to_dict(),
                message='Application approved successfully. User can now access the device.'
            )
            
        else:  # reject
            application.status = 'rejected'
            application.admin_comment = comment if comment else '已拒绝'
            application.reviewed_by = current_user.id
            application.reviewed_at = datetime.utcnow()
            
            application, error = db_helper.update_and_commit(
                application,
                status='rejected',
                admin_comment=application.admin_comment,
                reviewed_by=current_user.id,
                reviewed_at=application.reviewed_at
            )
            if error:
                return response_helper.internal_error(f'Update application failed: {error}')
            
            current_app.logger.info(f'Admin {current_user.id} rejected device access for User {application.user_id} -> Device {application.device_mac}')
            
            return response_helper.success(
                data=application.to_dict(),
                message='Application rejected'
            )
        
    except Exception as e:
        current_app.logger.error(f'Review application error: {e}')
        return response_helper.internal_error(f'Failed to review application: {str(e)}')


# 安全审计
# GET /api/logs
@bp.route('/logs', methods=['GET'])
@token_required
def get_logs():
    """
    统一日志查询接口（RBAC 动态过滤）。

    admin 查看全量；普通用户仅查看本人相关日志。
    """
    current_user = g.current_user
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    try:
        # 管理员查看全量日志
        if current_user.role == 'admin':
            query = Log.query
        # 普通用户只看和自己相关的日志
        else:
            # 先取出当前用户有权限的设备列表
            permitted_macs_query = (
                db.session.query(UserDevicePermission.device_mac)
                .filter(UserDevicePermission.user_id == current_user.id)
            )

            # 过滤本人操作日志，以及本人有权限设备的日志
            query = Log.query.filter(
                (Log.user_id == current_user.id) | 
                (Log.mac_address.in_(permitted_macs_query))
            )

        pagination = query.order_by(Log.create_time.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        logs = [log.to_dict() for log in pagination.items]

        return response_helper.paginated(
            items=logs,
            page=page,
            per_page=per_page,
            total=pagination.total,
            message='日志查询成功'
        )
    except Exception as e:
        current_app.logger.error(f'Get logs error: {e}')
        return response_helper.internal_error(f'Failed to get logs: {str(e)}')


# 宿管管理
# GET /api/users
# POST /api/users
@bp.route('/users', methods=['GET', 'POST'])
@token_required
def users_admin():
    """
    宿管管理入口，仅 admin 可访问。
    GET 拉取用户列表，POST 处理创建用户和强制解绑微信。
    """
    # 先做管理员权限校验
    error = permission_helper.require_admin()
    if error:
        return response_helper.error(error[0]['message'], error[0]['error_code'], error[1])

    # GET: 查询用户列表
    if request.method == 'GET':
        try:
            users, error = db_helper.get_all(User, order_by=User.id.desc())
            if error:
                return response_helper.internal_error(f'Query users failed: {error}')
            
            return response_helper.list_response(
                items=[u.to_dict() for u in (users or [])],
                message='用户列表查询成功'
            )
        except Exception as e:
            current_app.logger.error(f'Get users error: {e}')
            return response_helper.internal_error(f'Failed to get users: {str(e)}')

    # POST: 处理管理动作
    data = request.get_json(silent=True)
    if data is None:
        return response_helper.bad_request('Invalid JSON body', 'INVALID_JSON')

    action = (data.get('action') or '').strip()

    # 新增用户
    if action == 'create_user':
        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()
        name = (data.get('name') or username).strip()
        role = (data.get('role') or 'student').strip()

        if not username or not password:
            return response_helper.bad_request('username/password 不能为空', 'MISSING_FIELDS')

        existing_user, error = db_helper.get_by_filter(User, username=username)
        if existing_user:
            return response_helper.conflict('用户名已存在', 'USERNAME_EXISTS')

        user = User(username=username, name=name, role=role)
        user.set_password(password)
        user, error = db_helper.add_and_commit(user)
        if error:
            return response_helper.internal_error(f'Create user failed: {error}')

        return response_helper.created(
            data=user.to_dict(),
            message='用户创建成功'
        )

    # 强制解绑微信
    if action == 'force_unbind_wechat':
        username = (data.get('username') or '').strip()
        user_id = data.get('user_id')

        target_user = None
        if user_id:
            target_user, _ = db_helper.get_by_id(User, user_id)
        elif username:
            target_user, _ = db_helper.get_by_filter(User, username=username)

        if not target_user:
            return response_helper.not_found('User not found', 'USER_NOT_FOUND')

        old_openid = target_user.openid
        target_user, error = db_helper.update_and_commit(target_user, openid=None)
        if error:
            return response_helper.internal_error(f'Unbind WeChat failed: {error}')

        return response_helper.success(
            data={
                'user_id': target_user.id,
                'username': target_user.username,
                'old_openid': old_openid,
                'new_openid': target_user.openid
            },
            message='WeChat unbound successfully'
        )

    return response_helper.bad_request('不支持的 action', 'INVALID_ACTION')


# 6) 边缘硬件上报



# 7) 设备动作下发
# POST /api/device/action
@bp.route('/device/action', methods=['POST'])
@token_required
def device_action():
    """设备动作统一入口。请求体中包含 mac_address、action_type。"""
    current_user = g.current_user
    data = request.get_json(silent=True) or {}

    mac_address_input = (data.get('mac_address') or '').strip()
    mac_address = _normalize_mac_address(mac_address_input)
    action_type = (data.get('action_type') or '').strip().lower()
    state = data.get('state')

    if not mac_address:
        return response_helper.bad_request('MAC 地址格式无效', 'INVALID_MAC_FORMAT')
    if not action_type:
        return response_helper.bad_request('操作类型不能为空', 'MISSING_ACTION')

    # 权限检查
    error_resp = permission_helper.check_device_access(current_user, mac_address)
    if error_resp[0]:
        return response_helper.error(error_resp[0]['message'], error_resp[0]['error_code'], error_resp[1])

    # 兼容历史脏数据：权限已存在但 devices 表缺记录时，自动补齐离线占位设备
    device, error = db_helper.get_by_filter(Device, mac_address=mac_address)
    if error:
        current_app.logger.error(f'[device_action] query device failed: {error}')
    if not device:
        mac_no_colon = mac_address.replace(':', '')
        placeholder = Device(
            mac_address=mac_address,
            name=f'设备_{mac_no_colon[-8:]}',
            status='offline'
        )
        created_device, create_error = db_helper.add_and_commit(placeholder)
        if create_error:
            current_app.logger.warning(f'[device_action] create placeholder device failed: {create_error}')
        else:
            device = created_device

    # 前端 action_type -> ESP32 cmd
    # ESP32 订阅主题：/iot/device/{mac}/down
    actions = {
        'open_door': 'open_door',
        'keep_open': 'keep_open',      # 常开模式
        'cam_ctrl': 'cam_ctrl',
        'alarm': 'alarm',              # 报警
        'light': 'led_control',
        'query_status': 'query_status',
        'reboot': 'reboot',
    }

    cmd = actions.get(action_type)
    if not cmd:
        return response_helper.bad_request(f'不支持的动作: {action_type}', 'INVALID_ACTION_TYPE')

    try:
        command = {
            'cmd': cmd,
            'user_id': current_user.id,
            'timestamp': int(time.time())
        }
        if state is not None:
            command['state'] = state

        current_app.logger.info(f"[device_action] Publishing command: cmd={cmd}, mac={mac_address}")
        
        success = publish_command(mac_address, command)
        current_app.logger.info(f"[device_action] Publish result: {'success' if success else 'failed'}")
        
        if not success:
            return response_helper.error('指令下发失败', 'MQTT_ERROR', 500)

        return response_helper.success(
            data={'action_type': action_type},
            message='指令已发送'
        )
    except Exception as e:
        current_app.logger.error(f'Device action error: {e}')
        return response_helper.internal_error(f'操作失败: {str(e)}')


# 8) 用户解绑设备
# DELETE /api/user/devices/<mac>
@bp.route('/user/devices/<string:mac>', methods=['DELETE'])
@token_required
def unbind_device(mac):
    """用户解绑设备。"""
    current_user = g.current_user
    mac_address = (mac or '').strip().upper()

    if not mac_address:
        return response_helper.bad_request('MAC 地址无效', 'INVALID_MAC')

    perm, _ = db_helper.get_by_filter(
        UserDevicePermission,
        user_id=current_user.id,
        device_mac=mac_address
    )

    if not perm:
        return response_helper.not_found('未绑定该设备', 'BINDING_NOT_FOUND')

    try:
        _, error = db_helper.delete_and_commit(perm)
        if error:
            return response_helper.internal_error(f'解绑失败: {error}')
        
        return response_helper.success(
            data={'mac_address': mac_address},
            message='设备已解绑'
        )
    except Exception as e:
        current_app.logger.error(f'Unbind device error: {e}')
        return response_helper.internal_error(f'解绑失败: {str(e)}')


# 9) 实时视频流代理（纯转发，不存数据库）
# GET /api/device/stream/<mac_address>
@bp.route('/device/stream/<mac_address>', methods=['GET'])
@token_required
def proxy_device_stream(mac_address):
    """
        实时视频流代理接口（仅转发，不落库）。
    """
    current_user = g.current_user
    
    # 先做设备访问权限校验
    error = permission_helper.check_device_access(current_user, mac_address)
    if error:
        return response_helper.error(error[0]['message'], error[0]['error_code'], error[1])
    
    # 查询设备
    device, error = db_helper.get_by_filter(Device, mac_address=mac_address)
    if error:
        return response_helper.internal_error(f'Query device failed: {error}')
    if not device:
        return response_helper.not_found('设备不存在', 'DEVICE_NOT_FOUND')
    
    # 设备离线时直接返回
    if device.status != 'online':
        return response_helper.error(
            '设备离线，无法获取视频流',
            'DEVICE_OFFLINE',
            503
        )
    
    # 从配置读取视频流地址
    stream_url = current_app.config.get('DEVICE_STREAM_URL_TEMPLATE', 'http://192.168.3.161:81/stream')
    
    # 也可以改为从设备表读取 stream_url
    # stream_url = getattr(device, 'stream_url', None)
    # if not stream_url:
    #     return response_helper.not_found('设备未配置视频流地址', 'STREAM_URL_NOT_CONFIGURED')
    
    try:
        # 反向代理上游视频流
        current_app.logger.info(f'Proxying stream from {stream_url} for user {current_user.id}')
        
        # 流式读取上游响应
        upstream = requests.get(
            stream_url,
            stream=True,  # 启用流式传输
            timeout=30
        )
        
        # 再流式返回给小程序
        def generate():
            """逐块转发上游数据。"""
            try:
                for chunk in upstream.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
            except Exception as e:
                current_app.logger.error(f'Stream proxy error: {e}')
            finally:
                upstream.close()
        
        return Response(
            stream_with_context(generate()),
            content_type=upstream.headers.get('Content-Type', 'multipart/x-mixed-replace'),
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲（如果使用Nginx）
            }
        )
        
    except requests.exceptions.Timeout:
        return response_helper.error('设备响应超时', 'DEVICE_TIMEOUT', 504)
    except requests.exceptions.ConnectionError:
        return response_helper.error('无法连接到设备', 'DEVICE_UNREACHABLE', 503)
    except Exception as e:
        current_app.logger.error(f'Stream proxy fatal error: {e}')
        return response_helper.internal_error(f'视频流代理失败: {str(e)}')





