# -*- coding: utf-8 -*-
"""
工具函数模块，包含项目中重复使用的函数
"""

import pickle
import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from config import LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT


# 日志配置函数
def setup_logger(logger_name='TJUEcardLogger'):
    """
    配置并返回日志记录器
    
    :param logger_name: 日志记录器名称
    :return: 配置好的日志记录器
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # 检查是否已经有处理器，避免重复添加
    if not logger.handlers:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Cookie相关函数
def save_cookies(session: requests.Session, file_name: str) -> None:
    """
    保存会话cookies到文件
    
    :param session: 请求会话对象
    :param file_name: 保存的文件名
    """
    with open(file_name, 'wb') as file:
        pickle.dump(session.cookies, file)
    print(f"[信息] 新的会话已保存到 {file_name}")


def load_cookies(session: requests.Session, file_name: str) -> bool:
    """
    从文件加载cookies到会话
    
    :param session: 请求会话对象
    :param file_name: 加载的文件名
    :return: 是否成功加载
    """
    if not os.path.exists(file_name):
        return False
    with open(file_name, 'rb') as file:
        session.cookies.update(pickle.load(file))
    print("[信息] 已从本地加载会话。")
    return True


# CSRF Token相关函数
def extract_csrf_token(html_content: str) -> str | None:
    """
    从HTML内容中提取CSRF Token
    
    :param html_content: HTML内容
    :return: CSRF Token或None
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    csrf_meta_tag = soup.find('meta', {'name': '_csrf'})
    if csrf_meta_tag and csrf_meta_tag.has_attr('content'):
        return csrf_meta_tag['content']
    return None


# 配置文件相关函数
def load_config(filename: str, logger=None) -> dict | None:
    """
    加载并验证配置文件
    
    :param filename: 配置文件名
    :param logger: 日志记录器，可选
    :return: 配置数据或None
    """
    print(f"[信息] 正在读取用户配置文件 {filename}...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        msg = f"配置文件 '{filename}' 不存在。"
        print(f"[错误] {msg}")
        if logger:
            logger.error(msg)
        return None
    except json.JSONDecodeError:
        msg = f"配置文件 '{filename}' 格式错误，不是有效的JSON。"
        print(f"[错误] {msg}")
        if logger:
            logger.error(msg)
        return None

    if "selection" not in data:
        msg = "配置文件缺少'selection'部分。"
        print(f"[错误] {msg}")
        if logger:
            logger.error(msg)
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
            if logger:
                logger.error(msg)
            return None

    print("[成功] 配置文件校验通过。")
    return data


def save_config_to_json(filename: str, config_data: dict):
    """
    保存配置数据到JSON文件
    
    :param filename: 文件名
    :param config_data: 配置数据
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        print(f"[成功] 您的配置已保存到 {filename}")
    except IOError as e:
        print(f"[错误] 保存配置文件失败: {e}")
