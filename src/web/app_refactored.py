"""
Flask Web应用入口 - 重构版
整合所有路由模块，提供Web管理界面
"""
from flask import Flask
import logging

# 导入所有路由蓝图
from src.web.routes.auth_routes import auth_bp, init_auth_routes
from src.web.routes.config_routes import config_bp
from src.web.routes.checkin_routes import checkin_bp
from src.web.routes.points_routes import points_bp
from src.web.routes.logs_routes import logs_bp
from src.web.routes.redeem_routes import redeem_bp


def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)

    # 基础配置
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # 应该从环境变量或配置文件读取
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30天

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/web_service.log', mode='a', encoding='utf-8')
        ]
    )

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(points_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(redeem_bp)

    logging.info("Flask应用创建成功，所有路由已注册")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
