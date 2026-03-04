"""对象序列化工具"""


def serialize_user(user):
    if not user:
        return None
    return {
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'role': user.role,
        'created_at': user.created_at.isoformat() if user.created_at else None
    }


def serialize_device(device):
    if not device:
        return None
    return {
        'mac_address': device.mac_address,
        'name': device.name,
        'room_number': device.room_number,
        'status': device.status,
        'last_heartbeat': device.last_heartbeat.isoformat() if device.last_heartbeat else None,
        'created_at': device.created_at.isoformat() if device.created_at else None
    }


def serialize_log(log):
    if not log:
        return None
    return {
        'event_id': log.event_id,
        'mac_address': log.mac_address,
        'unlock_method': log.unlock_method,
        'user_name': log.user.name if log.user else 'Unknown',
        'snapshot_url': log.snapshot_url,
        'create_time': log.create_time.isoformat() if log.create_time else None
    }


def serialize_permission(perm):
    if not perm:
        return None
    return {
        'id': perm.id,
        'user_id': perm.user_id,
        'device_mac': perm.device_mac,
        'status': perm.status,
        'apply_time': perm.apply_time.isoformat() if perm.apply_time else None,
        'review_time': perm.review_time.isoformat() if perm.review_time else None,
        'reviewed_by': perm.reviewed_by,
        'created_at': perm.created_at.isoformat() if perm.created_at else None
    }


def serialize_application(app):
    if not app:
        return None
    return {
        'id': app.id,
        'user_id': app.user_id,
        'device_mac': app.device_mac,
        'status': app.status,
        'reason': app.reason,
        'admin_comment': app.admin_comment,
        'created_at': app.created_at.isoformat() if app.created_at else None,
        'updated_at': app.updated_at.isoformat() if app.updated_at else None,
        'reviewed_by': app.reviewed_by,
        'reviewed_at': app.reviewed_at.isoformat() if app.reviewed_at else None
    }
