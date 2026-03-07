"""日志记录工具"""

import time
from datetime import datetime
from core.models import Log
from .db_helper import db_helper


class LogHelper:
    """日志记录"""
    
    @staticmethod
    def create_access_log(mac_address, user_id=None, unlock_method='unknown', 
                         success=True, failure_reason=None, image_path=None):
        """创建访问日志
        
        Log 模型不保存 success/failure_reason。
        这两个参数保留是为了兼容旧调用方。
        """
        # 生成事件ID
        event_id = f"{unlock_method}_{int(time.time())}_{mac_address.replace(':', '')}"
        
        # 仅写入 Log 模型实际存在的字段
        log_entry = Log(
            event_id=event_id,
            mac_address=mac_address,
            user_id=user_id,
            unlock_method=unlock_method,
            snapshot_url=image_path
        )
        
        return db_helper.add_and_commit(log_entry)
    
    @staticmethod
    def create_remote_unlock_log(mac_address, user_id, device_name=None):
        """创建远程开锁日志"""
        return LogHelper.create_access_log(
            mac_address=mac_address,
            user_id=user_id,
            unlock_method='remote',
            success=True
        )
    
    @staticmethod
    def create_fingerprint_log(mac_address, user_id=None, success=True, 
                               failure_reason=None, image_path=None):
        """创建指纹日志"""
        return LogHelper.create_access_log(
            mac_address=mac_address,
            user_id=user_id,
            unlock_method='fingerprint',
            success=success,
            failure_reason=failure_reason,
            image_path=image_path
        )
    
    @staticmethod
    def create_nfc_log(mac_address, user_id=None, success=True, 
                      failure_reason=None, image_path=None):
        """
        创建NFC刷卡日志的快捷方法
        
        Args:
            mac_address: 设备MAC地址
            user_id: 识别出的用户ID
            success: 是否识别成功
            failure_reason: 失败原因
            image_path: 抓拍图片路径
            
        Returns:
            元组： (log_instance, error)
        """
        return LogHelper.create_access_log(
            mac_address=mac_address,
            user_id=user_id,
            unlock_method='nfc',
            success=success,
            failure_reason=failure_reason,
            image_path=image_path
        )
    
    @staticmethod
    def create_face_recognition_log(mac_address, user_id=None, success=True,
                                   failure_reason=None, image_path=None):
        """
        创建人脸识别日志的快捷方法
        
        Args:
            mac_address: 设备MAC地址
            user_id: 识别出的用户ID
            success: 是否识别成功
            failure_reason: 失败原因
            image_path: 抓拍图片路径
            
        Returns:
            元组： (log_instance, error)
        """
        return LogHelper.create_access_log(
            mac_address=mac_address,
            user_id=user_id,
            unlock_method='face',
            success=success,
            failure_reason=failure_reason,
            image_path=image_path
        )


log_helper = LogHelper()
