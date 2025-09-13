import requests
import pickle
import os
import json
import sys
import logging

# --- 1. 日志配置 ---
# 创建一个logger
logger = logging.getLogger('TjuEcardQuery')
logger.setLevel(logging.INFO)  # 设置日志级别

# 创建一个handler，用于写入日志文件，使用utf-8编码
file_handler = logging.FileHandler('TjuEcard.log', encoding='utf-8')

# 定义handler的输出格式
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)

# 给logger添加handler
logger.addHandler(file_handler)

# --- 2. 用户配置区 ---
BASE_DOMAIN = 'http://59.67.37.10:8180'
SELECTION_CACHE_FILE = 'selection_cache.json'
QUERY_URL = f'{BASE_DOMAIN}/epay/electric/queryelectricbill'
COOKIE_FILE = 'my_session.pkl'
VERIFY_LOGIN_URL = f'{BASE_DOMAIN}/epay/person/index'
LOAD_ELECTRIC_INDEX_URL = f'{BASE_DOMAIN}/epay/electric/load4electricindex'  # 用于Referer


# --- 3. 核心功能函数 ---
def load_cookies(session: requests.Session, file_name: str) -> bool:
    if not os.path.exists(file_name):
        msg = f"Cookie文件 '{file_name}' 不存在。"
        print(f"[错误] {msg}")
        logger.error(msg)
        return False
    with open(file_name, 'rb') as file:
        session.cookies.update(pickle.load(file))
    print("[信息] 已从本地加载会话。")
    return True


def extract_csrf_token(html_content: str) -> str | None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    csrf_meta_tag = soup.find('meta', {'name': '_csrf'})
    if csrf_meta_tag and csrf_meta_tag.has_attr('content'):
        return csrf_meta_tag['content']
    return None


def load_selection_from_cache(filename: str) -> dict | None:
    print("[信息] 正在读取房间选择缓存...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        msg = f"缓存文件 '{filename}' 不存在。"
        print(f"[错误] {msg}")
        logger.error(msg)
        return None
    except json.JSONDecodeError:
        msg = f"缓存文件 '{filename}' 格式错误，不是有效的JSON。"
        print(f"[错误] {msg}")
        logger.error(msg)
        return None

    required_keys = ['system', 'area', 'district', 'buis', 'floor', 'room']
    for key in required_keys:
        msg = ""
        if key not in data:
            msg = f"缓存文件校验失败：缺少顶级键 '{key}'。"
        elif not isinstance(data.get(key), dict) or 'id' not in data.get(key):
            msg = f"缓存文件校验失败：'{key}' 的内容格式不正确。"
        elif not data.get(key)['id']:
            msg = f"缓存文件校验失败：'{key}' 的 'id' 不能为空。"

        if msg:
            print(f"[错误] {msg}")
            logger.error(msg)
            return None

    print("[成功] 缓存文件校验通过。")
    return data


# --- 4. 主程序 ---
if __name__ == "__main__":
    logger.info("--- 查询脚本开始运行 ---")

    # 步骤1: 加载并验证缓存的房间选择
    cached_selection = load_selection_from_cache(SELECTION_CACHE_FILE)
    if not cached_selection:
        print("\n[操作建议] 请先运行 setup.py 来登录并选择一个房间。")
        logger.error("因缓存文件无效或不存在，脚本退出。")
        input("按回车键退出。")
        sys.exit(1)

    # 步骤2: 加载并验证会话Cookie
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    })

    if not load_cookies(session, COOKIE_FILE):
        print("\n[操作建议] 请运行 setup.py 重新登录。")
        logger.error("因Cookie文件不存在，脚本退出。")
        input("按回车键退出。")
        sys.exit(1)

    # 步骤3: 验证会话是否仍然有效
    print("[信息] 正在验证会话有效性...")
    try:
        verify_headers = session.headers.copy()
        del verify_headers['X-Requested-With']
        verify_response = session.get(VERIFY_LOGIN_URL, headers=verify_headers)
        verify_response.raise_for_status()
        if 'j_spring_security_check' in verify_response.text or 'j_username' in verify_response.text:
            msg = "会话已过期。"
            print(f"[错误] {msg}")
            logger.error(msg)
            print("\n[操作建议] 请运行 setup.py 重新登录。")
            input("按回车键退出。")
            sys.exit(1)
        else:
            print("[成功] 会话验证通过。")
    except requests.RequestException as e:
        msg = f"会话验证请求失败: {e}"
        print(f"[错误] {msg}")
        logger.error(msg)
        print("\n[操作建议] 请检查网络连接或运行 setup.py 重新登录。")
        input("按回车键退出。")
        sys.exit(1)

    # 步骤4: 准备并执行查询
    sel = cached_selection
    selected_sysid = sel['system']['id']
    token_page_url = f'{BASE_DOMAIN}/epay/electric/load4electricbill?elcsysid={selected_sysid}'
    query_payload = {
        'sysid': selected_sysid,
        'elcarea': sel['area']['id'],
        'elcbuis': sel['buis']['id'],
        'roomNo': sel['room']['id']
    }

    room_path = f"{sel['system']['name']} > {sel['area']['name']} > {sel['district']['name']} > {sel['buis']['name']} > {sel['floor']['name']} > {sel['room']['name']}"

    print("\n--- 开始查询电费 ---")
    print(f"查询目标: {room_path}")
    try:
        # 每次查询都需要获取最新的CSRF Token
        page_headers = session.headers.copy()
        del page_headers['X-Requested-With']
        page_headers['Referer'] = LOAD_ELECTRIC_INDEX_URL
        page_response = session.get(token_page_url, headers=page_headers)
        page_response.raise_for_status()
        final_csrf_token = extract_csrf_token(page_response.text)
        if not final_csrf_token:
            msg = "无法获取执行查询所需的CSRF Token！"
            print(f"[错误] {msg}")
            logger.error(msg)
            input("按回车键退出。")
            sys.exit(1)

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
        else:
            msg = f"查询失败: {result.get('retmsg')}"
            print(msg)
            logger.error(f"{msg} | 查询房间: {room_path} | 查询参数: {query_payload}")

    except (requests.RequestException, json.JSONDecodeError, Exception) as e:
        msg = f"查询过程中发生错误: {e}"
        print(msg)
        logger.error(f"{msg} | 查询房间: {room_path} | 查询参数: {query_payload}")

    logger.info("--- 查询脚本运行结束 ---\n")
    input("\n查询结束，按回车键退出。")
