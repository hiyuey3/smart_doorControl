from app import db
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
import secrets
import hashlib
from .mixins import BaseIDMixin, TimestampMixin, SerializerMixin


class User(BaseIDMixin, TimestampMixin, SerializerMixin, db.Model):
    """用户模型
    
    记录系统用户信息，支持多种认证方式（微信/用户名/指纹/NFC）
    """
    __tablename__ = 'users'

    # 认证信息
    openid: Mapped[Optional[str]] = mapped_column(db.String(100), unique=True)
    """微信 OpenID"""
    
    username: Mapped[Optional[str]] = mapped_column(db.String(50), unique=True)
    """用户名 (旧: db.Column(db.String(50), unique=True, nullable=True))"""
    
    password: Mapped[Optional[str]] = mapped_column(db.String(100))
    """密码哈希 (旧: db.Column(db.String(100), nullable=True))"""

    # 用户信息
    name: Mapped[Optional[str]] = mapped_column(db.String(100))
    """用户姓名 (旧: db.Column(db.String(100), nullable=True))"""
    
    avatar: Mapped[Optional[str]] = mapped_column(db.String(255))
    """用户头像 URL (旧: db.Column(db.String(255), nullable=True))"""
    
    role: Mapped[str] = mapped_column(db.Enum('student', 'warden', 'admin'), default='student')
    """用户角色 (旧: db.Column(db.Enum('student', 'warden', 'admin'), default='student'))"""

    # 生物识别
    fingerprint_id: Mapped[Optional[str]] = mapped_column(db.String(50), unique=True)
    """指纹 ID (旧: db.Column(db.String(50), unique=True))"""
    
    nfc_uid: Mapped[Optional[str]] = mapped_column(db.String(50), unique=True)
    """NFC 卡 UID (旧: db.Column(db.String(50), unique=True))"""

    # 会话信息
    token: Mapped[Optional[str]] = mapped_column(db.String(100), unique=True)
    """认证令牌 (旧: db.Column(db.String(100), unique=True, nullable=True))"""

    def set_password(self, password):
        """设置密码（SHA256 哈希）"""
        self.password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        """验证密码"""
        if not self.password:
            return False
        return self.password == hashlib.sha256(password.encode('utf-8')).hexdigest()

    def generate_token(self):
        """生成新的认证令牌"""
        self.token = secrets.token_hex(32)
        return self.token

    def verify_token(self, token):
        """验证令牌是否有效"""
        return self.token == token

    def to_dict(self, exclude=None):
        """自定义序列化方法 - 默认排除敏感字段
        
        Args:
            exclude: 额外要排除的字段列表
            
        Returns:
            dict: 序列化后的字典（不含密码、token 等敏感信息）
        """
        if exclude is None:
            exclude = []
        
        # 默认排除敏感字段
        exclude.extend(['password', 'token'])
        
        # 调用父类的 to_dict 方法
        return super().to_dict(exclude=exclude)
