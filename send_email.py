import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr


def send_notification_email(sender_email: str, auth_code: str, recipient_email: str, subject: str, body: str) -> tuple[
    bool, str]:
    """
    发送一封通知邮件。

    :param sender_email: 发件人的邮箱账号 (例如 '12345@qq.com')。
    :param auth_code: 发件人邮箱的SMTP授权码。
    :param recipient_email: 收件人的邮箱账号。
    :param subject: 邮件主题。
    :param body: 邮件正文内容。
    :return: 一个元组 (成功状态, 错误信息)。发送成功返回 (True, "")，失败返回 (False, 具体错误信息)。
    """
    ret = True
    error_msg = ""
    try:
        # 创建邮件内容
        msg = MIMEText(body, 'plain', 'utf-8')
        # 设置邮件头部信息
        msg['From'] = formataddr(["TJUEcard电费查询助手", sender_email])  # 发件人昵称和账号
        msg['To'] = formataddr(["用户", recipient_email])  # 收件人昵称和账号
        msg['Subject'] = subject  # 邮件主题

        # 根据邮箱域名选择不同的SMTP服务器
        if '@' not in sender_email:
            error_msg = "邮箱地址格式不正确"
            print(f"[错误] {error_msg}")
            return False, error_msg

        domain = sender_email.split('@')[1].lower()

        if domain == 'qq.com':
            server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        elif domain == '163.com':
            server = smtplib.SMTP_SSL("imap.163.com", 465)
        else:
            error_msg = f"不支持的邮箱域名: {domain}"
            print(f"[错误] {error_msg}")
            return False, error_msg

        # 登录邮箱
        server.login(sender_email, auth_code)
        # 发送邮件
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        # 关闭连接
        server.quit()
    except Exception as e:
        # 如果发生任何异常，则认为发送失败
        error_msg = f"邮件发送失败: {str(e)}"
        print(f"[错误] {error_msg}")
        ret = False
    return ret, error_msg
