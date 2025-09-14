import json
import requests
import sys
from bs4 import BeautifulSoup
from send_email import send_notification_email
from utils import save_cookies, load_cookies, extract_csrf_token, load_config, setup_logger
from config import (
    BASE_DOMAIN, USER_CONFIG_FILE, QUERY_URL, COOKIE_FILE, VERIFY_LOGIN_URL,
    LOGIN_PAGE_URL, LOGIN_URL, LOAD_ELECTRIC_INDEX_URL, DEFAULT_HEADERS
)

# --- 1. 日志配置 ---
logger = setup_logger('TJUEcardQuery')


# --- 2. 核心功能函数 ---


def perform_auto_login(session: requests.Session, username: str, password: str) -> bool:
    print("[信息] 正在尝试自动重新登录...")
    logger.info("尝试自动重新登录")
    try:
        page_response = session.get(LOGIN_PAGE_URL, timeout=10)  # 设置10秒超时
        page_response.raise_for_status()
        soup = BeautifulSoup(page_response.text, 'html.parser')
        csrf_input_tag = soup.find('input', {'name': '_csrf'})
        if not csrf_input_tag or not csrf_input_tag.has_attr('value'):
            logger.error("在登录页面中未找到CSRF token")
            return False
        csrf_token = csrf_input_tag['value']
    except requests.RequestException as e:
        logger.error(f"访问登录页面失败: {e}")
        return False

    login_data = {'j_username': username, 'j_password': password, '_csrf': csrf_token}
    try:
        headers = {'Referer': LOGIN_PAGE_URL, 'Origin': BASE_DOMAIN}
        response = session.post(LOGIN_URL, data=login_data, headers=headers, timeout=10)  # 设置10秒超时
        response.raise_for_status()
        if '<frameset' not in response.text:
            logger.error("登录失败，服务器返回的页面不包含预期内容")
            return False
        print("[成功] 自动重新登录成功！")
        logger.info("自动重新登录成功")
        return True
    except requests.RequestException as e:
        logger.error(f"登录请求失败: {e}")
        return False


# 处理重连逻辑
def handle_relogin(session: requests.Session, config: dict) -> bool:
    logger.info("开始处理重连逻辑")
    if "credentials" not in config or "username" not in config["credentials"] or "password" not in config[
        "credentials"]:
        msg = "配置文件中缺少登录凭据，无法自动登录。"
        print(f"[错误] {msg}")
        logger.error(msg)
        print(f"\n[操作建议] 请重新运行 setup 更新您的配置。")
        send_query_email(config, "【警告】电费查询失败通知", msg, -1)
        logger.info("--- 查询脚本运行结束 ---\n")
        sys.exit(1)

    # 2. 尝试登录
    credentials = config['credentials']
    logger.debug(f"使用用户名 {credentials['username']} 尝试自动登录")
    if perform_auto_login(session, credentials['username'], credentials['password']):
        save_cookies(session, COOKIE_FILE)
        logger.info("重连成功并保存新的会话")
        return True
    else:
        # 3. 处理登录失败
        msg = "自动重新登录失败。保存的密码可能已更改。"
        print(f"[错误] {msg}")
        logger.error(msg)
        print(f"\n[操作建议] 请重新运行 setup 更新您的配置。")
        send_query_email(config, "【警告】电费查询失败通知", msg, -1)
        logger.info("--- 查询脚本运行结束 ---\n")
        sys.exit(1)


# 一个辅助函数，用于发送查询结果邮件
def send_query_email(config: dict, subject: str, body: str, current_electricity: float):
    """检查配置并发送邮件，如果未配置则静默跳过。"""
    if not config:
        logger.warning("尝试发送邮件，但传入的config为None。")
        print("[警告] 未配置邮箱通知，无法发送邮件。")
        return  # 直接返回，不做任何事
    if "email_notifier" in config and config["email_notifier"].get("email") and config["email_notifier"].get(
            "auth_code"):
        notifier_config = config["email_notifier"]

        # 检查是否设置了通知阈值
        threshold = notifier_config.get("notification_threshold", -1)

        # 判断是否需要发送邮件
        if threshold >= 0 and current_electricity > threshold:
            # 当前电量高于阈值且不是失败通知，则不发送邮件
            logger.info(f"剩余电量({current_electricity}度)高于设置的通知阈值({threshold}度)，不发送邮件。")
            print(f"[信息] 剩余电量({current_electricity}度)高于设置的通知阈值({threshold}度)，不发送邮件。")
            return

        print("[信息] 正在发送邮件通知...")
        success, error_msg = send_notification_email(
            sender_email=notifier_config["email"],
            auth_code=notifier_config["auth_code"],
            recipient_email=notifier_config["email"],
            subject=subject,
            body=body
        )
        if success:
            logger.info(f"邮件通知发送成功到{notifier_config['email']}。")
            print("[成功] 邮件通知发送成功。")
        else:
            print(f"[警告] 邮件通知发送失败，请检查 setup 中的邮箱配置。")
            logger.error(f"邮件通知发送失败到{notifier_config['email']}。错误信息: {error_msg}")
            logger.debug(
                f"发送邮件详细信息: 发件人={notifier_config['email']}, 收件人={notifier_config['email']}, 主题={subject}")
    else:
        logger.info("未配置邮箱通知，跳过发送邮件。")
        # 如果配置文件中没有邮箱信息，则不执行任何操作
        pass


# --- 4. 主程序 ---
if __name__ == "__main__":
    logger.info("--- 查询脚本开始运行 ---")

    config = load_config(USER_CONFIG_FILE)
    if not config:
        msg = "因配置文件中房间参数无效或不存在，脚本退出。"
        logger.error(msg)
        print(f"\n[操作建议] 请先运行 setup 来生成 {USER_CONFIG_FILE}。")
        logger.info("--- 查询脚本运行结束 ---\n")
        sys.exit(1)

    selection = config['selection']

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    })

    is_session_valid = False
    if load_cookies(session, COOKIE_FILE):
        print("[信息] 正在验证会话有效性...")
        try:
            verify_headers = session.headers.copy()
            del verify_headers['X-Requested-With']
            verify_response = session.get(VERIFY_LOGIN_URL, headers=verify_headers, timeout=10)  # 设置10秒超时
            verify_response.raise_for_status()
            if 'j_spring_security_check' not in verify_response.text and 'j_username' not in verify_response.text:
                print("[成功] 会话验证通过。")
                logger.info("会话验证通过")
                is_session_valid = True
            else:
                print("[警告] 会话已过期。")
                logger.warning("会话已过期")
        except requests.RequestException as e:
            print("[警告] 会话验证请求失败。")
            logger.warning(f"会话验证请求失败: {e}")

    if not is_session_valid:
        print("[信息] 会话无效或不存在，尝试使用配置文件自动登录...")
        logger.info("会话无效或不存在，尝试使用配置文件自动登录")
        if handle_relogin(session, config):
            is_session_valid = True

    # --- 执行查询 ---
    selected_sysid = selection['system']['id']
    token_page_url = f'{BASE_DOMAIN}/epay/electric/load4electricbill?elcsysid={selected_sysid}'
    query_payload = {
        'sysid': selected_sysid,
        'elcarea': selection['area']['id'],
        'elcbuis': selection['buis']['id'],
        'roomNo': selection['room']['id']
    }
    room_path = (f"{selection['system']['name']} > {selection['area']['name']} > {selection['district']['name']} > "
                 f"{selection['buis']['name']} > {selection['floor']['name']} > {selection['room']['name']}")

    print(f"\n--- 开始查询电费: {room_path} ---")

    query_successful = False
    final_message = ""  # 用于邮件内容
    remaining_electricity = None  # 初始化剩余电量变量

    for attempt in range(2):
        try:
            page_headers = session.headers.copy()
            del page_headers['X-Requested-With']
            page_headers['Referer'] = LOAD_ELECTRIC_INDEX_URL
            page_response = session.get(token_page_url, headers=page_headers, timeout=10)  # 设置10秒超时
            page_response.raise_for_status()
            final_csrf_token = extract_csrf_token(page_response.text)

            if not final_csrf_token:
                # 将获取Token失败视为会话过期
                msg = "无法获取执行查询所需的CSRF Token，可能由于会话失效。"
                print(f"[警告] {msg}")
                logger.warning(msg)

                if attempt == 0:  # 如果是第一次尝试，则进行重连
                    print("[信息] 正在触发自动重连...")
                    # 【关键修改】第二次调用新的重连函数
                    if handle_relogin(session, config):
                        print("[信息] 重连成功，正在重试查询...")
                        logger.info("重连成功，重试查询。")
                        continue
                else:
                    final_message = "重试后依然无法获取Token。"
                    print(f"[错误] {final_message}")
                    logger.error(final_message)
                    break

            # 执行查询
            query_headers = {
                'X-CSRF-TOKEN': final_csrf_token,
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': token_page_url
            }
            query_response = session.post(QUERY_URL, data=query_payload, headers=query_headers, timeout=10)  # 设置10秒超时
            query_response.raise_for_status()
            result = query_response.json()

            # 显示并记录结果
            if result.get('retcode') == 0:
                result_text = ""
                if result.get('multiflag'):
                    print("\n========================\n查询成功！(该房间为一房多表模式)")
                    meter_results = []
                    for meter in result.get('elecRoomData', []):
                        line = f"  - {meter.get('name')}: 剩余电量 {meter.get('restElecDegree')} 度"
                        print(line)
                        meter_results.append(line.strip())
                    print("========================")
                    result_text = " | ".join(meter_results)
                    current_elec = float(result.get('elecRoomData', [{}])[0].get('restElecDegree', 0))
                else:
                    remaining_electricity = result.get('restElecDegree')
                    current_elec = float(remaining_electricity)
                    print("\n========================")
                    print(f"查询成功！剩余电量: {remaining_electricity} 度")
                    print("========================")
                    result_text = f"剩余电量: {remaining_electricity} 度"

                # 记录成功日志
                logger.info(
                    "查询成功。\n"
                    f"\t查询房间: {room_path}\n"
                    f"\t查询参数: {query_payload}\n"
                    f"\t查询结果: {result_text}"
                )
                query_successful = True
                final_message = f"查询房间: {room_path}\n\n查询结果:\n{result_text}"
                break  # 查询成功，跳出循环
            else:
                msg = f"查询失败: {result.get('retmsg')}"
                print(msg)
                logger.error(f"{msg} | 查询房间: {room_path} | 查询参数: {query_payload}")
                final_message = f"查询房间: {room_path}\n\n查询失败，服务器返回信息: {result.get('retmsg')}"
                break  # 服务器返回错误，无需重试

        except (requests.RequestException, json.JSONDecodeError, Exception) as e:
            msg = f"查询过程中发生错误: {e}"
            print(f"[错误] {msg}")
            logger.error(f"{msg} | 查询房间: {room_path} | 查询参数: {query_payload}")
            final_message = f"查询房间: {room_path}\n\n查询脚本在执行过程中遇到一个错误: {e}"
            if attempt == 0 and isinstance(e, requests.RequestException):
                print("[信息] 网络错误，尝试重新连接...")
                logger.info("网络错误，尝试重新连接")
                if handle_relogin(session, config):
                    print("[信息] 重连成功，重试查询...")
                    logger.info("重连成功，重试查询")
                    continue
            break  # 发生异常，无需重试

    # 无论成功失败，都在最后发送邮件
    if query_successful:
        send_query_email(config, "电费查询成功通知", final_message, current_elec)
    else:
        send_query_email(config, "【警告】电费查询失败通知", final_message, -1)
        print("\n[操作建议] 请检查网络或运行 setup 刷新配置。")

    logger.info("--- 查询脚本运行结束 ---\n")
