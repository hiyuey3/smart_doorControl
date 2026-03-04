from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from app import db
from core.models import Admin, User, Device, Log
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


@web_bp.route('/users/add', methods=['POST'])
@login_required
def add_user():
    """添加用户"""
    data = request.form
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
    return redirect(url_for('web.users'))


@web_bp.route('/users/<int:user_id>/delete')
@login_required
def delete_user(user_id):
    """删除用户"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
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
