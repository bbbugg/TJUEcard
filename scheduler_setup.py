import os
import sys
import platform
import subprocess
from datetime import datetime


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
            task_command = f'\"{main_executable}\"'
        else:
            # 作为脚本运行
            task_command = f'\"{python_executable}\" \"{config_path}\"'  # 注意这里需要转义引号

        # 构建schtasks命令
        # 使用 /ru "SYSTEM" 确保任务在用户未登录时也能运行，这需要管理员权限
        command = [
            "schtasks", "/create", "/tn", task_name,
            "/tr", task_command,
            "/sc", "daily", "/st", f"{hour:02d}:{minute:02d}",
            "/ru", "SYSTEM", "/f"
        ]

        # 执行命令
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"Windows定时任务创建成功！")
            print(f"   执行时间: 每天 {hour:02d}:{minute:02d}")
            print(f"   执行命令: {task_command}")
            return True
        else:
            # 检查是否是权限问题
            if "7042" in result.stderr or "Access is denied" in result.stderr or "拒绝访问" in result.stderr:
                print("Windows定时任务创建失败：权限不足。")
                print("请尝试以管理员身份运行此程序。")
            else:
                print(f"Windows定时任务创建失败:")
                print(f"   {result.stderr}")
            return False

    except Exception as e:
        print(f"Windows定时任务设置出错: {e}")
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

        # 为了让任务在用户未登录时也能运行，需要将cron任务添加到系统级的crontab中
        # 这通常需要管理员权限（sudo）
        cron_file = "/etc/crontab"
        print(f"将在系统级cron配置文件中添加任务: {cron_file}")
        print("这需要管理员权限，如果脚本运行失败，请尝试使用 'sudo' 再次运行。")

        # 在系统级的crontab中，需要指定运行任务的用户名，这里我们默认为root
        cron_command_with_user = f"{cron_expression} root {job_command}"

        try:
            with open(cron_file, "a") as f:
                f.write(f"\n# TJUEcard Auto Query Job\n{cron_command_with_user}\n")
            result = None  # 表示成功
        except PermissionError:
            print(f"权限错误: 无法写入 {cron_file}。请尝试使用 'sudo' 运行此脚本。")
            return False
        except Exception as e:
            print(f"写入 {cron_file} 时出错: {e}")
            return False

        # 检查是否成功写入
        # 在这个逻辑中，如果前面的 try-except 没有抛出异常，就意味着写入成功了
        print(f"Linux定时任务创建成功！")
        print(f"   Cron表达式: {cron_expression}")
        print(f"   执行命令: {job_command}")
        return True

    except Exception as e:
        print(f"Linux定时任务设置出错: {e}")
        return False


def setup_macos_launchd(config_path, python_executable):
    """设置macOS launchd定时任务"""
    try:
        current_time = datetime.now()
        hour = current_time.hour
        minute = current_time.minute

        # 确定要执行的命令
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            executable_path = os.path.abspath(sys.executable)
            executable_dir = os.path.dirname(executable_path)
            main_executable = os.path.join(executable_dir, 'TJUEcard')
            program_arguments = f'<string>{main_executable}</string>'
            task_command = f'\"{main_executable}\"'
        else:
            # 作为脚本运行
            main_py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))
            program_arguments = f'<string>{python_executable}</string>\n        <string>{main_py_path}</string>'
            task_command = f'\"{python_executable}\" \"{main_py_path}\"' 

        # 创建plist文件内容
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tjuecard.automatic</string>
    <key>ProgramArguments</key>
    <array>
{program_arguments}
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

        # 为了让任务在用户未登录时也能运行，需要将plist文件放在 /Library/LaunchDaemons/
        # 这需要管理员权限（sudo）
        plist_path = "/Library/LaunchDaemons/com.tjuecard.automatic.plist"
        print(f"将在以下路径创建macOS后台任务配置文件: {plist_path}")
        print("这需要管理员权限，如果脚本运行失败，请尝试使用 'sudo' 再次运行。")

        with open(plist_path, 'w') as f:
            f.write(plist_content)

        # 加载任务
        command = ["launchctl", "load", plist_path]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"macOS定时任务创建成功！")
            print(f"   执行时间: 每天 {hour:02d}:{minute:02d}")
            print(f"   执行命令: {task_command}")
            return True
        else:
            print(f"macOS定时任务创建失败:")
            print(f"   {result.stderr}")
            return False

    except Exception as e:
        print(f"macOS定时任务设置出错: {e}")
        return False


def setup_system_scheduler():
    """自动设置系统级定时任务"""
    print("开始设置系统定时任务...")

    # 获取当前平台
    current_platform = get_platform_type()
    print(f"检测到操作系统: {current_platform}")

    # 获取Python可执行文件和主脚本路径
    python_executable = sys.executable

    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件, config_path 实际上是可执行文件自己
        # 子函数会处理具体要执行的文件
        config_path = os.path.abspath(sys.executable)
        # print(f"执行文件: {config_path}")
    else:
        # 如果是作为 .py 脚本运行, 则定位 main.py
        # __file__ 是 scheduler_setup.py 的路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "main.py")
        print(f"Python/可执行文件路径: {python_executable}")
        print(f"执行文件: {config_path}")

    # 根据平台调用相应的设置函数
    success = False

    if current_platform == "windows":
        success = setup_windows_scheduler(config_path, python_executable)
    elif current_platform == "linux":
        success = setup_linux_cron(config_path, python_executable)
    elif current_platform == "macos":
        success = setup_macos_launchd(config_path, python_executable)
    else:
        print("[错误] 不支持的操作系统类型")
        return False

    if success:
        print("\n定时任务设置完成！")
        print("程序将在每天同一时间自动运行")
        print("您可以在系统任务计划中查看和管理定时任务")
    else:
        print("\n[错误] 定时任务设置失败")
        print("请检查系统权限或手动设置定时任务")

    return success


if __name__ == "__main__":
    setup_system_scheduler()
