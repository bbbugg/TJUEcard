# 天津大学电费查询自动化工具

本工具可以自动查询天津大学电费信息，并在电费低于阈值时发送邮件提醒。

## 功能

- 自动查询电费
- 低于阈值邮件提醒
- 跨平台支持（Windows, Linux, macOS）
- 支持多房间查询
- 可设置为开机自启或定时任务

## 使用步骤

1. **下载**

   从 [Releases](https://github.com/bbbugg/TjuEcard/releases) 页面下载适用于您操作系统的最新版本。
    - `TJUEcardSetup-windows-latest.exe` 适用于 Windows
    - `TJUEcardSetup-ubuntu-latest` 适用于 Linux
    - `TJUEcardSetup-macos-latest` 适用于 macOS

2. **配置**

    - **Windows**: 直接运行 `TJUEcardSetup-windows-latest.exe`。
    - **Linux/macOS**: 在终端中运行 `./TJUEcardSetup-ubuntu-latest` 或 `./TJUEcardSetup-macos-latest`。

   首次运行时，程序会引导您进行配置，包括学号、密码、用于接收邮件的邮箱等信息。配置成功后，会在程序同目录下生成
   `TJUEcard_user_config` 文件。

3. **定时任务**

   配置成功后，程序会询问您是否自动设置系统定时任务。如果选择是，程序会自动在系统中创建一个每日任务，在每天的同一时间运行
   `TJUEcard` 程序来查询并发送邮件。

## 定时任务管理

如果您需要查询或取消已设置的定时任务，可以按照以下步骤操作：

### Windows

- **查询定时任务**

  打开命令提示符（CMD）或 PowerShell，输入以下命令：

  ```bash
  schtasks /query /tn TJUEcardAutoQuery
  ```

- **取消定时任务**

  ```bash
  schtasks /delete /tn TJUEcardAutoQuery /f
  ```

### Linux

- **查询定时任务**

  打开终端，输入以下命令查看当前的 `cron` 任务列表：

  ```bash
  crontab -l
  ```

- **取消定时任务**

    1. 打开 `cron` 任务编辑器：

       ```bash
       crontab -e
       ```

    2. 在编辑器中，找到包含 `TJUEcard` 的那一行，删除它。
    3. 保存并退出编辑器。

### macOS

- **查询定时任务**

  打开终端，输入以下命令查看当前 root 用户的 `LaunchAgent` 任务列表：

  ```zsh
  sudo launchctl list
  ```

- **取消定时任务**

    1. 使用 `launchctl bootout` 命令停止并移除任务：

       ```zsh
       sudo launchctl bootout system /Library/LaunchDaemons/com.tjuecard.automatic.plist
       ```

    2. 找到对应的配置文件并删除：
    
       ``` zsh
    sudo rm ~/Library/LaunchAgents/com.tjuecard.automatic.plist
       ```
    
    3. 验证是否已移除
    
       ``` zsh
       sudo launchctl list | grep TJUEcard
       ```

## 注意事项

- 本项目仅供学习交流使用，请勿用于非法用途。
- 定时任务的执行时间是根据您运行 `TJUEcardSetup` 程序的时间确定的。
- 如果您移动了程序的位置，定时任务可能会失效，需要重新运行 `TJUEcardSetup` 进行配置。

## 故障排除

- **定时任务未执行**：请检查您的系统时间和定时任务的设置是否正确。
- **邮件未收到**：请检查您的邮箱配置是否正确，以及垃圾邮件文件夹。
- **程序报错**：请在 [GitHub Issues](https://github.com/bbbugg/TJUEcard/issues) 中提交您的问题，并附上详细的错误信息。