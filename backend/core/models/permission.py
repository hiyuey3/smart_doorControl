from app import db
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from .mixins import BaseIDMixin, SerializerMixin


class UserDevicePermission(BaseIDMixin, SerializerMixin, db.Model):
    """用户设备权限模型
    
    记录用户对设备的访问权限及其申请与审批流程
    """
    __tablename__ = 'user_device_permissions'
    
    # 权限关系
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'), index=True)
    """申请用户 ID (旧: db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False))"""
    
    device_mac: Mapped[str] = mapped_column(db.String(17), db.ForeignKey('devices.mac_address'), index=True)
    """设备 MAC 地址 (旧: db.Column(db.String(17), db.ForeignKey('devices.mac_address'), nullable=False))"""
    
    # 权限状态
    status: Mapped[str] = mapped_column(db.Enum('pending', 'approved', 'rejected'), default='pending', index=True)
    """权限状态 (旧: db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending'))"""
    
    # 申请信息
    apply_time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    """申请时间 (旧: db.Column(db.DateTime, default=datetime.utcnow))"""
    
    # 审批信息
    review_time: Mapped[Optional[datetime]]
    """审批时间 (旧: db.Column(db.DateTime, nullable=True))"""
    
    reviewed_by: Mapped[Optional[int]] = mapped_column(db.ForeignKey('users.id'))
    """审批人 ID (旧: db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True))"""
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    """记录创建时间 (旧: db.Column(db.DateTime, default=datetime.utcnow))"""
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'device_mac', name='uc_user_device'),
    )
