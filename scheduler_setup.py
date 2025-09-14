#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import platform
import subprocess
import json
from datetime import datetime
from pathlib import Path


def get_platform_type():
    """识别当前操作系统类型"""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "unknown"


def setup_windows_scheduler(config_path, python_executable):
    """设置Windows定时任务"""
    try:
        # 获取当前时间作为执行时间
        current_time = datetime.now()
        hour = current_time.hour
        minute = current_time.minute

        # 创建任务名称
        task_name = "TJUEcardAutoQuery"

        # 确定要执行的命令
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            executable_path = os.path.abspath(sys.executable)
            executable_dir = os.path.dirname(executable_path)
            main_executable = os.path.join(executable_dir, 'TJUEcard.exe')
            task_command = f'\"{main_executable}\"'  # 注意这里需要转义引号
        else:
            # 作为脚本运行
            task_command = f'\"{python_executable}\" \"{config_path}\"'  # 注意这里需要转义引号

        # 构建schtasks命令
        command = [
            "schtasks", "/create", "/tn", task_name,
            "/tr", task_command,
            "/sc", "daily", "/st", f"{hour:02d}:{minute:02d}",
            "/f"
        ]

        # 执行命令
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Windows定时任务创建成功！")
            print(f"   执行时间: 每天 {hour:02d}:{minute:02d}")
            print(f"   执行命令: {python_executable} {config_path}")
            return True
        else:
            print(f"❌ Windows定时任务创建失败:")
            print(f"   {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Windows定时任务设置出错: {e}")
        return False


def setup_linux_cron(config_path, python_executable):
    """设置Linux cron定时任务"""
    try:
        current_time = datetime.now()
        minute = current_time.minute
        hour = current_time.hour

        # 构建cron表达式
        cron_expression = f"{minute} {hour} * * *"

        # 确定要执行的命令
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            executable_path = os.path.abspath(sys.executable)
            executable_dir = os.path.dirname(executable_path)
            main_executable = os.path.join(executable_dir, 'TJUEcard')
            job_command = f"'{main_executable}'"
        else:
            # 作为脚本运行
            job_command = f"'{python_executable}' '{config_path}'"

        # 构建cron命令
        cron_command = f"{cron_expression} {job_command}"

        # 使用crontab命令添加任务
        command = f"(crontab -l 2>/dev/null; echo '{cron_command}') | crontab -"

        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Linux定时任务创建成功！")
            print(f"   Cron表达式: {cron_expression}")
            print(f"   执行命令: {python_executable} {config_path}")
            return True
        else:
            print(f"❌ Linux定时任务创建失败:")
            print(f"   {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Linux定时任务设置出错: {e}")
        return False


def setup_macos_launchd(config_path, python_executable):
    """设置macOS launchd定时任务"""
    try:
        current_time = datetime.now()
        hour = current_time.hour
        minute = current_time.minute

        # 创建plist文件内容
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tjuecard.automatic</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_executable}</string>
        <string>{config_path}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>'''

        # 保存plist文件
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.tjuecard.automatic.plist")

        with open(plist_path, 'w') as f:
            f.write(plist_content)

        # 加载任务
        command = ["launchctl", "load", plist_path]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ macOS定时任务创建成功！")
            print(f"   执行时间: 每天 {hour:02d}:{minute:02d}")
            print(f"   执行命令: {python_executable} {config_path}")
            return True
        else:
            print(f"❌ macOS定时任务创建失败:")
            print(f"   {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ macOS定时任务设置出错: {e}")
        return False


def setup_system_scheduler():
    """自动设置系统级定时任务"""
    print("🚀 开始设置系统定时任务...")

    # 获取当前平台
    current_platform = get_platform_type()
    print(f"📋 检测到操作系统: {current_platform}")

    # 获取Python可执行文件和配置文件路径
    python_executable = sys.executable
    config_path = os.path.abspath("main.py")

    print(f"🐍 Python路径: {python_executable}")
    print(f"📁 执行文件: {config_path}")

    # 根据平台调用相应的设置函数
    success = False

    if current_platform == "windows":
        success = setup_windows_scheduler(config_path, python_executable)
    elif current_platform == "linux":
        success = setup_linux_cron(config_path, python_executable)
    elif current_platform == "macos":
        success = setup_macos_launchd(config_path, python_executable)
    else:
        print("❌ 不支持的操作系统类型")
        return False

    if success:
        print("\n🎉 定时任务设置完成！")
        print("💡 程序将在每天同一时间自动运行")
        print("📋 您可以在系统任务计划中查看和管理定时任务")
    else:
        print("\n❌ 定时任务设置失败")
        print("💡 请检查系统权限或手动设置定时任务")

    return success


if __name__ == "__main__":
    setup_system_scheduler()
