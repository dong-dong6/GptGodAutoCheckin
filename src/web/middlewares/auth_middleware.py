"""
认证中间件
提供Session认证和API Token认证
"""
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
import logging


class AuthMiddleware:
    """认证中间件类"""

    def __init__(self, auth_config):
        """
        初始化认证中间件

        Args:
            auth_config: 认证配置字典
                {
                    'enabled': bool,
                    'username': str,
                    'password_hash': str,
                    'api_token': str
                }
        """
        self.auth_config = auth_config

    def require_auth(self, f):
        """
        认证装饰器（Session或API Token）

        Usage:
            @auth_middleware.require_auth
            def protected_route():
                return "Protected content"
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查是否启用认证
            if not self.auth_config.get('enabled', True):
                return f(*args, **kwargs)

            # 方式1: Session认证
            if session.get('authenticated'):
                return f(*args, **kwargs)

            # 方式2: API Token认证
            token = request.headers.get('Authorization')
            if token:
                # 支持 "Bearer TOKEN" 格式
                if token.startswith('Bearer '):
                    token = token[7:]

                if token == self.auth_config.get('api_token'):
                    return f(*args, **kwargs)

            # 认证失败
            if request.is_json or request.path.startswith('/api/'):
                # API请求返回JSON
                return jsonify({'success': False, 'message': '未授权访问'}), 401
            else:
                # Web请求重定向到登录页
                return redirect(url_for('auth.login', next=request.url))

        return decorated_function

    def require_api_token(self, f):
        """
        API Token认证装饰器（仅Token，不支持Session）

        Usage:
            @auth_middleware.require_api_token
            def api_route():
                return jsonify({"data": "..."})
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查是否启用认证
            if not self.auth_config.get('enabled', True):
                return f(*args, **kwargs)

            # 获取Token
            token = request.headers.get('Authorization')
            if token:
                if token.startswith('Bearer '):
                    token = token[7:]

                if token == self.auth_config.get('api_token'):
                    return f(*args, **kwargs)

            # 认证失败
            return jsonify({
                'success': False,
                'message': 'API Token无效或缺失',
                'hint': '请在请求头添加: Authorization: Bearer YOUR_TOKEN'
            }), 401

        return decorated_function

    def optional_auth(self, f):
        """
        可选认证装饰器
        如果已认证则提供用户信息，未认证也允许访问

        Usage:
            @auth_middleware.optional_auth
            def public_route():
                user = request.user  # None或用户信息
                return "Content"
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 检查Session
            if session.get('authenticated'):
                request.user = {
                    'username': session.get('username'),
                    'authenticated': True
                }
            else:
                request.user = None

            return f(*args, **kwargs)

        return decorated_function


# 创建全局实例的辅助函数
def create_auth_middleware(auth_config):
    """
    创建认证中间件实例

    Args:
        auth_config: 认证配置

    Returns:
        AuthMiddleware实例
    """
    return AuthMiddleware(auth_config)


# 示例使用
if __name__ == '__main__':
    # 示例配置
    config = {
        'enabled': True,
        'username': 'admin',
        'password_hash': '5f4dcc3b5aa765d61d8327deb882cf99',  # password
        'api_token': 'test-token-123'
    }

    middleware = AuthMiddleware(config)

    # 测试装饰器
    @middleware.require_auth
    def protected():
        return "Protected"

    print("认证中间件创建成功")
