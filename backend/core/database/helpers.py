"""数据库操作工具类"""

from functools import wraps
from flask import current_app
from app import db
from sqlalchemy.exc import SQLAlchemyError


class DatabaseHelper:
    """数据库查询、增删改、提交操作"""
    
    @staticmethod
    def get_by_id(model, record_id):
        """根据ID获取记录"""
        try:
            record = model.query.get(record_id)
            if not record:
                return None, f'{model.__name__} not found'
            return record, None
        except Exception as e:
            current_app.logger.error(f'Get by ID error: {e}')
            return None, str(e)
    
    @staticmethod
    def get_by_filter(model, **filters):
        """按条件查询单条记录"""
        try:
            record = model.query.filter_by(**filters).first()
            return record, None
        except Exception as e:
            current_app.logger.error(f'Get by filter error: {e}')
            return None, str(e)
    
    @staticmethod
    def get_all(model, order_by=None, **filters):
        """按条件查询所有记录"""
        try:
            query = model.query.filter_by(**filters)
            if order_by is not None:
                query = query.order_by(order_by)
            records = query.all()
            return records, None
        except Exception as e:
            current_app.logger.error(f'Get all error: {e}')
            return None, str(e)
    
    @staticmethod
    def add_and_commit(instance):
        """添加记录并保存"""
        try:
            db.session.add(instance)
            db.session.commit()
            return instance, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Add error: {e}')
            return None, str(e)
    
    @staticmethod
    def update_and_commit(instance, **updates):
        """更新记录并保存"""
        try:
            for key, value in updates.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            db.session.commit()
            return instance, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Update error: {e}')
            return None, str(e)
    
    @staticmethod
    def delete_and_commit(instance):
        """删除记录并保存"""
        try:
            db.session.delete(instance)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Delete error: {e}')
            return False, str(e)
    
    @staticmethod
    def commit_changes():
        """保存所有修改"""
        try:
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Commit error: {e}')
            return False, str(e)
    
    @staticmethod
    def rollback():
        """撤销所有修改"""
        try:
            db.session.rollback()
        except Exception as e:
            current_app.logger.error(f'Rollback error: {e}')


db_helper = DatabaseHelper()
