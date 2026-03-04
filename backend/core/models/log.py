from app import db
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from .mixins import SerializerMixin


class Log(SerializerMixin, db.Model):
    """操作日志模型
    
    记录所有门禁设备的开锁操作和事件
    """
    __tablename__ = 'logs'
    
    # 主键
    event_id: Mapped[str] = mapped_column(db.String(50), primary_key=True)
    """事件 ID (旧: db.Column(db.String(50), primary_key=True))"""

    # 关键关系
    mac_address: Mapped[str] = mapped_column(db.String(17), db.ForeignKey('devices.mac_address'), index=True)
    """设备 MAC 地址 (Foreign Key) (旧: db.Column(db.String(17), db.ForeignKey('devices.mac_address'), nullable=False))"""
    
    user_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('users.id'), index=True)
    """操作用户 ID (Foreign Key) (旧: db.Column(db.Integer, db.ForeignKey('users.id')))"""

    # 操作信息
    unlock_method: Mapped[str] = mapped_column(db.Enum('fingerprint', 'nfc', 'remote'), index=True)
    """开锁方式 (旧: db.Column(db.Enum('fingerprint', 'nfc', 'remote'), nullable=False))"""
    
    snapshot_url: Mapped[Optional[str]] = mapped_column(db.String(255))
    """快照图片 URL (旧: db.Column(db.String(255)))"""

    # 时间戳
    create_time: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    """事件创建时间 (旧: db.Column(db.DateTime, default=datetime.utcnow))"""