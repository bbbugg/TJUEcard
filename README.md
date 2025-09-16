# 天津大学电费自动化查询工具

本工具可以自动查询天津大学电费信息，并在电费低于阈值的时候发送邮件提醒，解决了没及时充电费，导致半夜突然停电的痛点。

## ⭐ 主要功能

🔍 自动化电费查询。

📮 电费低于一定余额时发送邮件提醒。

👍 跨平台支持（Windows、Linux、~~macOS~~）。

⏰ 自动设置定时任务，每天检查一次电费余额。

🔑 密码和邮箱授权码加密保存在本地。

## 💻 运行要求

### 系统

| 操作系统          | 支持架构                                      |
|---------------|-------------------------------------------|
| Windows 10+   | x86_64                                    |
| Ubuntu 22.04+ | x86_64                                    |
| ~~macOS 13+~~ | ~~x86_64 (Intel), arm64 (Apple Silicon)~~ |

> ⚠ 其他 Linux 发行版未经验证，不保证能正常使用。

### 邮箱

目前支持 QQ 邮箱和 163 邮箱（SMTP）。

### 网络

- 网络连接到天津大学的校园网。
- 能够发送邮件。

## 🚀 快速开始

1. **下载**

   从 [Releases](https://github.com/bbbugg/TJUEcard/releases) 页面下载适用于您操作系统的最新版本。
    - `TJUEcard-windows-x86_64.zip` 适用于 Windows
    - `TJUEcard-linux-x86_64.tar.gz` 适用于 Linux
    - `TJUEcard-macos-arm64.tar.gz` 或 `TJUEcard-macos-x86_64.tar.gz` 适用于 macOS

   解压后，Windows系统包含 `TJUEcard.exe` 和 `TJUEcardSetup.exe` 两个文件，Linux和macOS系统则包含 `TJUEcard` 和
   `TJUEcardSetup`。**请确保这两个文件在同一目录下。并且移动到一个相对固定的位置，以后不再移动。**

2. **配置**

   - **Windows**: 管理员权限运行 `TJUEcardSetup.exe`。
   - **Linux/macOS**: 在终端中运行 `sudo ./TJUEcardSetup`。

   运行 TJUEcardSetup 时，程序会引导您进行配置，包括**一卡通用户名**、**一卡通密码**、用于接收邮件的邮箱和授权码等信息。配置成功后，会在程序同目录下生成
   `TJUEcard_user_config.json` 文件。

   > 若不确定一卡通的账号密码，请[验证或找回](https://ecard.tju.edu.cn/epay/person/index)

3. **定时任务**

   配置成功后，程序会询问您是否自动设置系统定时任务。任务将被设置为在每天的固定时间运行 `TJUEcard`
   程序来查询并发送邮件。每天固定时间是您最后一次运行 `TJUEcardSetup` 程序完成配置的时间。

   > **注意**: 为了让定时任务在用户未登录时也能正常运行，在所有系统上设置时都要使用 **管理员权限** 。请确保您以管理员身份运行
   `TJUEcardSetup` 程序（在Windows上右键点击“以管理员身份运行”，在Linux和macOS上使用 `sudo` 命令）。

## 🔧 高级

### 定时任务管理

如果您需要查询或取消已设置的定时任务，可以按照以下步骤操作：

#### Windows

- **查询定时任务**

    - **方式一：命令行**
      打开 **管理员权限** 的命令提示符（cmd）或 PowerShell，输入以下命令：
      
      ```bash
      schtasks /query /tn TJUEcardAutoQuery
      ```
    - **方式二：任务计划程序**
      搜索『任务计划程序』并打开，在任务计划程序库中可以找到名为 `TJUEcardAutoQuery` 的计划，您可以右键单击它进行修改或删除。

- **取消定时任务**

  ```bash
  schtasks /delete /tn TJUEcardAutoQuery /f
  ```

#### Linux

- **查询定时任务**

  脚本会将定时任务添加到系统级的 `/etc/crontab` 文件中。您可以使用以下命令查看内容：

  ```bash
  cat /etc/crontab
  ```

- **修改/取消定时任务**

  您需要以管理员权限编辑 `/etc/crontab` 文件来移除任务。

    1. 使用文本编辑器（如 `nano` 或 `vim`）打开文件：

       ```bash
       sudo nano /etc/crontab
       ```

    2. 在编辑器中，找到并修改/删除包含 `tjuecard` 的那一行。
    3. 保存并退出编辑器。

#### macOS

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

       ```zsh
       sudo rm /Library/LaunchDaemons/com.tjuecard.automatic.plist
       ```

    3. 验证是否已移除：

       ```zsh
       sudo launchctl list | grep tjuecard
       ```

## ❗注意事项

- 本项目仅供学习交流使用，请勿用于非法用途。
- 本项目需要提供您的天津大学一卡通账号密码，登录才能查询电费。并且保存在您的计算机上，不会上传到任何服务器。
- 定时任务的执行时间是根据您运行 `TJUEcardSetup` 程序的时间确定的，每天在您设置的时间运行一次。
- 如果您移动了程序的位置或更改了文件名，定时任务可能会失效，需要重新运行 `TJUEcardSetup` 进行配置，或者手动修改定时任务的配置文件。
- 如需重新配置用户密码、邮箱、查询房间，请重新运行 `TJUEcardSetup` 进行配置。
- 重复运行 `TJUEcardSetup` 时，先前的配置会被自动覆盖。**Linux重复设置定时任务不会覆盖**，请按照上方Linux删除定时任务的教程，删除重复的定时任务。
- 请勿在多个计算机上运行 `TJUEcardSetup` 程序，同一个账号只能同时在一个计算机上保持登录状态，否则每次查询都会自动重新登录。

## 💡常见问题

- **程序会一直在后台运行吗？** 不会。程序只会在定时任务触发时自动运行，平时不会常驻后台或持续占用系统资源。
- **定时任务设置失败**：请以管理员权限运行 `TJUEcardSetup` 程序。
- **定时任务未执行**：请检查定时任务的设置和日志以及 `TJUEcard.log`日志文件。
- **邮件未收到**：请检查您的邮箱配置是否正确，以及垃圾邮件，并查看 `TJUEcard.log` 日志文件。
- **程序报错**：请在 [GitHub Issues](https://github.com/bbbugg/TJUEcard/issues) 中提交您的问题，并附上详细的错误信息。

## 🤝 贡献

我们欢迎任何形式的贡献！如果您有好的想法或需求，欢迎通过以下方式参与项目：

- **提交 Pull Request**: 如果您修复了 bug 或实现了新功能，欢迎提交 PR。
- **创建 Issue**: 如果您有任何建议或发现了问题，请在 [GitHub Issue](https://github.com/bbbugg/TJUEcard/issues) 页面进行讨论。

## 📋 待办事项

- [ ] macOS 的定时任务存在已知问题，预计在下个版本修复。
- [x] 敏感信息目前还是明文存储，预计在下个版本改成加密存储。
- [ ] 考虑支持多房间的查询。
