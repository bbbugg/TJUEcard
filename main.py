import requests
from bs4 import BeautifulSoup
import pickle
import os
import time
import json

# --- 1. 用户配置区 (无变化) ---
BASE_DOMAIN = 'http://59.67.37.10:8180'
SELECTION_CACHE_FILE = 'selection_cache.json'
LOAD_ELECTRIC_INDEX_URL = f'{BASE_DOMAIN}/epay/electric/load4electricindex'
LOGIN_URL = f'{BASE_DOMAIN}/epay/j_spring_security_check'
QUERY_URL = f'{BASE_DOMAIN}/epay/electric/queryelectricbill'
COOKIE_FILE = 'my_session.pkl'
LOGIN_PAGE_URL = f'{BASE_DOMAIN}/epay/person/index'
VERIFY_LOGIN_URL = f'{BASE_DOMAIN}/epay/person/index'
API_BASE_URL = f'{BASE_DOMAIN}/epay/electric'
API_URLS = {
    'area': f'{API_BASE_URL}/queryelectricarea',
    'district': f'{API_BASE_URL}/queryelectricdistricts',
    'buis': f'{API_BASE_URL}/queryelectricbuis',
    'floor': f'{API_BASE_URL}/queryelectricfloors',
    'room': f'{API_BASE_URL}/queryelectricrooms'
}
KEY_MAP = {
    'area': {'list': 'areas', 'id': 'areaId', 'name': 'areaName'},
    'district': {'list': 'districts', 'id': 'districtId', 'name': 'districtName'},
    'buis': {'list': 'buils', 'id': 'buiId', 'name': 'buiName'},
    'floor': {'list': 'floors', 'id': 'floorId', 'name': 'floorName'},
    'room': {'list': 'rooms', 'id': 'roomId', 'name': 'roomName'},
}


# --- 2. 核心功能函数 (无变化) ---
def save_cookies(session: requests.Session, file_name: str) -> None:
    with open(file_name, 'wb') as file: pickle.dump(session.cookies, file)
    print(f"会话已成功保存到 {file_name}")


def load_cookies(session: requests.Session, file_name: str) -> None:
    with open(file_name, 'rb') as file: session.cookies.update(pickle.load(file))
    print(f"已从 {file_name} 加载会话")


def extract_csrf_token(html_content: str) -> str | None:
    soup = BeautifulSoup(html_content, 'html.parser')
    csrf_meta_tag = soup.find('meta', {'name': '_csrf'})
    if csrf_meta_tag and csrf_meta_tag.has_attr('content'):
        return csrf_meta_tag['content']
    return None


def perform_login(session: requests.Session) -> bool:
    print("Cookie 文件无效或不存在，需要手动登录。")
    try:
        page_response = session.get(LOGIN_PAGE_URL)
        page_response.raise_for_status()
        soup = BeautifulSoup(page_response.text, 'html.parser')
        csrf_input_tag = soup.find('input', {'name': '_csrf'})
        if not csrf_input_tag or not csrf_input_tag.has_attr('value'):
            print("错误：在登录页面中未找到 _csrf token！")
            return False
        csrf_token = csrf_input_tag['value']
    except requests.RequestException as e:
        print(f"访问登录页面失败: {e}")
        return False

    username = input("请输入用户名: ")
    password = input("请输入密码: ")
    login_data = {'j_username': username, 'j_password': password, '_csrf': csrf_token}
    try:
        headers = {'Referer': LOGIN_PAGE_URL, 'Origin': BASE_DOMAIN}
        response = session.post(LOGIN_URL, data=login_data, headers=headers)
        response.raise_for_status()
        if '<frameset' not in response.text:
            print("登录失败！请检查用户名或密码。")
            return False
        print("登录成功！")
        save_cookies(session, COOKIE_FILE)
        return True
    except requests.RequestException as e:
        print(f"登录请求失败: {e}")
        return False


# --- 3. 交互式查询与缓存函数 ---
def get_user_choice(options: list) -> dict | None:
    if not options:
        print("未找到可用选项。")
        return None
    for i, option in enumerate(options): print(f"  [{i + 1}] {option['name']}")
    print("  [0] 返回上一步/退出")
    while True:
        try:
            choice = int(input("请输入您的选择 (数字): "))
            if 0 <= choice <= len(options):
                if choice == 0: return None
                return options[choice - 1]
            else:
                print("无效的输入，请输入列表中的数字。")
        except ValueError:
            print("无效的输入，请输入一个数字。")


def fetch_options(session: requests.Session, level: str, payload: dict, csrf_token: str, token_page_url: str) -> list:
    url = API_URLS[level]
    map_keys = KEY_MAP[level]
    normalized_options = []
    try:
        time.sleep(0.3)
        api_headers = {'X-CSRF-TOKEN': csrf_token, 'Referer': token_page_url}
        response = session.post(url, data=payload, headers=api_headers)
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"错误：服务器在请求 '{level}' 列表时没有返回有效的JSON。")
            return []
        raw_list = data.get(map_keys['list'], [])
        for item in raw_list:
            normalized_options.append({'id': str(item[map_keys['id']]), 'name': str(item[map_keys['name']])})
        return normalized_options
    except requests.RequestException as e:
        print(f"获取 {level} 列表时发生网络错误: {e}")
    return []


def interactive_query_flow(session: requests.Session, csrf_token: str, sysid: str, token_page_url: str) -> dict | None:
    print("\n--- 正在自动选择默认校区 ---")
    area_options = fetch_options(session, 'area', {'sysid': sysid}, csrf_token, token_page_url)
    if not area_options:
        print("错误：无法获取校区列表。")
        return None
    selected_area = area_options[0]
    print(f"已自动选择: {selected_area['name']}")
    selected_district = None
    selected_buis = None
    selected_floor = None
    selected_room = None
    while True:
        if not selected_district:
            print("\n--- 请选择缴费区域 ---")
            district_payload = {'sysid': sysid, 'area': selected_area['id']}
            district_options = fetch_options(session, 'district', district_payload, csrf_token, token_page_url)
            choice = get_user_choice(district_options)
            if not choice: return None
            selected_district = choice
            continue
        if not selected_buis:
            print("\n--- 请选择缴费楼栋 ---")
            buis_payload = {'sysid': sysid, 'area': selected_area['id'], 'district': selected_district['id']}
            buis_options = fetch_options(session, 'buis', buis_payload, csrf_token, token_page_url)
            choice = get_user_choice(buis_options)
            if not choice:
                selected_district = None
                print("\n返回上一步...")
                continue
            selected_buis = choice
            continue
        if not selected_floor:
            print("\n--- 请选择缴费楼层 ---")
            floor_payload = {'sysid': sysid, 'area': selected_area['id'], 'district': selected_district['id'],
                             'build': selected_buis['id']}
            floor_options = fetch_options(session, 'floor', floor_payload, csrf_token, token_page_url)
            choice = get_user_choice(floor_options)
            if not choice:
                selected_buis = None
                print("\n返回上一步...")
                continue
            selected_floor = choice
            continue
        if not selected_room:
            print("\n--- 请选择缴费房间 ---")
            room_payload = {'sysid': sysid, 'area': selected_area['id'], 'district': selected_district['id'],
                            'build': selected_buis['id'], 'floor': selected_floor['id']}
            room_options = fetch_options(session, 'room', room_payload, csrf_token, token_page_url)
            choice = get_user_choice(room_options)
            if not choice:
                selected_floor = None
                print("\n返回上一步...")
                continue
            selected_room = choice
        break

    return {
        'area': selected_area, 'district': selected_district,
        'buis': selected_buis, 'floor': selected_floor, 'room': selected_room
    }


def select_electric_system(session: requests.Session) -> dict | None:
    print("\n--- 正在获取电控系统列表 ---")
    try:
        headers = session.headers.copy()
        if 'X-Requested-With' in headers:
            del headers['X-Requested-With']
        response = session.get(LOAD_ELECTRIC_INDEX_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        target_systems = ["北洋园电控", "卫津路空调电控", "卫津路宿舍电控"]
        available_options = []
        li_tags = soup.find_all('li', class_='my_link')
        for tag in li_tags:
            name = tag.get_text(strip=True)
            if name in target_systems:
                onclick_attr = tag.get('onclick', '')
                try:
                    sysid = onclick_attr.split("'")[1]
                    available_options.append({'name': name, 'id': sysid})
                except IndexError:
                    continue
        if not available_options:
            print("错误：在页面上未找到指定的电控系统选项。")
            return None
        print("\n--- 请选择电控系统 ---")
        return get_user_choice(available_options)
    except requests.RequestException as e:
        print(f"访问电控系统选择页面失败: {e}")
        return None


# 【关键修改】增强的缓存加载函数
def load_selection_from_cache(filename: str) -> dict | None:
    """
    从文件加载并严格验证缓存的选择。
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 文件不存在或不是有效的JSON，都视为无缓存
        return None

    # 定义所有必需的顶级键
    required_keys = ['system', 'area', 'district', 'buis', 'floor', 'room']

    # 循环检查每个键
    for key in required_keys:
        # 检查1: 顶级键是否存在
        if key not in data:
            print(f"缓存文件校验失败：缺少顶级键 '{key}'。")
            return None

        # 检查2: 对应的值是否是字典，且包含'id'键
        item = data.get(key)
        if not isinstance(item, dict) or 'id' not in item:
            print(f"缓存文件校验失败：'{key}' 的内容格式不正确（不是字典或缺少'id'）。")
            return None

        # 检查3: 'id'的值不能为空
        if not item['id']:  # 这个检查能同时捕获 None 和 ""
            print(f"缓存文件校验失败：'{key}' 的 'id' 不能为空。")
            return None

    # 所有检查通过，返回数据
    return data


def save_selection_to_cache(filename: str, selection_data: dict):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(selection_data, f, ensure_ascii=False, indent=4)
        print(f"选择已缓存到 {filename}")
    except IOError as e:
        print(f"保存缓存失败: {e}")


# --- 4. 主函数 (无变化) ---
def get_electric_bill() -> None:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    })

    if os.path.exists(COOKIE_FILE):
        load_cookies(session, COOKIE_FILE)
        print("正在验证已加载的会话...")
        try:
            verify_headers = session.headers.copy()
            del verify_headers['X-Requested-With']
            verify_response = session.get(VERIFY_LOGIN_URL, headers=verify_headers)
            verify_response.raise_for_status()
            if 'j_spring_security_check' in verify_response.text or 'j_username' in verify_response.text:
                print("会话已失效，需要重新登录。")
                os.remove(COOKIE_FILE)
                if not perform_login(session): return
            else:
                print("会话验证通过，仍然有效！")
        except requests.RequestException as e:
            print(f"会话验证请求失败: {e}，需要重新登录。")
            if not perform_login(session): return
    else:
        if not perform_login(session): return

    query_payload = None
    token_page_url = None

    cached_selection = load_selection_from_cache(SELECTION_CACHE_FILE)
    if cached_selection:
        print("\n--- 检测到有效缓存，将直接使用 ---")
        sel = cached_selection
        print(
            f"缓存信息: {sel['system']['name']} > {sel['area']['name']} > {sel['district']['name']} > {sel['buis']['name']} > {sel['floor']['name']} > {sel['room']['name']}")

        selected_sysid = sel['system']['id']
        token_page_url = f'{BASE_DOMAIN}/epay/electric/load4electricbill?elcsysid={selected_sysid}'
        query_payload = {
            'sysid': selected_sysid,
            'elcarea': sel['area']['id'],
            'elcbuis': sel['buis']['id'],
            'roomNo': sel['room']['id']
        }

    if not query_payload:
        print("\n--- 未找到有效缓存，开始手动选择 ---")
        while True:
            selected_system = select_electric_system(session)
            if not selected_system:
                print("用户在主菜单选择退出，程序结束。")
                return

            selected_sysid = selected_system['id']
            token_page_url = f'{BASE_DOMAIN}/epay/electric/load4electricbill?elcsysid={selected_sysid}'

            print("\n正在访问电费页面以获取API操作权限...")
            try:
                page_headers = session.headers.copy()
                del page_headers['X-Requested-With']
                page_headers['Referer'] = LOAD_ELECTRIC_INDEX_URL
                page_response = session.get(token_page_url, headers=page_headers)
                page_response.raise_for_status()
                api_csrf_token = extract_csrf_token(page_response.text)
                if not api_csrf_token:
                    print("错误：无法在电费页面中找到API操作所需的CSRF Token！")
                    continue
                print("成功获取API操作权限 (CSRF Token)！")
            except requests.RequestException as e:
                print(f"访问电费页面失败: {e}")
                continue

            full_selection = interactive_query_flow(session, api_csrf_token, selected_sysid, token_page_url)
            if not full_selection:
                print("\n返回主菜单...")
                continue

            query_payload = {
                'sysid': selected_sysid,
                'elcarea': full_selection['area']['id'],
                'elcbuis': full_selection['buis']['id'],
                'roomNo': full_selection['room']['id']
            }

            full_selection['system'] = selected_system
            save_selection_to_cache(SELECTION_CACHE_FILE, full_selection)
            break

    if not query_payload:
        print("未能确定查询目标，程序退出。")
        return

    print("\n开始执行电费查询...")
    try:
        page_headers = session.headers.copy()
        del page_headers['X-Requested-With']
        page_headers['Referer'] = LOAD_ELECTRIC_INDEX_URL
        page_response = session.get(token_page_url, headers=page_headers)
        page_response.raise_for_status()
        final_csrf_token = extract_csrf_token(page_response.text)
        if not final_csrf_token:
            print("错误：在最终查询前无法获取CSRF Token！")
            return

        query_headers = {
            'X-CSRF-TOKEN': final_csrf_token,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': token_page_url
        }
        query_response = session.post(QUERY_URL, data=query_payload, headers=query_headers)
        query_response.raise_for_status()
        result = query_response.json()

        if result.get('retcode') == 0:
            if result.get('multiflag'):
                print("\n========================\n查询成功！(该房间为一房多表模式)")
                for meter in result.get('elecRoomData', []):
                    print(f"  - {meter.get('name')}: 剩余电量 {meter.get('restElecDegree')} 度")
                print("========================")
            else:
                remaining_electricity = result.get('restElecDegree')
                print("\n========================")
                print(f"查询成功！剩余电量: {remaining_electricity} 度")
                print("========================")
            save_cookies(session, COOKIE_FILE)
        else:
            print(f"查询失败: {result.get('retmsg')}")

    except (requests.RequestException, json.JSONDecodeError, Exception) as e:
        print(f"查询过程中发生错误: {e}")


if __name__ == "__main__":
    get_electric_bill()