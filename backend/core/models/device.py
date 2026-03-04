from app import db
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from .mixins import SerializerMixin


class Device(SerializerMixin, db.Model):
    """设备模型
    
    管理门禁系统中的硬件设备（锁）
    """
    __tablename__ = 'devices'

    # 主键
    mac_address: Mapped[str] = mapped_column(db.String(17), primary_key=True)
    """设备 MAC 地址 (旧: db.Column(db.String(17), primary_key=True))"""

    # 设备信息
    name: Mapped[Optional[str]] = mapped_column(db.String(100))
    """设备名称 (旧: db.Column(db.String(100), nullable=True))"""
    
    room_number: Mapped[Optional[str]] = mapped_column(db.String(10))
    """房间号 (旧: db.Column(db.String(10), nullable=True))"""

    # 状态监控
    status: Mapped[str] = mapped_column(db.Enum('online', 'offline'), default='offline')
    """设备状态 (旧: db.Column(db.Enum('online', 'offline'), default='offline'))"""
    
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column()
    """最后心跳时间 (旧: db.Column(db.DateTime))"""

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    """设备创建时间 (旧: db.Column(db.DateTime, default=datetime.utcnow))"""
