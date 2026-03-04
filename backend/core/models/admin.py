from app import db
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
import hashlib
from .mixins import BaseIDMixin, SerializerMixin


class Admin(BaseIDMixin, SerializerMixin, db.Model):
    """管理员模型
    
    系统管理员账户，用于后台管理和审批操作
    """
    __tablename__ = 'admins'

    # 认证信息
    username: Mapped[str] = mapped_column(db.String(50), unique=True)
    """管理员用户名 (旧: db.Column(db.String(50), unique=True, nullable=False))"""
    
    password: Mapped[str] = mapped_column(db.String(100))
    """密码哈希 (旧: db.Column(db.String(100), nullable=False))"""

    # 权限
    role: Mapped[str] = mapped_column(db.String(20), default='admin')
    """管理员角色 (旧: db.Column(db.String(20), default='admin'))"""

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    """账户创建时间 (旧: db.Column(db.DateTime, default=datetime.utcnow))"""
    
    last_login: Mapped[Optional[datetime]]
    """最后登录时间 (旧: db.Column(db.DateTime, nullable=True))"""

    def set_password(self, password):
        """设置密码（SHA256 哈希）"""
        self.password = hashlib.sha256(password.encode('utf-8')).hexdigest()

    def check_password(self, password):
        """验证密码"""
        if not self.password:
            return False
        return self.password == hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def to_dict(self, exclude=None):
        """自定义序列化方法 - 默认排除密码
        
        Args:
            exclude: 额外要排除的字段列表
            
        Returns:
            dict: 序列化后的字典（不含密码）
        """
        if exclude is None:
            exclude = []
        
        # 默认排除密码字段
        exclude.append('password')
        
        # 调用父类的 to_dict 方法
        return super().to_dict(exclude=exclude)
