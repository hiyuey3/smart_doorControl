"""数据库操作工具类 - 统一CRUD操作和事务管理"""

from app import db
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps


class DatabaseHelper:
    """数据库帮助类 - 提供统一的CRUD操作
    
    所有方法都返回 (result, error) 元组，便于统一错误处理。
    """
    
    @staticmethod
    def get_by_filter(model_class, **filters):
        """按条件查询单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            **filters: 过滤条件 (key=value)
            
        Returns:
            tuple: (record, None) 成功 或 (None, error_message) 失败
        """
        try:
            query = select(model_class).filter_by(**filters)
            record = db.session.execute(query).scalar_one_or_none()
            return record, None
        except SQLAlchemyError as e:
            return None, f"数据库查询失败: {str(e)}"
        except Exception as e:
            return None, f"未知错误: {str(e)}"
    
    @staticmethod
    def get_by_id(model_class, record_id):
        """按主键查询单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            record_id: 主键值
            
        Returns:
            tuple: (record, None) 成功 或 (None, error_message) 失败
        """
        try:
            record = db.session.get(model_class, record_id)
            return record, None
        except SQLAlchemyError as e:
            return None, f"数据库查询失败: {str(e)}"
        except Exception as e:
            return None, f"未知错误: {str(e)}"
    
    @staticmethod
    def get_all(model_class):
        """查询所有记录
        
        Args:
            model_class: SQLAlchemy 模型类
            
        Returns:
            tuple: (records_list, None) 成功 或 ([], error_message) 失败
        """
        try:
            query = select(model_class)
            records = db.session.execute(query).scalars().all()
            return records, None
        except SQLAlchemyError as e:
            return [], f"数据库查询失败: {str(e)}"
        except Exception as e:
            return [], f"未知错误: {str(e)}"
    
    @staticmethod
    def add_and_commit(instance):
        """新增并提交
        
        Args:
            instance: 数据库实例对象
            
        Returns:
            tuple: (instance, None) 成功 或 (None, error_message) 失败
        """
        try:
            db.session.add(instance)
            db.session.commit()
            return instance, None
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"数据库提交失败: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"未知错误: {str(e)}"
    
    @staticmethod
    def update_and_commit(instance, **updates):
        """更新并提交
        
        Args:
            instance: 数据库实例对象
            **updates: 要更新的字段值
            
        Returns:
            tuple: (instance, None) 成功 或 (None, error_message) 失败
        """
        try:
            for key, value in updates.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            db.session.commit()
            return instance, None
        except SQLAlchemyError as e:
            db.session.rollback()
            return None, f"数据库更新失败: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return None, f"未知错误: {str(e)}"
    
    @staticmethod
    def delete_and_commit(instance):
        """删除并提交
        
        Args:
            instance: 数据库实例对象
            
        Returns:
            tuple: (True, None) 成功 或 (False, error_message) 失败
        """
        try:
            db.session.delete(instance)
            db.session.commit()
            return True, None
        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"数据库删除失败: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"未知错误: {str(e)}"
    
    @staticmethod
    def batch_add_and_commit(instances):
        """批量新增并提交
        
        Args:
            instances: 实例列表
            
        Returns:
            tuple: (instances, None) 成功 或 ([], error_message) 失败
        """
        try:
            db.session.add_all(instances)
            db.session.commit()
            return instances, None
        except SQLAlchemyError as e:
            db.session.rollback()
            return [], f"数据库批量提交失败: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return [], f"未知错误: {str(e)}"
    
    @staticmethod
    def with_transaction(f):
        """事务装饰器 - 自动处理提交和回滚
        
        Usage:
            @with_transaction
            def update_user_and_device(user_id, device_id):
                ...
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                db.session.commit()
                return result, None
            except SQLAlchemyError as e:
                db.session.rollback()
                return None, f"事务执行失败: {str(e)}"
            except Exception as e:
                db.session.rollback()
                return None, f"未知错误: {str(e)}"
        return decorated_function


# 全局实例
db_helper = DatabaseHelper()
