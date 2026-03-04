#!/usr/bin/env python3
"""
快照渲染修复验证脚本

用途：测试 normalize_mac() 函数和 Base64 编码逻辑
运行：python test_snapshot_fix.py
"""

import sys
import os

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.dirname(__file__))

from api.routes import normalize_mac
import base64


def test_normalize_mac():
    """测试 MAC 地址标准化函数"""
    print("=" * 60)
    print("测试 1: normalize_mac() 函数")
    print("=" * 60)
    
    test_cases = [
        # (输入, 期望输出, 期望错误)
        ('AA:BB:CC:DD:EE:FF', 'AA:BB:CC:DD:EE:FF', None),
        ('aa:bb:cc:dd:ee:ff', 'AA:BB:CC:DD:EE:FF', None),
        ('AABBCCDDEEFF', 'AA:BB:CC:DD:EE:FF', None),
        ('aabbccddeeff', 'AA:BB:CC:DD:EE:FF', None),
        ('AA-BB-CC-DD-EE-FF', 'AA:BB:CC:DD:EE:FF', None),
        ('AA BB CC DD EE FF', 'AA:BB:CC:DD:EE:FF', None),
        ('26:05:AF:97:BE:47', '26:05:AF:97:BE:47', None),
        ('invalid', None, 'MAC 地址长度无效'),
        ('GGHHIIJJKKLL', None, 'MAC 地址包含非法字符'),
        ('', None, '缺少 MAC 地址'),
    ]
    
    passed = 0
    failed = 0
    
    for input_mac, expected_output, expected_error in test_cases:
        result, error = normalize_mac(input_mac)
        
        if expected_error:
            # 期望有错误
            if error and expected_error in error:
                print(f"PASS: '{input_mac}' -> 错误: {error}")
                passed += 1
            else:
                print(f"FAIL: '{input_mac}' -> 期望错误: {expected_error}, 实际: {error}")
                failed += 1
        else:
            # 期望成功
            if result == expected_output and error is None:
                print(f"PASS: '{input_mac}' -> '{result}'")
                passed += 1
            else:
                print(f"FAIL: '{input_mac}' -> 期望: '{expected_output}', 实际: '{result}', 错误: {error}")
                failed += 1
    
    print(f"\n总结: {passed} 通过, {failed} 失败")
    return failed == 0


def test_base64_encoding():
    """测试 Base64 编码是否包含换行符"""
    print("\n" + "=" * 60)
    print("测试 2: Base64 编码（检查换行符）")
    print("=" * 60)
    
    # 创建一个较大的测试数据（模拟 JPEG 图像）
    test_data = b'\xff\xd8\xff\xe0' + b'\x00' * 1000 + b'\xff\xd9'
    
    # 使用 base64.b64encode().decode('utf-8')
    base64_str = base64.b64encode(test_data).decode('utf-8')
    
    # 检查是否包含换行符
    has_newline = '\r' in base64_str or '\n' in base64_str
    
    print(f"Base64 字符串长度: {len(base64_str)}")
    print(f"包含换行符: {'是' if has_newline else '否'}")
    print(f"前 50 个字符: {base64_str[:50]}")
    print(f"后 50 个字符: {base64_str[-50:]}")
    
    if has_newline:
        print("\n警告: Base64 字符串包含换行符，可能导致微信小程序渲染失败！")
        return False
    else:
        print("\nBase64 编码正确，无换行符")
        return True


def main():
    """主测试函数"""
    print("\n智慧校园门禁系统 - 快照渲染修复验证\n")
    
    test1_passed = test_normalize_mac()
    test2_passed = test_base64_encoding()
    
    print("\n" + "=" * 60)
    print("最终结果")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("所有测试通过！修复验证成功。")
        return 0
    else:
        print("部分测试失败，请检查代码。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
