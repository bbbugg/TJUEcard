import requests
from bs4 import BeautifulSoup
import pickle
import os
import time
import json

# --- 1. 配置区 ---
BASE_DOMAIN = 'http://59.67.37.10:8180'
# 【新】统一的用户配置文件
USER_CONFIG_FILE = 'user_config.json'
# 其他配置
LOAD_ELECTRIC_INDEX_URL = f'{BASE_DOMAIN}/epay/electric/load4electricindex'
LOGIN_URL = f'{BASE_DOMAIN}/epay/j_spring_security_check'
QUERY_URL = f'{BASE_DOMAIN}/epay/electric/queryelectricbill'
COOKIE_FILE = 'my_session.pkl'
LOGIN_PAGE_URL = f'{BASE_DOMAIN}/epay/person/index'
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


# --- 2. 核心功能函数 ---
def save_cookies(session: requests.Session, file_name: str) -> None:
    with open(file_name, 'wb') as file: pickle.dump(session.cookies, file)
    print(f"\n[成功] 新的会话已成功保存到 {file_name}")


def extract_csrf_token(html_content: str) -> str | None:
    soup = BeautifulSoup(html_content, 'html.parser')
    csrf_meta_tag = soup.find('meta', {'name': '_csrf'})
    if csrf_meta_tag and csrf_meta_tag.has_attr('content'):
        return csrf_meta_tag['content']
    return None


def perform_login(session: requests.Session) -> tuple[str | None, str | None]:
    print("--- 开始强制登录流程 ---")
    try:
        page_response = session.get(LOGIN_PAGE_URL)
        page_response.raise_for_status()
        soup = BeautifulSoup(page_response.text, 'html.parser')
        csrf_input_tag = soup.find('input', {'name': '_csrf'})
        if not csrf_input_tag or not csrf_input_tag.has_attr('value'):
            print("[错误] 在登录页面中未找到 _csrf token！")
            return None, None
        csrf_token = csrf_input_tag['value']
    except requests.RequestException as e:
        print(f"[错误] 访问登录页面失败: {e}")
        return None, None

    username = input("请输入用户名: ")
    password = input("请输入密码: ")
    login_data = {'j_username': username, 'j_password': password, '_csrf': csrf_token}
    try:
        headers = {'Referer': LOGIN_PAGE_URL, 'Origin': BASE_DOMAIN}
        response = session.post(LOGIN_URL, data=login_data, headers=headers)
        response.raise_for_status()
        if '<frameset' not in response.text:
            print("[错误] 登录失败！请检查用户名或密码。")
            return None, None
        print("[成功] 登录成功！")
        return username, password
    except requests.RequestException as e:
        print(f"[错误] 登录请求失败: {e}")
        return None, None

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
            print(f"[错误] 服务器在请求 '{level}' 列表时没有返回有效的JSON。")
            return []
        raw_list = data.get(map_keys['list'], [])
        for item in raw_list:
            normalized_options.append({'id': str(item[map_keys['id']]), 'name': str(item[map_keys['name']])})
        return normalized_options
    except requests.RequestException as e:
        print(f"[错误] 获取 {level} 列表时发生网络错误: {e}")
    return []


def interactive_query_flow(session: requests.Session, csrf_token: str, sysid: str, token_page_url: str) -> dict | None:
    print("\n--- 正在自动选择默认校区 ---")
    area_options = fetch_options(session, 'area', {'sysid': sysid}, csrf_token, token_page_url)
    if not area_options:
        print("[错误] 无法获取校区列表。")
        return None
    selected_area = area_options[0]
    print(f"已自动选择: {selected_area['name']}")
    selected_district, selected_buis, selected_floor, selected_room = None, None, None, None
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
        if 'X-Requested-With' in headers: del headers['X-Requested-With']
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
            print("[错误] 在页面上未找到指定的电控系统选项。")
            return None
        print("\n--- 请选择电控系统 ---")
        return get_user_choice(available_options)
    except requests.RequestException as e:
        print(f"[错误] 访问电控系统选择页面失败: {e}")
        return None


def save_config_to_json(filename: str, config_data: dict):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"[成功] 您的配置已保存到 {filename}")
    except IOError as e:
        print(f"[错误] 保存配置文件失败: {e}")

# --- 3. 主程序 ---
if __name__ == "__main__":
    print("欢迎使用电费查询配置程序 (setup.py)。")
    print("本程序将引导您登录并选择一个房间，然后将配置保存供 query.py 使用。")
    print("\n注意：您的密码将以明文形式保存在 user_config.json 文件中，请妥善保管此文件。")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    })

    username, password = perform_login(session)
    if not username:
        input("按回车键退出。")
        exit()

    while True:
        selected_system = select_electric_system(session)
        if not selected_system:
            print("用户在主菜单选择退出，程序结束。")
            exit()

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
                print("[错误] 无法在电费页面中找到API操作所需的CSRF Token！")
                continue
            print("[成功] 获取API操作权限 (CSRF Token)！")
        except requests.RequestException as e:
            print(f"[错误] 访问电费页面失败: {e}")
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

        print("\n--- 正在验证您的选择并保存配置 ---")
        try:
            query_headers = {
                'X-CSRF-TOKEN': api_csrf_token,
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': token_page_url
            }
            query_response = session.post(QUERY_URL, data=query_payload, headers=query_headers)
            query_response.raise_for_status()
            result = query_response.json()

            if result.get('retcode') == 0:
                print("[成功] 您的选择已通过验证！")

                # 构建最终的配置文件
                config_data = {
                    "credentials": {
                        "username": username,
                        "password": password
                    },
                    "selection": {
                        "system": selected_system,
                        **full_selection
                    }
                }

                # 验证成功后，才保存所有配置
                save_config_to_json(USER_CONFIG_FILE, config_data)
                save_cookies(session, COOKIE_FILE)
                print("\n所有配置已成功保存！现在您可以使用 query.py 进行快速查询。")
                break
            else:
                print(f"[错误] 验证失败: {result.get('retmsg')}")
                input("按回车键返回主菜单...")
                continue
        except (requests.RequestException, json.JSONDecodeError, Exception) as e:
            print(f"[错误] 验证过程中发生错误: {e}")
            input("按回车键返回主菜单...")
            continue

    input("按回车键退出。")