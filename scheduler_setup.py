import os
import platform
import subprocess
import sys
from datetime import datetime
from typing import List, Optional


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
        result = subprocess.run(command, capture_output=True, text=True, check=False)

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


def find_system_crontab_location():
    """
    动态查找系统级的 crontab 文件或相关目录。
    兼容主流发行版 (Debian, CentOS) 和轻量级系统 (OpenWrt, Alpine)。
    """
    # 按优先级排序：
    # 1. /etc/cron.d: 现代主流系统的最佳实践。
    # 2. /etc/crontabs/root: OpenWrt 和 Alpine (BusyBox cron) 的标准位置。
    # 3. /etc/crontab: 传统的主系统 crontab 文件。
    potential_paths = [
        '/etc/cron.d',
        '/etc/crontabs/root',
        '/etc/crontab',
    ]

    print("开始在标准位置搜索 crontab...")
    for path in potential_paths:
        print(f"正在检查路径: '{path}'...")
        if os.path.exists(path):
            print(f"成功！找到存在的路径: '{path}'")
            return path  # 只要找到一个就立即返回

    print("未能在所有已知标准位置找到 crontab 文件或目录。")
    return None


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

        cron_location = find_system_crontab_location()

        if not cron_location:
            print("无法定位系统 cron 配置文件。请确认 cron 服务已安装 (如 'cron', 'cronie' 或 BusyBox crond)。")
            return False

        print(f"将在系统级 cron 配置中添加任务: {cron_location}")
        print("这需要管理员权限，如果脚本运行失败，请尝试使用 'sudo' 再次运行。")

        # --- 智能格式化任务命令 ---
        # 根据找到的路径决定是否需要添加 'root' 用户名
        if 'crontabs/root' in cron_location:
            # OpenWrt/Alpine (BusyBox) 格式，不需要用户名
            print("检测到 BusyBox cron 格式，任务行将不包含用户名。")
            final_cron_command = f"{cron_expression} {job_command}"
        else:
            # 标准 Vixie-cron/cronie 格式，需要用户名
            print("检测到标准 cron 格式，任务行将包含 'root' 用户名。")
            final_cron_command = f"{cron_expression} root {job_command}"

        job_content = f"# TJUEcard Auto Query Job\n{final_cron_command}\n"

        try:
            target_file = ""
            if os.path.isdir(cron_location):
                # 情况1: /etc/cron.d 目录
                target_file = os.path.join(cron_location, "tjuecard-auto-query")
                print(f"检测到 cron 目录，将创建/更新任务文件: {target_file}")
                with open(target_file, "w", encoding='utf-8') as f:
                    f.write(job_content + "\n")

            elif os.path.isfile(cron_location):
                # 情况2: /etc/crontab 或 /etc/crontabs/root 文件
                target_file = cron_location
                print(f"检测到 cron 文件，将创建/更新任务于: {target_file}")

                lines = []
                try:
                    with open(target_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except FileNotFoundError:
                    pass  # 文件不存在是正常情况，lines为空列表

                # 过滤掉所有与此任务相关的旧行
                new_lines = [line for line in lines if 'TJUEcard' not in line]

                # 清理末尾可能存在的空行
                while new_lines and new_lines[-1].strip() == "":
                    new_lines.pop()

                # 将新任务追加到清理后的内容末尾
                new_lines.append(f"\n{job_content}")

                # 将全新内容写回文件，实现覆盖
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)

        except PermissionError:
            print(f"权限错误: 无法写入 {cron_location} 或其子文件。请尝试使用 'sudo' 运行此脚本。")
            return False
        except Exception as e:
            print(f"写入 cron 配置时出错: {e}")
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


CRON_IDENTIFIER = "[TJUEcard-JOB]"  # 唯一标识，用于幂等更新/删除

def _run(cmd: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False
    )


def _cron_read(use_root: bool = False) -> str:
    cmd = (["sudo", "crontab", "-l"] if use_root else ["crontab", "-l"])
    p = _run(cmd)
    # 空 crontab 时通常非 0；按空文本处理
    return "" if p.returncode != 0 else p.stdout


def _ensure_nl(s: str) -> str:
    return s if s.endswith("\n") else s + "\n"


def _cron_write(content: str, use_root: bool = False) -> None:
    cmd = (["sudo", "crontab", "-"] if use_root else ["crontab", "-"])
    p = _run(cmd, input_text=content)
    if p.returncode != 0:
        raise RuntimeError(f"crontab install failed: {p.stderr.strip()}")


def setup_unix_cron(config_path: str,
                    python_executable: str,
                    schedule: str | None = None,
                    use_root: bool = False) -> bool:
    try:
        now = datetime.now()
        cron_expr = schedule or f"{now.minute} {now.hour} * * *"

        # 1) 组装命令：把 PATH 放到命令里，避免顶部环境行不被支持
        if getattr(sys, 'frozen', False):
            exe_path = os.path.abspath(sys.executable)
            exe_dir = os.path.dirname(exe_path)
            main_exe = os.path.join(exe_dir, 'TJUEcard' + ('.exe' if platform.system().lower()=="windows" else ""))
            base_cmd = f'/bin/sh -lc "PATH=/usr/local/bin:/usr/bin:/bin {main_exe}"'
        else:
            base_cmd = f'/bin/sh -lc "PATH=/usr/local/bin:/usr/bin:/bin {python_executable} {config_path}"'

        cron_line = f"{cron_expr} {base_cmd} >> /var/tmp/tjuecard.log 2>&1 # {CRON_IDENTIFIER}"

        # 2) 读取现有 crontab，移除旧的同标识
        current = _cron_read(use_root=use_root)
        lines = [l for l in current.splitlines() if l.strip()]
        lines = [l for l in lines if 'TJUEcard' not in l]

        # 3) 先尝试“带 header”版本（在支持的系统上更清晰）
        header = []
        # 只有在“看起来像 Vixie/Crond”时才加；BusyBox 常见出错，先允许加，失败再降级
        if "SHELL=" in current or "MAILTO=" in current:
            header = []  # 已经有就不重复
        else:
            header = ["SHELL=/bin/sh", "MAILTO="]

        content_with_header = ""
        if header:
            content_with_header += "\n".join(header) + "\n"
        if lines:
            content_with_header += "\n".join(lines) + "\n"
        content_with_header += cron_line + "\n"

        try:
            _cron_write(_ensure_nl(content_with_header), use_root=use_root)
            print("cron 定时任务创建/更新成功！（带 header）")
            print(f"  Cron表达式: {cron_expr}")
            print(f"  执行命令: {base_cmd}")
            return True
        except Exception as e:
            msg = str(e)
            # BusyBox 常见报错：“bad minute”且第一行是 SHELL=...
            if "bad minute" in msg or "errors in crontab file" in msg:
                # 4) 降级：去掉 header，重新写入
                content_no_header = ""
                if lines:
                    content_no_header += "\n".join(lines) + "\n"
                content_no_header += cron_line + "\n"
                _cron_write(_ensure_nl(content_no_header), use_root=use_root)
                print("cron 定时任务创建/更新成功！（已自动去掉 header 兼容 BusyBox）")
                print(f"  Cron表达式: {cron_expr}")
                print(f"  执行命令: {base_cmd}")
                return True
            else:
                raise

    except Exception as e:
        print(f"设置 cron 失败: {e}")
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
        # 如果是作为 .py 脚本运行, 则定位 TJUEcard_main.py
        # __file__ 是 scheduler_setup.py 的路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "TJUEcard_main.py")
        print(f"Python/可执行文件路径: {python_executable}")
        print(f"执行文件: {config_path}")

    # 根据平台调用相应的设置函数
    success = False

    if current_platform == "windows":
        success = setup_windows_scheduler(config_path, python_executable)
    elif current_platform == "linux":
        success = setup_linux_cron(config_path, python_executable)
    elif current_platform == "macos":
        success = setup_unix_cron(config_path, python_executable)
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


def check_and_update_cron():
    """
    检查旧的/etc/crontab中是否存在定时任务，如果存在则移除，并重新设置。
    """
    if platform.system().lower() != 'linux':
        # 非Linux系统，直接返回
        return True

    old_cron_path = '/etc/crontab'
    script_identifier = 'TJUEcard'  # 用于识别定时任务行的标识符

    try:
        # 检查文件是否存在
        if not os.path.exists(old_cron_path):
            # print(f"[信息] {old_cron_path} 文件不存在，无需检查。")
            return True

        with open(old_cron_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 过滤掉包含脚本标识符的行
        new_lines = [line for line in lines if script_identifier not in line]

        if len(new_lines) < len(lines):
            print(f"[信息] 在 {old_cron_path} 中找到旧的定时任务，正在移除...")
            try:
                with open(old_cron_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                print("[成功] 旧的定时任务已移除。")

                # 重新设置定时任务
                print("[信息] 正在使用新的方式重新设置定时任务...")
                if not setup_system_scheduler():
                    print("[错误] 定时任务设置失败。")
                    return False
                print("[成功] 定时任务已重新设置。")
            except PermissionError:
                print(f"[错误] 权限不足，无法写入 {old_cron_path}。请使用 'sudo' 权限运行此脚本以更新定时任务。")
                return False
            except Exception as e:
                print(f"[错误] 移除旧定时任务时出错: {e}")
                return False
        else:
            # print("[信息] 未在 /etc/crontab 中找到需要更新的旧定时任务。")
            pass
        return True

    except Exception as e:
        print(f"[错误] 检查和更新旧定时任务时出错: {e}")
        return False

if __name__ == "__main__":
    setup_system_scheduler()
