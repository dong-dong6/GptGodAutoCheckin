"""
错误处理中间件
统一处理应用错误和异常
"""
from flask import jsonify, render_template_string
import logging
import traceback


class ErrorHandler:
    """错误处理器类"""

    def __init__(self, app=None):
        """
        初始化错误处理器

        Args:
            app: Flask应用实例（可选）
        """
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        注册错误处理器到Flask应用

        Args:
            app: Flask应用实例
        """
        self.app = app

        # 注册各种HTTP错误处理器
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(500, self.handle_internal_error)

        # 注册通用异常处理器
        app.register_error_handler(Exception, self.handle_exception)

        logging.info("错误处理器已注册")

    def handle_bad_request(self, error):
        """处理400错误"""
        logging.warning(f"Bad Request: {error}")
        return self._make_response(400, "请求参数错误", str(error))

    def handle_unauthorized(self, error):
        """处理401错误"""
        logging.warning(f"Unauthorized: {error}")
        return self._make_response(401, "未授权访问", "请先登录")

    def handle_forbidden(self, error):
        """处理403错误"""
        logging.warning(f"Forbidden: {error}")
        return self._make_response(403, "禁止访问", "您没有权限访问此资源")

    def handle_not_found(self, error):
        """处理404错误"""
        logging.debug(f"Not Found: {error}")
        return self._make_response(404, "页面不存在", "请求的资源未找到")

    def handle_internal_error(self, error):
        """处理500错误"""
        logging.error(f"Internal Server Error: {error}")
        logging.error(traceback.format_exc())
        return self._make_response(
            500,
            "服务器内部错误",
            "服务器处理请求时发生错误，请稍后重试"
        )

    def handle_exception(self, error):
        """处理未捕获的异常"""
        logging.error(f"Unhandled Exception: {error}")
        logging.error(traceback.format_exc())

        # 如果是HTTP异常，使用其状态码
        if hasattr(error, 'code'):
            status_code = error.code
        else:
            status_code = 500

        return self._make_response(
            status_code,
            "发生错误",
            str(error) if self.app.debug else "请求处理失败"
        )

    def _make_response(self, status_code, title, message):
        """
        创建错误响应

        Args:
            status_code: HTTP状态码
            title: 错误标题
            message: 错误消息

        Returns:
            Response对象
        """
        from flask import request

        # 如果是API请求，返回JSON
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': {
                    'code': status_code,
                    'title': title,
                    'message': message
                }
            }), status_code

        # Web请求返回HTML
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{status_code} - {title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 100px auto;
                    padding: 20px;
                    text-align: center;
                }}
                h1 {{
                    color: #e74c3c;
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #7f8c8d;
                    font-size: 16px;
                    line-height: 1.6;
                }}
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <h1>{status_code}</h1>
            <h2>{title}</h2>
            <p>{message}</p>
            <p><a href="/">返回首页</a></p>
        </body>
        </html>
        """

        return render_template_string(error_html), status_code


# 创建全局实例的辅助函数
def create_error_handler(app):
    """
    创建并注册错误处理器

    Args:
        app: Flask应用实例

    Returns:
        ErrorHandler实例
    """
    return ErrorHandler(app)


# 示例使用
if __name__ == '__main__':
    from flask import Flask

    app = Flask(__name__)
    error_handler = ErrorHandler(app)

    @app.route('/test-error')
    def test_error():
        raise Exception("测试错误")

    print("错误处理器创建成功")
