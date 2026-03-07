#!/usr/bin/env python3
"""
数据库初始化脚本 - 用于初始化测试数据
默认模式：不删除现有数据库，只创建缺失的表
重置模式：使用 --reset 标志重新创建数据库

使用方法：
    python init_db.py          # 仅创建新表，保留现有数据
    python init_db.py --reset  # 删除所有表并重新初始化（谨慎使用）
"""

from app import create_app, db
from core.models import User, Device, Log, UserDevicePermission, DeviceApplication, Admin
import hashlib
import sys

def init_database(reset_mode=False):
    """
    初始化数据库
    
    Args:
        reset_mode: 是否重置模式（删除并重新创建所有表）
    """
    app = create_app()
    
    with app.app_context():
        print("=== 开始初始化数据库 ===")
        
        if reset_mode:
            # 重置模式：删除所有表
            print("1. 重置模式：删除旧表...")
            confirm = input("警告: 这将删除所有现有数据！继续吗？(yes/no): ")
            if confirm.lower() != 'yes':
                print("已取消操作")
                return
            db.drop_all()
        else:
            # 安全模式：仅创建缺失的表
            print("1. 安全模式：保留现有数据，创建缺失的表...")
        
        # 创建所有表
        print("2. 创建新表...")
        db.create_all()
        
        # 在安全模式下，检查测试数据是否已存在
        if not reset_mode:
            existing_student = User.query.filter_by(username='2021001').first()
            if existing_student:
                print("3. 跳过测试数据添加（已存在）")
                print("\n=== 数据库初始化完成 ===")
                return
        
        # 添加测试用户
        print("3. 添加测试数据...")
        
        # 添加学生用户
        student = User(
            username='2021001',  # 学号作为登录账号
            name='张三',  # 姓名
            role='student'
        )
        student.set_password('123456')
        db.session.add(student)
        
        # 添加管理员用户
        admin_user = User(
            username='admin001',  # 工号作为登录账号
            name='李四',  # 姓名
            role='admin'
        )
        admin_user.set_password('123456')
        db.session.add(admin_user)
        
        # 添加宿管用户
        warden_user = User(
            username='warden001',  # 工号作为登录账号
            name='王五',  # 姓名
            role='warden'
        )
        warden_user.set_password('123456')
        db.session.add(warden_user)
        
        # 提交用户数据
        db.session.commit()
        print(f"   - 用户创建完成 (学生ID: {student.id}, 管理员ID: {admin_user.id}, 宿管ID: {warden_user.id})")
        
        # 添加测试设备
        device1 = Device(
            mac_address='AA:BB:CC:DD:EE:01',
            name='教室1门禁',
            room_number='101',
            status='online'
        )
        db.session.add(device1)
        
        device2 = Device(
            mac_address='AA:BB:CC:DD:EE:02',
            name='教室2门禁',
            room_number='102',
            status='online'
        )
        db.session.add(device2)
        
        device3 = Device(
            mac_address='AA:BB:CC:DD:EE:03',
            name='宿舍楼门禁',
            room_number='宿舍楼',
            status='online'
        )
        db.session.add(device3)
        
        device4 = Device(
            mac_address='AA:BB:CC:DD:EE:04',
            name='图书馆门禁',
            room_number='图书馆',
            status='offline'
        )
        db.session.add(device4)
        
        device5 = Device(
            mac_address='AA:BB:CC:DD:EE:05',
            name='食堂门禁',
            room_number='食堂',
            status='online'
        )
        db.session.add(device5)
        
        db.session.commit()
        print(f"   - 设备创建完成 (共5个设备)")
        
        # 写入用户-设备权限关系（多对多）
        
        # 学生：教室1，已批准
        permission1 = UserDevicePermission(
            user_id=student.id,
            device_mac=device1.mac_address,
            status='approved'
        )
        db.session.add(permission1)
        
        # 学生：宿舍楼，已批准
        permission2 = UserDevicePermission(
            user_id=student.id,
            device_mac=device3.mac_address,
            status='approved'
        )
        db.session.add(permission2)
        
        # 学生：食堂，待审批
        permission_pending = UserDevicePermission(
            user_id=student.id,
            device_mac=device5.mac_address,
            status='pending'
        )
        db.session.add(permission_pending)
        
        # 管理员：默认拥有全部设备权限
        for device in [device1, device2, device3, device4, device5]:
            admin_permission = UserDevicePermission(
                user_id=admin_user.id,
                device_mac=device.mac_address,
                status='approved'
            )
            db.session.add(admin_permission)
        
        # 宿管：宿舍楼和食堂
        warden_permission1 = UserDevicePermission(
            user_id=warden_user.id,
            device_mac=device3.mac_address,
            status='approved'
        )
        warden_permission2 = UserDevicePermission(
            user_id=warden_user.id,
            device_mac=device5.mac_address,
            status='approved'
        )
        db.session.add(warden_permission1)
        db.session.add(warden_permission2)
        
        db.session.commit()
        print(f"   - 权限关联创建完成")
        print(f"\n   多对多映射示例")
        print(f"   • 学生 {student.name}（ID:{student.id}）关联多个设备：")
        print(f"     ├─ 教室1门禁 - 已批准 [OK]")
        print(f"     ├─ 宿舍楼门禁 - 已批准 [OK]")
        print(f"     └─ 食堂门禁 - 待审批 [PENDING]")
        print(f"   • 宿管 {warden_user.name} 关联多个设备：已批准宿舍楼和食堂")
        print(f"   • 管理员 {admin_user.name} 关联所有设备")
        
        # 添加管理员账户（用于 Web 后台）
        web_admin = Admin(
            username='admin'
        )
        web_admin.set_password('admin123')  # 使用 SHA256 哈希
        db.session.add(web_admin)
        
        db.session.commit()
        print(f"\n   - Web 管理员创建完成")
        
        print("\n" + "=" * 60)
        print("=== 数据库初始化完成 ===")
        print("=" * 60)
        print("\n测试账户信息\n")
        print("1. 学生账号")
        print("   学号：2021001")
        print("   密码：123456")
        print("   设备权限：教室1 [OK]｜宿舍楼 [OK]｜食堂 [PENDING]")
        print("\n2. 宿管账号")
        print("   学号：warden001")
        print("   密码：123456")
        print("   设备权限：宿舍楼 [OK]｜食堂 [OK]")
        print("\n3. 管理员账号（微信小程序）")
        print("   学号：admin001")
        print("   密码：123456")
        print("   权限：所有设备 [OK]")
        print("\n4. Web 后台管理员")
        print("   用户名：admin")
        print("   密码：admin123")
        print("   访问：http://localhost:5000/admin")
        print("\n" + "=" * 60)
        print("多对多权限映射说明")
        print("=" * 60)
        print("• 一个用户可以绑定多个设备（已批准状态下可控制）")
        print("• 一个设备可以分配给多个用户（不同角色不同权限）")
        print("• 权限三态：pending（待审批）| approved（已批准）| rejected（已拒绝）")
        print("• 学生初始状态：可以申请设备，待管理员审批")
        print("=" * 60)

if __name__ == '__main__':
    # 检查命令行参数
    reset_mode = '--reset' in sys.argv
    init_database(reset_mode=reset_mode)
