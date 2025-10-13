"""
邮件通知服务
提供邮件发送功能
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from typing import List, Optional, Dict, Any


class EmailService:
    """邮件服务类"""

    def __init__(self, smtp_config: Optional[Dict[str, Any]] = None):
        """
        初始化邮件服务

        Args:
            smtp_config: SMTP配置字典
                {
                    'enabled': bool,
                    'server': str,
                    'port': int,
                    'sender_email': str,
                    'sender_name': str,
                    'sender_password': str,
                    'receiver_emails': List[str] or str
                }
        """
        self.smtp_config = smtp_config or {}

    def send_email(
        self,
        subject: str,
        body: str,
        html: bool = True,
        to_emails: Optional[List[str]] = None
    ) -> bool:
        """
        发送邮件

        Args:
            subject: 邮件主题
            body: 邮件正文
            html: 是否为HTML格式
            to_emails: 收件人列表（可选，不提供则使用配置中的默认收件人）

        Returns:
            bool: 是否发送成功
        """
        try:
            # 检查是否启用
            if not self.smtp_config.get('enabled', False):
                logging.info("邮件通知功能未启用")
                return False

            # 获取配置
            smtp_server = self.smtp_config.get('server', 'smtp.gmail.com')
            smtp_port = self.smtp_config.get('port', 587)
            auth_email = self.smtp_config.get('sender_email', '')  # 认证邮箱
            auth_password = self.smtp_config.get('sender_password', '')
            from_email = self.smtp_config.get('from_email', '') or auth_email  # 代发邮箱，默认使用认证邮箱
            sender_name = self.smtp_config.get('sender_name', '')  # 显示名称

            # 确定收件人
            if to_emails is None:
                receiver_emails = self.smtp_config.get('receiver_emails', [])
            else:
                receiver_emails = to_emails

            # 验证配置
            if not auth_email or not auth_password:
                logging.warning("SMTP认证配置不完整")
                return False

            if not receiver_emails:
                logging.warning("没有指定收件人")
                return False

            # 构建发件人显示信息
            if sender_name:
                # 使用发件人名称 + 代发邮箱地址
                from_addr = formataddr((sender_name, from_email))
            else:
                # 只使用代发邮箱地址
                from_addr = from_email

            logging.info(f"邮件发送: 认证邮箱={auth_email}, 发件邮箱={from_email}, 发件人名称={sender_name or '(无)'}")

            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ', '.join(receiver_emails) if isinstance(receiver_emails, list) else receiver_emails
            msg['Subject'] = subject

            # 添加邮件正文
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))

            # 发送邮件
            if smtp_port == 465:
                # SSL端口
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(auth_email, auth_password)  # 使用认证邮箱登录
                    self._send_to_recipients(server, msg, from_email, receiver_emails)  # 使用代发邮箱作为发件人
            else:
                # TLS端口
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(auth_email, auth_password)  # 使用认证邮箱登录
                    self._send_to_recipients(server, msg, from_email, receiver_emails)  # 使用代发邮箱作为发件人

            logging.info(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            logging.error(f"发送邮件失败: {str(e)}", exc_info=True)
            return False

    def _send_to_recipients(
        self,
        server: smtplib.SMTP,
        msg: MIMEMultipart,
        sender: str,
        recipients: List[str] or str
    ) -> None:
        """
        向收件人发送邮件

        Args:
            server: SMTP服务器连接
            msg: 邮件消息
            sender: 发件人
            recipients: 收件人列表
        """
        if isinstance(recipients, list):
            for receiver in recipients:
                server.send_message(msg, from_addr=sender, to_addrs=[receiver])
        else:
            server.send_message(msg, from_addr=sender, to_addrs=[recipients])

    def send_checkin_notification(
        self,
        results: Dict[str, Any],
        success_count: int,
        failed_count: int
    ) -> bool:
        """
        发送全局签到通知邮件（发送给全局配置的收件人）

        Args:
            results: 签到结果列表
            success_count: 成功数量
            failed_count: 失败数量

        Returns:
            bool: 是否发送成功
        """
        subject = f"GPT-GOD自动签到汇总 - 成功{success_count}，失败{failed_count}"

        # 构建HTML正文
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .summary {{
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .success {{ color: #28a745; }}
                .failed {{ color: #dc3545; }}
                .result-item {{
                    padding: 10px;
                    margin: 5px 0;
                    border-left: 3px solid #ccc;
                }}
                .result-item.success {{ border-left-color: #28a745; }}
                .result-item.failed {{ border-left-color: #dc3545; }}
            </style>
        </head>
        <body>
            <h2>GPT-GOD自动签到汇总报告</h2>
            <div class="summary">
                <p><strong>本次签到总计:</strong> {success_count + failed_count} 个账号</p>
                <p class="success"><strong>签到成功:</strong> {success_count} 个账号</p>
                <p class="failed"><strong>签到失败:</strong> {failed_count} 个账号</p>
            </div>
            <h3>各账号详细结果:</h3>
        """

        # 添加每个账号的结果
        for result in results.get('results', []):
            status_class = 'success' if result.get('success') else 'failed'
            status_icon = '✅' if result.get('success') else '❌'
            email = result.get('email', 'Unknown')
            message = result.get('message', 'No message')
            points_info = ""

            if result.get('current_points', 0) > 0:
                points_info = f"<p>当前积分: {result['current_points']}</p>"

            body += f"""
            <div class="result-item {status_class}">
                <p>{status_icon} <strong>{email}</strong></p>
                <p>{message}</p>
                {points_info}
            </div>
            """

        body += """
            <hr>
            <p style="color: #666; font-size: 12px;">
                此邮件为系统自动发送，包含所有账号的签到结果汇总。<br>
                如需取消订阅，请联系系统管理员。
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)

    def send_personal_checkin_notification(
        self,
        account_result: Dict[str, Any]
    ) -> bool:
        """
        发送个人签到通知邮件（发送给配置了邮件通知的账号本人）

        Args:
            account_result: 单个账号的签到结果

        Returns:
            bool: 是否发送成功
        """
        email = account_result.get('email', '')
        success = account_result.get('success', False)
        message = account_result.get('message', '')
        current_points = account_result.get('current_points', 0)
        domain = account_result.get('domain', '')

        # 构建主题和内容
        if success:
            subject = "✅ GPT-GOD签到成功通知"
            status_icon = "✅"
            status_text = "签到成功"
            status_color = "#28a745"
        else:
            subject = "❌ GPT-GOD签到失败通知"
            status_icon = "❌"
            status_text = "签到失败"
            status_color = "#dc3545"

        # 构建HTML正文
        body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f8f9fa;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .status {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                .content {{
                    padding: 30px;
                }}
                .info-card {{
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 15px 0;
                }}
                .info-item {{
                    display: flex;
                    justify-content: space-between;
                    margin: 10px 0;
                    padding: 8px 0;
                    border-bottom: 1px solid #e9ecef;
                }}
                .info-label {{
                    font-weight: bold;
                    color: #495057;
                }}
                .info-value {{
                    color: {status_color};
                    font-weight: bold;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="status">{status_icon}</div>
                    <h1>{status_text}</h1>
                    <p>GPT-GOD 自动签到系统通知</p>
                </div>

                <div class="content">
                    <div class="info-card">
                        <div class="info-item">
                            <span class="info-label">账号邮箱:</span>
                            <span class="info-value">{email}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">签到状态:</span>
                            <span class="info-value">{status_text}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">签到域名:</span>
                            <span class="info-value">{domain}</span>
                        </div>
                        {f'<div class="info-item"><span class="info-label">当前积分:</span><span class="info-value">{current_points}</span></div>' if current_points > 0 else ''}
                        <div class="info-item">
                            <span class="info-label">详细信息:</span>
                            <span class="info-value">{message}</span>
                        </div>
                    </div>

                    {f'<div style="color: {status_color}; text-align: center; font-size: 16px; margin: 20px 0;"><strong>🎉 恭喜您今日签到成功！</strong></div>' if success else '<div style="color: {status_color}; text-align: center; font-size: 16px; margin: 20px 0;"><strong>❌ 签到失败，请检查账号状态</strong></div>'}
                </div>

                <div class="footer">
                    <p>此邮件为系统自动发送，仅包含您个人账号的签到结果</p>
                    <p>如需取消此通知，请联系系统管理员或在设置中关闭</p>
                    <p>发送时间: {account_result.get('timestamp', '')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 发送给账号本人
        return self.send_email(subject, body, html=True, to_emails=[email])

    def send_error_notification(self, error_message: str, context: str = "") -> bool:
        """
        发送错误通知邮件

        Args:
            error_message: 错误信息
            context: 错误上下文

        Returns:
            bool: 是否发送成功
        """
        subject = "GPT-GOD自动签到系统 - 错误通知"

        body = f"""
        <html>
        <body>
            <h2>系统错误通知</h2>
            <p><strong>错误信息:</strong></p>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 3px;">{error_message}</pre>
        """

        if context:
            body += f"""
            <p><strong>错误上下文:</strong></p>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 3px;">{context}</pre>
            """

        body += """
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)


# 创建全局实例的辅助函数
def create_email_service(smtp_config: Dict[str, Any]) -> EmailService:
    """
    创建邮件服务实例

    Args:
        smtp_config: SMTP配置

    Returns:
        EmailService实例
    """
    return EmailService(smtp_config)


# 示例使用
if __name__ == '__main__':
    # 示例配置
    config = {
        'enabled': True,
        'server': 'mail.example.com',
        'port': 465,
        'sender_email': 'sender@example.com',
        'sender_name': 'GPT-GOD 签到系统',
        'sender_password': 'password',
        'receiver_emails': ['receiver@example.com']
    }

    service = EmailService(config)

    # 发送测试邮件
    success = service.send_email(
        subject="测试邮件",
        body="<h1>这是一封测试邮件</h1>",
        html=True
    )

    print(f"邮件发送: {'成功' if success else '失败'}")
