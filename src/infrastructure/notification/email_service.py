"""
邮件通知服务
提供邮件发送功能
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
            sender_email = self.smtp_config.get('sender_email', '')
            sender_password = self.smtp_config.get('sender_password', '')

            # 确定收件人
            if to_emails is None:
                receiver_emails = self.smtp_config.get('receiver_emails', [])
            else:
                receiver_emails = to_emails

            # 验证配置
            if not sender_email or not sender_password:
                logging.warning("邮件发送者配置不完整")
                return False

            if not receiver_emails:
                logging.warning("没有指定收件人")
                return False

            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(receiver_emails) if isinstance(receiver_emails, list) else receiver_emails
            msg['Subject'] = subject

            # 添加邮件正文
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))

            # 发送邮件
            if smtp_port == 465:
                # SSL端口
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(sender_email, sender_password)
                    self._send_to_recipients(server, msg, sender_email, receiver_emails)
            else:
                # TLS端口
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    self._send_to_recipients(server, msg, sender_email, receiver_emails)

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
        发送签到通知邮件

        Args:
            results: 签到结果列表
            success_count: 成功数量
            failed_count: 失败数量

        Returns:
            bool: 是否发送成功
        """
        subject = f"GPT-GOD自动签到结果 - 成功{success_count}，失败{failed_count}"

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
            <h2>GPT-GOD自动签到结果</h2>
            <div class="summary">
                <p><strong>总计:</strong> {success_count + failed_count} 个账号</p>
                <p class="success"><strong>成功:</strong> {success_count}</p>
                <p class="failed"><strong>失败:</strong> {failed_count}</p>
            </div>
            <h3>详细结果:</h3>
        """

        # 添加每个账号的结果
        for result in results.get('results', []):
            status_class = 'success' if result.get('success') else 'failed'
            status_icon = '✅' if result.get('success') else '❌'
            email = result.get('email', 'Unknown')
            message = result.get('message', 'No message')

            body += f"""
            <div class="result-item {status_class}">
                <p>{status_icon} <strong>{email}</strong></p>
                <p>{message}</p>
            </div>
            """

        body += """
        </body>
        </html>
        """

        return self.send_email(subject, body, html=True)

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
