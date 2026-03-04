"""权限检查工具"""

from flask import g
from core.models import UserDevicePermission


class PermissionHelper:
    """权限检查"""
    
    @staticmethod
    def is_admin(user=None):
        """判断是否是管理员"""
        if user is None:
            user = g.current_user
        return user.role == 'admin'
    
    @staticmethod
    def require_admin(user=None):
        """检查是否是管理员，不是返回错误"""
        if user is None:
            user = g.current_user
        
        if user.role != 'admin':
            return {
                'success': False,
                'message': '无管理员权限',
                'error_code': 'ADMIN_REQUIRED'
            }, 403
        
        return None, None
    
    @staticmethod
    def has_device_permission(user_id, device_mac, status='approved'):
        """检查用户是否有设备权限"""
        perm = UserDevicePermission.query.filter_by(
            user_id=user_id,
            device_mac=device_mac,
            status=status
        ).first()
        return (True, perm) if perm else (False, None)
    
    @staticmethod
    def check_device_access(user, device_mac):
        """检查设备访问权限"""
        # 管理员有全部权限
        if user.role == 'admin':
            return None, None
        
        # 普通用户需要拥有权限
        has_perm, _ = PermissionHelper.has_device_permission(
            user.id, device_mac, status='approved'
        )
        
        if not has_perm:
            return {
                'success': False,
                'message': '无权限访问该设备',
                'error_code': 'PERMISSION_DENIED'
            }, 403
        
        return None, None
    
    @staticmethod
    def get_user_accessible_devices(user_id):
        """获取用户有权访问的所有设备"""
        perms = UserDevicePermission.query.filter_by(
            user_id=user_id,
            status='approved'
        ).all()
        return [p.device_mac for p in perms]


permission_helper = PermissionHelper()
