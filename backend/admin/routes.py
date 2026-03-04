from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
from app import db
from core.models import Admin, User, Device, Log, UserDevicePermission
from datetime import datetime

web_bp = Blueprint('web', __name__, url_prefix='/admin')


def login_required(f):
    """管理员登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('web.login'))
        return f(*args, **kwargs)
    return decorated_function


@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('admin/login.html', error='请输入用户名和密码')

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            # 登录成功，更新最后登录时间
            admin.last_login = datetime.utcnow()
            db.session.commit()

            # 设置 session
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username

            return redirect(url_for('web.dashboard'))
        else:
            return render_template('admin/login.html', error='用户名或密码错误')

    return render_template('admin/login.html')


@web_bp.route('/logout')
def logout():
    """管理员退出登录"""
    session.clear()
    return redirect(url_for('web.login'))


@web_bp.route('/')
@login_required
def dashboard():
    """管理后台首页 - 仪表盘"""
    # 统计数据
    user_count = User.query.count()
    device_count = Device.query.count()
    online_count = Device.query.filter_by(status='online').count()
    today_logs = Log.query.filter(
        db.func.date(Log.create_time) == db.func.current_date()
    ).count()
    total_logs = Log.query.count()

    # 最新通行记录
    recent_logs = Log.query.order_by(Log.create_time.desc()).limit(10).all()

    # 设备状态
    devices = Device.query.all()

    return render_template('admin/dashboard.html',
                         user_count=user_count,
                         device_count=device_count,
                         online_count=online_count,
                         today_logs=today_logs,
                         total_logs=total_logs,
                         recent_logs=recent_logs,
                         devices=devices)


@web_bp.route('/users')
@login_required
def users():
    """用户管理页面"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@web_bp.route('/users', methods=['POST'])
@login_required
def add_user():
    """添加用户（RESTful：POST /users）"""
    data = request.form
    try:
        user = User(
            username=data.get('username'),
            name=data.get('name'),
            role=data.get('role', 'student'),
            fingerprint_id=data.get('fingerprint_id'),
            nfc_uid=data.get('nfc_uid')
        )
        if data.get('password'):
            user.set_password(data.get('password'))
        else:
            user.set_password('123456')

        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template('admin/users.html', 
                             users=User.query.order_by(User.created_at.desc()).all(),
                             error=f'添加用户失败: {str(e)}')
    return redirect(url_for('web.users'))


@web_bp.route('/users/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """删除用户（RESTful：POST /users/<id>，通过_method=DELETE标识）"""
    user = User.query.get_or_404(user_id)
    action = request.form.get('action', 'delete')  # 默认为删除操作
    
    try:
        if action == 'delete':
            db.session.delete(user)
        elif action == 'edit':
            user.name = request.form.get('name')
            user.role = request.form.get('role', 'student')
            user.fingerprint_id = request.form.get('fingerprint_id')
            user.nfc_uid = request.form.get('nfc_uid')
        else:
            raise ValueError(f'无效的操作: {action}')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template('admin/users.html', 
                             users=User.query.order_by(User.created_at.desc()).all(),
                             error=f'操作失败: {str(e)}')
    return redirect(url_for('web.users'))


@web_bp.route('/logs')
@login_required
def logs():
    """通行记录页面"""
    page = request.args.get('page', 1, type=int)
    pagination = Log.query.order_by(Log.create_time.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/logs.html', logs=pagination.items, pagination=pagination)


@web_bp.route('/devices')
@login_required
def devices():
    """设备管理页面"""
    devices = Device.query.order_by(Device.last_heartbeat.desc()).all()
    return render_template('admin/devices.html', devices=devices)


@web_bp.route('/devices', methods=['POST'])
@login_required
def add_device():
    """添加设备（RESTful：POST /devices）"""
    data = request.form
    try:
        # 检查MAC地址是否已存在
        existing = Device.query.filter_by(mac_address=data.get('mac_address')).first()
        if existing:
            raise ValueError(f'MAC地址已存在: {data.get("mac_address")}')
        
        device = Device(
            name=data.get('name'),
            mac_address=data.get('mac_address'),
            location=data.get('location'),
            room_number=data.get('room_number'),
            status='offline'  # 新设备默认离线
        )
        
        db.session.add(device)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template('admin/devices.html', 
                             devices=Device.query.order_by(Device.last_heartbeat.desc()).all(),
                             error=f'添加设备失败: {str(e)}')
    return redirect(url_for('web.devices'))


@web_bp.route('/devices/<int:device_id>', methods=['POST'])
@login_required
def manage_device(device_id):
    """管理设备（编辑或删除）"""
    device = Device.query.get_or_404(device_id)
    action = request.form.get('action')  # 'edit' 或 'delete'
    
    try:
        if action == 'edit':
            # 编辑设备信息
            device.name = request.form.get('name')
            device.location = request.form.get('location')
            device.room_number = request.form.get('room_number')
            db.session.commit()
        
        elif action == 'delete':
            # 删除设备
            db.session.delete(device)
            db.session.commit()
        
        else:
            raise ValueError(f'无效的操作: {action}')
    
    except Exception as e:
        db.session.rollback()
        return render_template('admin/devices.html', 
                             devices=Device.query.order_by(Device.last_heartbeat.desc()).all(),
                             error=f'操作失败: {str(e)}')
    
    return redirect(url_for('web.devices'))


@web_bp.route('/permissions')
@login_required
def permissions():
    """权限审批页面"""
    # 获取筛选参数
    status_filter = request.args.get('status', 'all')
    
    # 构建查询
    query = UserDevicePermission.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # 按最新申请时间倒序排列
    permissions = query.order_by(UserDevicePermission.apply_time.desc()).all()
    
    # 统计待审批数量
    pending_count = UserDevicePermission.query.filter_by(status='pending').count()
    
    # 获取用户和设备列表（用于添加权限的下拉框）
    users = User.query.order_by(User.created_at.desc()).all()
    devices = Device.query.all()
    
    return render_template('admin/permissions.html', 
                         permissions=permissions, 
                         status_filter=status_filter,
                         pending_count=pending_count,
                         users=users,
                         devices=devices)


@web_bp.route('/permissions/add', methods=['POST'])
@login_required
def add_permission():
    """添加新的用户设备权限（管理员主动分配）"""
    user_id = request.form.get('user_id')
    device_mac = request.form.get('device_mac')
    status = request.form.get('status', 'approved')  # 默认已批准
    
    try:
        # 检查用户和设备是否存在
        user = User.query.get_or_404(user_id)
        device = Device.query.filter_by(mac_address=device_mac).first()
        if not device:
            raise ValueError(f'设备不存在: {device_mac}')
        
        # 检查是否已存在相同权限
        existing = UserDevicePermission.query.filter_by(
            user_id=user_id, device_mac=device_mac
        ).first()
        if existing:
            raise ValueError(f'该用户已有此设备的权限')
        
        # 创建新权限
        permission = UserDevicePermission(
            user_id=int(user_id),
            device_mac=device_mac,
            status=status
        )
        
        # 如果是直接批准，记录审批信息
        if status == 'approved':
            permission.review_time = datetime.utcnow()
            permission.reviewed_by = session.get('admin_id')
        
        db.session.add(permission)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template('admin/permissions.html',
                             permissions=UserDevicePermission.query.order_by(
                                 UserDevicePermission.apply_time.desc()).all(),
                             users=User.query.order_by(User.created_at.desc()).all(),
                             devices=Device.query.all(),
                             status_filter='all',
                             pending_count=UserDevicePermission.query.filter_by(status='pending').count(),
                             error=f'添加权限失败: {str(e)}')
    
    return redirect(url_for('web.permissions'))


@web_bp.route('/permissions/<int:permission_id>', methods=['POST'])
@login_required
def update_permission(permission_id):
    """更新权限状态或信息（RESTful：POST /permissions/<id>，通过action参数区分操作）"""
    permission = UserDevicePermission.query.get_or_404(permission_id)
    action = request.form.get('action')  # 'approve', 'reject', 'revoke' 等
    
    try:
        # 根据操作类型处理
        if action == 'approve':
            # 批准待审批申请
            if permission.status != 'pending':
                raise ValueError('只能批准待审批的申请')
            permission.status = 'approved'
            permission.review_time = datetime.utcnow()
            permission.reviewed_by = session.get('admin_id')
        
        elif action == 'reject':
            # 拒绝待审批申请
            if permission.status != 'pending':
                raise ValueError('只能拒绝待审批的申请')
            permission.status = 'rejected'
            permission.review_time = datetime.utcnow()
            permission.reviewed_by = session.get('admin_id')
        
        elif action == 'revoke':
            # 撤销已批准的权限
            if permission.status != 'approved':
                raise ValueError('只能撤销已批准的权限')
            db.session.delete(permission)
        
        else:
            raise ValueError(f'无效的操作: {action}')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template('admin/permissions.html',
                             permissions=UserDevicePermission.query.order_by(
                                 UserDevicePermission.apply_time.desc()).all(),
                             users=User.query.order_by(User.created_at.desc()).all(),
                             devices=Device.query.all(),
                             status_filter='all',
                             pending_count=UserDevicePermission.query.filter_by(status='pending').count(),
                             error=f'操作失败: {str(e)}')
    
    return redirect(url_for('web.permissions'))
