import requests
import pickle
import os
import json
import sys
import logging
from bs4 import BeautifulSoup

# --- 1. 日志配置 ---
logger = logging.getLogger('TjuEcardQuery')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('TjuEcard.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- 2. 用户配置区 ---
BASE_DOMAIN = 'http://59.67.37.10:8180'
USER_CONFIG_FILE = 'user_config.json'
QUERY_URL = f'{BASE_DOMAIN}/epay/electric/queryelectricbill'
COOKIE_FILE = 'my_session.pkl'
VERIFY_LOGIN_URL = f'{BASE_DOMAIN}/epay/person/index'
LOGIN_PAGE_URL = f'{BASE_DOMAIN}/epay/person/index'
LOGIN_URL = f'{BASE_DOMAIN}/epay/j_spring_security_check'
LOAD_ELECTRIC_INDEX_URL = f'{BASE_DOMAIN}/epay/electric/load4electricindex'


# --- 3. 核心功能函数 ---
def save_cookies(session: requests.Session, file_name: str) -> None:
    with open(file_name, 'wb') as file: pickle.dump(session.cookies, file)
    print(f"[信息] 新的会话已保存到 {file_name}")


def load_cookies(session: requests.Session, file_name: str) -> bool:
    if not os.path.exists(file_name):
        return False
    with open(file_name, 'rb') as file:
        session.cookies.update(pickle.load(file))
    print("[信息] 已从本地加载会话。")
    return True


def extract_csrf_token(html_content: str) -> str | None:
    soup = BeautifulSoup(html_content, 'html.parser')
    csrf_meta_tag = soup.find('meta', {'name': '_csrf'})
    if csrf_meta_tag and csrf_meta_tag.has_attr('content'):
        return csrf_meta_tag['content']
    return None


def load_config(filename: str) -> dict | None:
    print("[信息] 正在读取用户配置文件...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        msg = f"配置文件 '{filename}' 不存在。"
        print(f"[错误] {msg}")
        logger.error(msg)
        return None
    except json.JSONDecodeError:
        msg = f"配置文件 '{filename}' 格式错误，不是有效的JSON。"
        print(f"[错误] {msg}")
        logger.error(msg)
        return None

    if "selection" not in data:
        print("[错误] 配置文件缺少'selection'部分。")
        return None

    required_keys = ['system', 'area', 'district', 'buis', 'floor', 'room']
    for key in required_keys:
        msg = ""
        if key not in data["selection"]:
            msg = f"配置文件校验失败：缺少顶级键 '{key}'。"
        elif not isinstance(data["selection"].get(key), dict) or 'id' not in data["selection"].get(key):
            msg = f"配置文件校验失败：'{key}' 的内容格式不正确。"
        elif not data["selection"].get(key)['id']:
            msg = f"配置文件校验失败：'{key}' 的 'id' 不能为空。"

        if msg:
            print(f"[错误] {msg}")
            logger.error(msg)
            return None

    print("[成功] 配置文件校验通过。")
    return data


def perform_auto_login(session: requests.Session, username: str, password: str) -> bool:
    print("[信息] 正在尝试自动重新登录...")
    try:
        page_response = session.get(LOGIN_PAGE_URL)
        page_response.raise_for_status()
        soup = BeautifulSoup(page_response.text, 'html.parser')
        csrf_input_tag = soup.find('input', {'name': '_csrf'})
        if not csrf_input_tag or not csrf_input_tag.has_attr('value'):
            return False
        csrf_token = csrf_input_tag['value']
    except requests.RequestException:
        return False

    login_data = {'j_username': username, 'j_password': password, '_csrf': csrf_token}
    try:
        headers = {'Referer': LOGIN_PAGE_URL, 'Origin': BASE_DOMAIN}
        response = session.post(LOGIN_URL, data=login_data, headers=headers)
        response.raise_for_status()
        if '<frameset' not in response.text:
            return False
        print("[成功] 自动重新登录成功！")
        return True
    except requests.RequestException:
        return False


# ==============================================================================
# 【新增】这是我们封装的新函数，用于处理重连逻辑
# ==============================================================================
def handle_relogin(session: requests.Session, config: dict) -> bool:
    """
    处理自动重新登录的完整逻辑。
    检查凭据 -> 尝试登录 -> 保存Cookie -> 处理失败。
    :param session: requests的会话对象。
    :param config: 加载后的配置字典。
    :return: 登录成功返回 True，失败则直接退出脚本。
    """
    # 1. 检查凭据是否存在
    if "credentials" not in config or "username" not in config["credentials"] or "password" not in config[
        "credentials"]:
        msg = "配置文件中缺少登录凭据，无法自动登录。"
        print(f"[错误] {msg}")
        logger.error(msg)
        print(f"\n[操作建议] 请重新运行 setup.py 更新您的配置。")
        input("按回车键退出。")
        sys.exit(1)

    # 2. 尝试登录
    credentials = config['credentials']
    if perform_auto_login(session, credentials['username'], credentials['password']):
        save_cookies(session, COOKIE_FILE)
        return True
    else:
        # 3. 处理登录失败
        msg = "自动重新登录失败。保存的密码可能已更改。"
        print(f"[错误] {msg}")
        logger.error(msg)
        print(f"\n[操作建议] 请重新运行 setup.py 更新您的配置。")
        input("按回车键退出。")
        sys.exit(1)


# ==============================================================================

# --- 4. 主程序 ---
if __name__ == "__main__":
    logger.info("--- 查询脚本开始运行 ---")

    config = load_config(USER_CONFIG_FILE)
    if not config:
        msg = "因配置文件中房间参数无效或不存在，脚本退出。"
        logger.error(msg)
        print(f"\n[操作建议] 请先运行 setup.py 来生成 {USER_CONFIG_FILE}。")
        input("按回车键退出。")
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
            verify_response = session.get(VERIFY_LOGIN_URL, headers=verify_headers)
            verify_response.raise_for_status()
            if 'j_spring_security_check' not in verify_response.text and 'j_username' not in verify_response.text:
                print("[成功] 会话验证通过。")
                is_session_valid = True
            else:
                print("[警告] 会话已过期。")
        except requests.RequestException:
            print("[警告] 会话验证请求失败。")

    # 【关键修改】当会话无效时，调用新的重连函数
    if not is_session_valid:
        print("[信息] 会话无效或不存在，尝试使用配置文件自动登录...")
        logger.info("会话无效或不存在，尝试使用配置文件自动登录")
        # 直接调用封装好的函数，如果成功，则更新会话状态
        if handle_relogin(session, config):
            is_session_valid = True
        # 注意：如果 handle_relogin 失败，脚本会直接退出，所以不需要 else 分支

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
    for attempt in range(2):  # 最多尝试2次
        try:
            page_headers = session.headers.copy()
            del page_headers['X-Requested-With']
            page_headers['Referer'] = LOAD_ELECTRIC_INDEX_URL
            page_response = session.get(token_page_url, headers=page_headers)
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
                        continue  # 重连成功，继续下一次循环（即重试）
                    # 如果重连失败，handle_relogin 会直接退出，所以下面的代码不会执行
                else:  # 如果是第二次尝试仍然失败
                    print("[错误] 重试后依然无法获取Token。")
                    logger.error("重试后依然无法获取Token。")
                    break

            # 执行查询
            query_headers = {
                'X-CSRF-TOKEN': final_csrf_token,
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': token_page_url
            }
            query_response = session.post(QUERY_URL, data=query_payload, headers=query_headers)
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
                else:
                    remaining_electricity = result.get('restElecDegree')
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
                break  # 查询成功，跳出循环
            else:
                msg = f"查询失败: {result.get('retmsg')}"
                print(msg)
                logger.error(f"{msg} | 查询房间: {room_path} | 查询参数: {query_payload}")
                break  # 服务器返回错误，无需重试

        except (requests.RequestException, json.JSONDecodeError, Exception) as e:
            msg = f"查询过程中发生错误: {e}"
            print(msg)
            logger.error(f"{msg} | 查询房间: {room_path} | 查询参数: {query_payload}")
            break  # 发生异常，无需重试

    if not query_successful:
        print("\n[操作建议] 请检查网络或运行 setup.py 刷新配置。")

    logger.info("--- 查询脚本运行结束 ---\n")
    input("\n查询结束，按回车键退出。")
