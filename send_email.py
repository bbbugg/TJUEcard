import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def send_notification_email(sender_email: str, auth_code: str, recipient_email: str, subject: str, body: str) -> bool:
    """
    发送一封通知邮件。

    :param sender_email: 发件人的邮箱账号 (例如 '12345@qq.com')。
    :param auth_code: 发件人邮箱的SMTP授权码。
    :param recipient_email: 收件人的邮箱账号。
    :param subject: 邮件主题。
    :param body: 邮件正文内容。
    :return: 发送成功返回 True，否则返回 False。
    """
    ret = True
    try:
        # 创建邮件内容
        msg = MIMEText(body, 'plain', 'utf-8')
        # 设置邮件头部信息
        msg['From'] = formataddr(["TjuEcard电费查询助手", sender_email])  # 发件人昵称和账号
        msg['To'] = formataddr(["用户", recipient_email])  # 收件人昵称和账号
        msg['Subject'] = subject  # 邮件主题

        # 连接到QQ邮箱的SMTP服务器
        # 注意：SMTP_SSL默认使用465端口
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        # 登录邮箱
        server.login(sender_email, auth_code)
        # 发送邮件
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        # 关闭连接
        server.quit()
    except Exception as e:
        # 如果发生任何异常，则认为发送失败
        print(f"[错误] 邮件发送失败: {str(e)}")
        ret = False
    return ret
