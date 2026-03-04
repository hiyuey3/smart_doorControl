"""API响应格式化工具"""

from flask import jsonify


class ResponseHelper:
    """统一生成API响应"""
    
    @staticmethod
    def success(data=None, message='成功', status_code=200):
        """返回成功响应"""
        response = {'success': True, 'message': message}
        if data is not None:
            response['data'] = data
        return jsonify(response), status_code
    
    @staticmethod
    def error(message, error_code='ERROR', status_code=400, data=None):
        """返回错误响应"""
        response = {
            'success': False,
            'message': message,
            'error_code': error_code
        }
        if data is not None:
            response['data'] = data
        return jsonify(response), status_code
    
    @staticmethod
    def created(data, message='创建成功'):
        """返回创建成功响应（201）"""
        resp = jsonify({'success': True, 'message': message, 'data': data})
        resp.status_code = 201
        return resp
    
    @staticmethod
    def paginated(items, page, per_page, total, message='成功'):
        """返回分页响应"""
        import math
        return jsonify({
            'success': True,
            'message': message,
            'data': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': math.ceil(total / per_page) if per_page > 0 else 0
            }
        }), 200
    
    @staticmethod
    def list_response(items, count=None, message='成功'):
        """返回列表响应"""
        if count is None:
            count = len(items) if items else 0
        return jsonify({
            'success': True,
            'message': message,
            'data': items,
            'count': count
        }), 200
    
    # 常用错误响应
    @staticmethod
    def bad_request(message='请求错误', error_code='BAD_REQUEST'):
        """400 错误请求"""
        return ResponseHelper.error(message, error_code, 400)
    
    @staticmethod
    def unauthorized(message='未授权', error_code='UNAUTHORIZED'):
        """401 未授权"""
        return ResponseHelper.error(message, error_code, 401)
    
    @staticmethod
    def forbidden(message='无权限', error_code='FORBIDDEN'):
        """403 禁止访问"""
        return ResponseHelper.error(message, error_code, 403)
    
    @staticmethod
    def not_found(message='不存在', error_code='NOT_FOUND'):
        """404 不存在"""
        return ResponseHelper.error(message, error_code, 404)
    
    @staticmethod
    def conflict(message='冲突', error_code='CONFLICT'):
        """409 冲突"""
        return ResponseHelper.error(message, error_code, 409)
    
    @staticmethod
    def internal_error(message='服务器错误', error_code='INTERNAL_ERROR'):
        """500 服务器错误"""
        return ResponseHelper.error(message, error_code, 500)


response_helper = ResponseHelper()
