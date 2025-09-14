from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import json
import os
from send_email import send_notification_email
from scheduler_setup import setup_system_scheduler

# 导入工具函数和配置
from utils import save_cookies, load_cookies, extract_csrf_token, load_config
from config import (
    BASE_DOMAIN, USER_CONFIG_FILE, LOAD_ELECTRIC_INDEX_URL, LOGIN_URL,
    QUERY_URL, COOKIE_FILE, LOGIN_PAGE_URL, API_BASE_URL, API_URLS, KEY_MAP
)


# --- 1. 核心功能函数 ---


def perform_login(session) -> tuple[str | None, str | None]:
    try:
        page_response = session.get(LOGIN_PAGE_URL, timeout=10)  # 设置10秒超时
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

    # 循环直到登录成功
    while True:
        username = input("请输入用户名: ")
        password = input("请输入密码: ")
        login_data = {'j_username': username, 'j_password': password, '_csrf': csrf_token}
        try:
            headers = {'Referer': LOGIN_PAGE_URL, 'Origin': BASE_DOMAIN}
            response = session.post(LOGIN_URL, data=login_data, headers=headers, timeout=10)  # 设置10秒超时
            response.raise_for_status()
            if '<frameset' not in response.text:
                print("[错误] 登录失败！请检查用户名或密码。")
                print("[提示] 将重新尝试登录...")
                # 继续循环，再次尝试登录
                continue
            print("[成功] 登录成功！")
            return username, password
        except requests.RequestException as e:
            print(f"[错误] 登录请求失败: {e}")
            print("[提示] 将重新尝试登录...")
            # 继续循环，再次尝试登录
            continue

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
                if choice == 0:
                    return None
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
        response = session.post(url, data=payload, headers=api_headers, timeout=10)  # 设置10秒超时
        response.raise_for_status()
        try:
            data = response.json()
        except json.JSONDecodeError:
            error_msg = f"服务器在请求 '{level}' 列表时没有返回有效的JSON"
            print(f"[错误] {error_msg}")
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
        response = session.get(LOAD_ELECTRIC_INDEX_URL, headers=headers, timeout=10)  # 设置10秒超时
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
    print("欢迎使用电费查询配置程序 (setup)。")
    print("本程序将引导您登录、选择房间并配置邮件提醒。")
    print("\n注意：您的密码和邮箱授权码将以明文形式保存在 TJUEcard_user_config.json 文件中，请妥善保管此文件。")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    })

    username, password = perform_login(session)
    if not username:
        input("按回车键退出。")
        exit()

    # 【新增】循环以允许用户在邮件测试失败后重试
    email_configured = False
    while not email_configured:
        print("\n--- 邮件通知配置 ---")
        print("您需要提供一个QQ邮箱或163邮箱用于接收通知，以及该邮箱的SMTP授权码。")
        print(
            "QQ邮箱：请前往QQ邮箱 -> 设置 -> 账号与安全 -> 安全设置 -> 开启“POP3/IMAP/SMTP/Exchange/CardDAV 服务” -> 生成授权码获取。")
        print(
            "163邮箱：请前往163邮箱 -> 设置 -> POP3/SMTP/IMAP -> 开启“IMAP/SMTP服务”，生成授权码获取。")
        user_email = input("请输入您的邮箱: ")
        user_auth_code = input("请输入您的邮箱授权码: ")

        if not user_email or not user_auth_code:
            print("[警告] 您未输入邮箱或授权码，将无法使用邮件通知功能。")
            if input("确实要跳过邮件配置吗？(y/n): ").lower() == 'y':
                user_email, user_auth_code = None, None  # 明确设置为空
                break  # 跳出邮件配置循环
            else:
                continue  # 重新输入

        print("\n[信息] 正在发送一封测试邮件以验证您的配置...")
        email_success, email_error = send_notification_email(
            sender_email=user_email,
            auth_code=user_auth_code,
            recipient_email=user_email,
            subject="电费查询助手 - 邮箱配置测试",
            body="如果您收到此邮件，说明您的邮箱配置成功！现在可以继续进行后续设置。"
        )

        if email_success:
            print("[成功] 测试邮件发送成功！请检查您的收件箱。")
            email_configured = True
        else:
            print(f"[错误] 测试邮件发送失败！错误信息: {email_error}")

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
            page_response = session.get(token_page_url, headers=page_headers, timeout=10)  # 设置10秒超时
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
            query_response = session.post(QUERY_URL, data=query_payload, headers=query_headers, timeout=10)  # 设置10秒超时
            query_response.raise_for_status()
            result = query_response.json()

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
                # 只有在用户配置了邮箱的情况下才添加
                if user_email and user_auth_code:
                    config_data["email_notifier"] = {
                        "email": user_email,
                        "auth_code": user_auth_code
                    }
                    # 添加电费通知阈值设置
                    print("\n--- 电费通知阈值设置 ---")
                    print("设置后，只有当剩余电量小于等于阈值时才会发送邮件通知。")
                    print("如果不设置，每次查询都会发送邮件通知。")
                    set_threshold = input("是否需要设置电费通知阈值？(y/n): ").strip().lower()

                    if set_threshold == 'y':
                        while True:
                            try:
                                threshold_input = input("请输入电量阈值（单位：度，0-1024，最多两位小数）: ")
                                # 检查输入是否为数字且最多两位小数
                                threshold = float(threshold_input)
                                # 验证范围
                                if 0 <= threshold <= 1024:
                                    # 检查小数位数
                                    if '.' in threshold_input and len(threshold_input.split('.')[1]) > 2:
                                        print("[错误] 最多只能输入两位小数。")
                                        continue
                                    config_data["email_notifier"]["notification_threshold"] = threshold
                                    print(f"[成功] 已设置电费通知阈值: {threshold} 度")
                                    break
                                else:
                                    print("[错误] 电量阈值必须在0到1024之间。")
                            except ValueError:
                                print("[错误] 请输入有效的数字。")
                    else:
                        # 不设置阈值，保存-1
                        config_data["email_notifier"]["notification_threshold"] = -1
                        print("[成功] 未设置电费通知阈值，每次查询都会发送邮件。")

                # 验证成功后，才保存所有配置
                save_config_to_json(USER_CONFIG_FILE, config_data)
                save_cookies(session, COOKIE_FILE)
                print("\n所有配置已成功保存！现在您可以使用 main 进行快速查询。")

                # 记录当前时间并设置定时任务
                current_time = datetime.now()
                print(f"⏰ 记录执行时间: {current_time.strftime('%H:%M')}")

                # 询问是否设置系统定时任务
                setup_scheduler = input("\n是否自动设置系统定时任务？(y/n, 默认y): ").strip().lower()
                if setup_scheduler in ['', 'y', 'yes']:
                    try:
                        # 导入并执行定时任务设置
                        setup_system_scheduler()
                    except ImportError:
                        print("❌ 定时任务设置模块未找到")
                    except Exception as e:
                        print(f"❌ 定时任务设置失败: {e}")
                else:
                    print("💡 您可以选择稍后手动设置定时任务")

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