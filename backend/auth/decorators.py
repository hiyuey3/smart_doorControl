from functools import wraps
from flask import jsonify, request, g, current_app
from core.models import User
import jwt
from datetime import datetime

def token_required(f):
    """
    【JWT Token 验证装饰器】
    
    功能：
    1. 从 HTTP Authorization 头提取 JWT Token
    2. 使用应用的 SECRET_KEY 验证 Token 签名
    3. 检查 Token 是否过期
    4. 从 Token 的 Payload 中提取 user_id，并加载用户对象到 g.current_user
    
    使用方式：
    @bp.route('/api/my_devices', methods=['GET'])
    @token_required
    def get_my_devices():
        current_user = g.current_user  # 获取当前登录用户
        ...
    
    错误响应：
    - HTTP 401（无 Token）：Missing authorization token
    - HTTP 401（格式错误）：Invalid token format
    - HTTP 401（签名验证失败）：Invalid or expired token
    - HTTP 404（用户不存在）：User not found
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 【步骤 1】从 Authorization 头提取 Token
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'success': False,
                'message': 'Missing authorization token',
                'error_code': 'MISSING_TOKEN'
            }), 401
        
        # 【步骤 2】验证 Token 格式：应该是 "Bearer <token>"
        parts = auth_header.split()
        
        if len(parts) != 2 or parts[0] != 'Bearer':
            return jsonify({
                'success': False,
                'message': 'Invalid token format. Use "Bearer <token>"',
                'error_code': 'INVALID_TOKEN_FORMAT'
            }), 401
        
        token = parts[1]
        
        # 【步骤 3】验证 JWT Token 的签名和过期时间
        try:
            secret_key = current_app.config.get('SECRET_KEY')
            
            # 解码 JWT Token（这会验证签名和过期时间）
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            print(f"[验证] JWT Token 验证成功: user_id={payload.get('user_id')}, role={payload.get('role')}")
        
        except jwt.ExpiredSignatureError:
            # Token 已过期
            print(f"[错误] JWT Token 已过期")
            return jsonify({
                'success': False,
                'message': 'Token has expired',
                'error_code': 'TOKEN_EXPIRED'
            }), 401
        
        except jwt.InvalidTokenError as e:
            # Token 签名验证失败或其他解码错误
            print(f"[错误] JWT Token 验证失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Invalid or corrupted token',
                'error_code': 'INVALID_TOKEN'
            }), 401
        
        except Exception as e:
            # 其他异常
            print(f"[错误] Token 处理异常: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Token processing error: {str(e)}',
                'error_code': 'TOKEN_ERROR'
            }), 401
        
        # 【步骤 4】从 Token 的 Payload 提取 user_id，并加载用户对象
        user_id = payload.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Invalid token: missing user_id',
                'error_code': 'MISSING_USER_ID'
            }), 401
        
        # 查询数据库获取用户对象
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found',
                'error_code': 'USER_NOT_FOUND'
            }), 404
        
        # 【步骤 5】将当前用户对象存储到 g 对象中，供后续路由函数使用
        g.current_user = user
        
        # 继续执行原始的路由函数
        return f(*args, **kwargs)
    
    return decorated_function