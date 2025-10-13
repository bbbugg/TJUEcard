# 定时任务管理

如果您需要查询或取消已设置的定时任务，可以按照以下步骤操作：

## Windows

- **方式一：命令行**

    - **查询定时任务**

      打开 **管理员权限** 的命令提示符（cmd）或 PowerShell，输入以下命令：

      ```bash
      schtasks /query /tn TJUEcardAutoQuery
      ```

    - **取消定时任务**

      ```bash
      schtasks /delete /tn TJUEcardAutoQuery /f
      ```
- **方式二：任务计划程序**

  搜索『任务计划程序』并打开，在任务计划程序库中可以找到名为 `TJUEcardAutoQuery` 的计划，您可以右键单击它进行修改或删除。

## Linux

- **查询定时任务**

  脚本会自动检测系统环境，并将定时任务添加到合适的位置。通常情况下，任务配置文件会创建在以下三个位置之一：
    - `/etc/cron.d/tjuecard-auto-query` (首选方式，适用于Ubuntu/Debian等系统，单个文件形式)
    - `/etc/crontabs/root` (用于 OpenWrt/Alpine 等系统，追加到文件末尾)
    - `/etc/crontab` (传统方式，追加到文件末尾)

  您可以依次检查这些文件来找到任务配置。
  ```bash
  # 例如，检查 /etc/cron.d 目录：
  cat /etc/cron.d/tjuecard-auto-query

  # 检查 /etc/crontabs/root 文件：
  cat /etc/crontabs/root

  # 检查 /etc/crontab 文件：
  cat /etc/crontab
  ```

- **修改/取消定时任务**

  根据任务所在的位置(通过`查询定时任务`确定)，以管理员权限编辑或删除对应的文件即可。
    - **如果任务在 `/etc/cron.d/tjuecard-auto-query`**：
        - 修改定时任务：
          ```bash
          sudo nano /etc/cron.d/tjuecard-auto-query
          ```
        - 删除定时任务：
          ```bash
          sudo rm /etc/cron.d/tjuecard-auto-query
          ```
    - **如果任务在 `/etc/crontabs/root` 或 `/etc/crontab`**，您需要编辑该文件并修改/移除包含 `TJUEcard` 的相关行。
      ```bash
      # 例如：/etc/crontabs/root 文件
      sudo nano /etc/crontabs/root
  
      # /etc/crontab 文件
      sudo nano /etc/crontab
      ```

## macOS

- **查询定时任务**

  打开终端，输入以下命令查看当前 root 用户的 `crontab` 任务列表：

  ```zsh
  sudo crontab -l
  ```

- **取消定时任务**

  打开终端，输入以下命令编辑当前 root 用户的 `crontab` 文件，并移除包含 `TJUEcard` 的相关行：
   ```zsh
   sudo crontab -e
   ```

  验证是否已移除：

   ```zsh
   sudo crontab -l | grep TJUEcard
   ```