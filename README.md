# 天津大学电费查询自动化工具

本工具可以自动查询天津大学电费信息，并在电费低于一定值的时候发送邮件提醒。

## ⭐主要功能

- 自动化查询电费
- 低于一定的电量时可以发送邮件提醒
- 跨平台支持（Windows, Linux, ~~macOS~~）
- 自动设置定时任务，每天检查一次电费的余额

## 运行要求

### 系统

| 操作系统          | 支持架构                                      |
|---------------|-------------------------------------------|
| Windows 10+   | x86_64                                    |
| Ubuntu 22.04+ | x86_64                                    |
| ~~macOS 13+~~ | ~~x86_64 (Intel), arm64 (Apple Silicon)~~ |

> 其他操作系统版本或架构未经测试，不确定能否正常使用。

### 邮箱

目前支持 QQ 邮箱和 163 邮箱（SMTP）。

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

   首次运行时，程序会引导您进行配置，包括用户名、密码、用于接收邮件的邮箱等信息。配置成功后，会在程序同目录下生成
   `TJUEcard_user_config.json` 文件。

3. **定时任务**

   配置成功后，程序会询问您是否自动设置系统定时任务。任务将被设置为在每天的固定时间运行 `TJUEcard`
   程序来查询并发送邮件。每天固定时间是您最后一次运行 `TJUEcardSetup` 程序完成配置的时间。

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

       ```zsh
       sudo rm /Library/LaunchDaemons/com.tjuecard.automatic.plist
       ```

    3. 验证是否已移除：

       ```zsh
       sudo launchctl list | grep tjuecard
       ```

## ❗注意事项

- 本项目仅供学习交流使用，请勿用于非法用途。
- 定时任务的执行时间是根据您运行 `TJUEcardSetup` 程序的时间确定的，每天在您设置的时间运行一次。
- 如果您移动了程序的位置，定时任务可能会失效，需要重新运行 `TJUEcardSetup` 进行配置。
- 确保`TJUEcardSetup` `TJUEcard` 两个程序在同一目录下。
- 在运行完`TJUEcardSetup` 程序配置完成后，`TJUEcard` 程序可以手动运行，作为一次查询。
- 如需重新配置用户密码、邮箱，可以直接修改 `TJUEcard_user_config.json` 文件中对应的值。如需重新配置查询房间，请重新运行
  `TJUEcardSetup` 进行配置。

## 💡常见问题

- **定时任务设置失败**：请以管理员权限运行 `TJUEcardSetup` 程序。
- **定时任务未执行**：请检查您的系统时间和定时任务的设置是否正确。
- **邮件未收到**：请检查您的邮箱配置是否正确，以及垃圾邮件文件夹。
- **程序报错**：请在 [GitHub Issues](https://github.com/bbbugg/TJUEcard/issues) 中提交您的问题，并附上详细的错误信息。

## 贡献

我们欢迎任何形式的贡献！如果您有好的想法或需求，欢迎通过以下方式参与项目：

- **提交 Pull Request**: 如果您修复了Bug或实现了新功能，请提交PR。
- **创建 Issue**: 如果您有任何建议或发现了问题，请在 [Issue](https://github.com/bbbugg/TJUEcard/issues) 页面进行讨论。

## TODO

- [ ] 测试macOS系统上通过定时任务运行
