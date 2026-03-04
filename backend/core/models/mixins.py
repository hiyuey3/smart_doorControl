"""SQLAlchemy 2.0 Mixin 类 - 为所有模型提供基础字段"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.inspection import inspect


class BaseIDMixin:
    """基础 ID 主键 Mixin
    
    为所有模型提供统一的自增主键字段
    旧语法: id = db.Column(db.Integer, primary_key=True)
    """
    id: Mapped[int] = mapped_column(primary_key=True)


class TimestampMixin:
    """时间戳 Mixin
    
    为所有模型提供创建时间和更新时间字段：
    - created_at: 记录首次创建时间
    - updated_at: 记录最后一次更新时间
    
    旧语法:
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    """
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class SerializerMixin:
    """序列化 Mixin
    
    为所有模型提供 to_dict() 方法，用于 JSON 序列化
    自动处理所有数据库字段，包括 datetime 类型
    """
    
    def to_dict(self, exclude=None):
        """将模型实例转换为字典
        
        Args:
            exclude: 要排除的字段列表（可选）
            
        Returns:
            dict: 序列化后的字典
        """
        if exclude is None:
            exclude = []
        
        result = {}
        
        # 获取所有列
        mapper = inspect(self.__class__)
        for column in mapper.columns:
            column_name = column.key
            
            # 跳过排除的字段
            if column_name in exclude:
                continue
            
            value = getattr(self, column_name, None)
            
            # 处理 datetime 类型
            if isinstance(value, datetime):
                result[column_name] = value.isoformat() if value else None
            else:
                result[column_name] = value
        
        return result
