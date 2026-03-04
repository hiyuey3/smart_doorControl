from app import db
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from .mixins import BaseIDMixin, TimestampMixin, SerializerMixin


class DeviceApplication(BaseIDMixin, TimestampMixin, SerializerMixin, db.Model):
    """设备申请模型
    
    记录用户对设备的申请信息，包含申请人、目标设备、申请状态和审批流程。
    
    关键业务字段：
    - user_id + device_mac：快速定位『谁在申请哪个设备』
    - status：申请状态 (pending/approved/rejected)
    - reason：用户申请原因
    - admin_comment：管理员审批意见
    - reviewed_by + reviewed_at：审批人和审批时间
    """
    __tablename__ = 'device_applications'

    # 核心申请关系
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'), index=True)
    """申请用户 ID (Foreign Key to users.id)"""
    
    device_mac: Mapped[str] = mapped_column(db.String(17), db.ForeignKey('devices.mac_address'), index=True)
    """申请的设备 MAC 地址 (Foreign Key to devices.mac_address)"""
    
    # 申请流程
    status: Mapped[str] = mapped_column(db.String(20), default='pending', index=True)
    """申请状态：pending(待审批) / approved(已批准) / rejected(已拒绝)"""
    
    reason: Mapped[Optional[str]] = mapped_column(db.String(200))
    """用户申请原因/说明"""
    
    admin_comment: Mapped[Optional[str]] = mapped_column(db.String(200))
    """管理员审批意见或拒绝原因"""
    
    # 审批信息
    reviewed_by: Mapped[Optional[int]] = mapped_column(db.ForeignKey('users.id'))
    """审批人 ID (Foreign Key to users.id，仅在已审批时有值)"""
    
    reviewed_at: Mapped[Optional[datetime]]
    """审批时间 (仅在已审批时有值)"""
