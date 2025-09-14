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
    - `TJUEcard-windows-x86_64.zip` 适用于 Windows
    - `TJUEcard-linux-x86_64.tar.gz` 适用于 Linux
    - `TJUEcard-macos-arm64.tar.gz` 或 `TJUEcard-macos-x86_64.tar.gz` 适用于 macOS

   解压后，Windows系统包含 `TJUEcard.exe` 和 `TJUEcardSetup.exe` 两个文件，Linux和macOS系统则包含 `TJUEcard` 和
   `TJUEcardSetup`。

2. **配置**

    - **Windows**: 直接运行 `TJUEcardSetup.exe`。
    - **Linux/macOS**: 在终端中运行 `./TJUEcardSetup`。

   首次运行时，程序会引导您进行配置，包括学号、密码、用于接收邮件的邮箱等信息。配置成功后，会在程序同目录下生成
   `TJUEcard_user_config.json` 文件。

3. **定时任务**

   配置成功后，程序会询问您是否自动设置系统定时任务。任务将被设置为在每天的固定时间运行 `TJUEcard` 程序来查询并发送邮件。

   > **注意**: 为了让定时任务在用户未登录时也能正常运行，在所有系统上设置时都建议使用 **管理员权限** 。请确保您以管理员身份运行
   `TJUEcardSetup` 程序（在Windows上右键点击“以管理员身份运行”，在Linux和macOS上使用 `sudo` 命令）。

## 定时任务管理

如果您需要查询或取消已设置的定时任务，可以按照以下步骤操作：

### Windows

- **查询定时任务**

    - **方式一：命令行**
      打开 **管理员权限** 的命令提示符(cmd)或PowerShell，输入以下命令：
      ```bash
      schtasks /query /tn TJUEcardAutoQuery
      ```
    - **方式二：任务计划程序**
      搜索"任务计划程序"并打开，在任务计划程序库中可以找到名为“TJUEcardAutoQuery”的计划，您可以右键单击它进行修改或删除。

- **取消定时任务**

  ```bash
  schtasks /delete /tn TJUEcardAutoQuery /f
  ```

### Linux

- **查询定时任务**

  脚本会将定时任务添加到系统级的 `/etc/crontab` 文件中。您可以使用以下命令查看内容：

  ```bash
  cat /etc/crontab
  ```

- **取消定时任务**

  您需要以管理员权限编辑 `/etc/crontab` 文件来移除任务。

    1. 使用文本编辑器（如 `nano` 或 `vim`）打开文件：

       ```bash
       sudo nano /etc/crontab
       ```

    2. 在编辑器中，找到并删除包含 `tjuecard` 的那一行。
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
       sudo rm /Library/LaunchDaemons/com.tjuecard.automatic.plist
       ```
    
    3. 验证是否已移除：
    
       ``` zsh
       sudo launchctl list | grep tjuecard
       ```

## 注意事项

- 本项目仅供学习交流使用，请勿用于非法用途。
- 定时任务的执行时间是根据您运行 `TJUEcardSetup` 程序的时间确定的。
- 如果您移动了程序的位置，定时任务可能会失效，需要重新运行 `TJUEcardSetup` 进行配置。

## 故障排除

- **定时任务未执行**：请检查您的系统时间和定时任务的设置是否正确。
- **邮件未收到**：请检查您的邮箱配置是否正确，以及垃圾邮件文件夹。
- **程序报错**：请在 [GitHub Issues](https://github.com/bbbugg/TJUEcard/issues) 中提交您的问题，并附上详细的错误信息。
