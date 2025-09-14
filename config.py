# -*- coding: utf-8 -*-
"""
配置文件，统一管理常量
"""

# 基础URL配置
BASE_DOMAIN = 'http://59.67.37.10:8180'

# API URL配置
LOGIN_PAGE_URL = f'{BASE_DOMAIN}/epay/person/index'
LOGIN_URL = f'{BASE_DOMAIN}/epay/j_spring_security_check'
VERIFY_LOGIN_URL = f'{BASE_DOMAIN}/epay/person/index'
LOAD_ELECTRIC_INDEX_URL = f'{BASE_DOMAIN}/epay/electric/load4electricindex'
QUERY_URL = f'{BASE_DOMAIN}/epay/electric/queryelectricbill'

# 电控系统API URL配置
API_BASE_URL = f'{BASE_DOMAIN}/epay/electric'
API_URLS = {
    'area': f'{API_BASE_URL}/queryelectricarea',
    'district': f'{API_BASE_URL}/queryelectricdistricts',
    'buis': f'{API_BASE_URL}/queryelectricbuis',
    'floor': f'{API_BASE_URL}/queryelectricfloors',
    'room': f'{API_BASE_URL}/queryelectricrooms'
}

# 电控系统API响应字段映射
KEY_MAP = {
    'area': {'list': 'areas', 'id': 'areaId', 'name': 'areaName'},
    'district': {'list': 'districts', 'id': 'districtId', 'name': 'districtName'},
    'buis': {'list': 'buils', 'id': 'buiId', 'name': 'buiName'},
    'floor': {'list': 'floors', 'id': 'floorId', 'name': 'floorName'},
    'room': {'list': 'rooms', 'id': 'roomId', 'name': 'roomName'},
}

# 文件路径配置
USER_CONFIG_FILE = 'user_config.json'
COOKIE_FILE = 'my_session.pkl'
LOG_FILE = 'TjuEcard.log'

# HTTP请求头配置
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

# 日志配置
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 目标电控系统列表
TARGET_SYSTEMS = ["北洋园电控", "卫津路空调电控", "卫津路宿舍电控"]
