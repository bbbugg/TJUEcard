#!/usr/bin/env bash
# install_tjuecard.sh
# Linux/macOS 安装器：获取 bbbugg/TJUEcard 最新 Release，下载并运行 TJUEcardSetup*
# 依赖：curl 必需；可选：jq、unzip、tar、hdiutil(macOS)

set -euo pipefail

OWNER="bbbugg"
REPO="TJUEcard"
API_LATEST="https://api.github.com/repos/${OWNER}/${REPO}/releases/latest"
UA="TJUEcard-Installer/1.0 (+https://github.com/${OWNER}/${REPO})"

# --- 询问安装目录 ---
default_dir="$(pwd)"
read -r -p "安装目录（留空默认：${default_dir}）： " INSTALL_DIR
INSTALL_DIR="${INSTALL_DIR:-$default_dir}"
mkdir -p "$INSTALL_DIR"

echo "安装目录：$INSTALL_DIR"
cd "$INSTALL_DIR"

# --- OS/ARCH 识别，用于挑选资产 ---
OS="$(uname -s | tr '[:upper:]' '[:lower:]')" # linux / darwin
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *) ARCH="$ARCH" ;;
esac
echo "检测到系统：$OS，架构：$ARCH"

fetch_json() {
  # 优先 jq；没有 jq 用 curl + grep 兜底
  curl -fsSL -H "User-Agent: $UA" "$API_LATEST"
}

# --- 解析最新 Release 资产列表 ---
# 首选路径：jq 可用 -> 精确解析；否则粗糙正则回退
ASSET_NAME=""
ASSET_URL=""

JSON="$(fetch_json || true)"
if [[ -z "$JSON" ]]; then
  echo "获取 Release 信息失败。" >&2
  exit 1
fi

select_asset_with_jq() {
  echo "$JSON" | jq -r '
    .tag_name as $tag
    | (.assets // [])
    | map({name:.name, url:.browser_download_url})
    | . as $assets
    # 优先匹配 TJUEcardSetup* 且与 OS/ARCH 相关的（若资产名带关键词）
    | (
        $assets
        | map(select(.name|test("(?i)^TJUEcardSetup")))
        | (
            # 尝试包含 os/arch 关键词的资产
            (map(select(.name|test("(?i)(linux|darwin|mac|osx)"))) // .)
          )
      + (
        # 备选：任何 exe/sh/pkg/appimage/zip/tar.gz
        $assets
        | map(select(.name|test("(?i)(\\.sh$|\\.pkg$|\\.appimage$|\\.zip$|\\.tar\\.(gz|xz|bz2)$|\\.bin$)")))
      )
      ) 
    | unique
    | (.[0] // empty)
    | [.name, .url] | @tsv
  '
}

select_asset_without_jq() {
  # 粗略抓取：按行扫出 name 与 url，优先包含 TJUEcardSetup*，再兜底
  # 注意：JSON 解析不使用 jq 时不完全健壮，但一般够用
  # 构建 name->url 列表
  # shellcheck disable=SC2016
  printf "%s\n" "$JSON" | awk '
    BEGIN{ name=""; url="" }
    /"name":/{
      match($0, /"name": *"([^"]+)"/, m);
      if(m[1]!=""){ name=m[1] }
    }
    /"browser_download_url":/{
      match($0, /"browser_download_url": *"([^"]+)"/, m);
      if(m[1]!=""){ url=m[1]; printf("%s\t%s\n", name, url); name=""; url="" }
    }
  ' | awk '
    BEGIN{
      bestName=""; bestURL="";
      fallbackName=""; fallbackURL="";
    }
    {
      n=$1; $1=""; sub(/^\t/,""); u=$0;
      # 优先 TJUEcardSetup*
      if (match(n, /^(?i:TJUEcardSetup)/)) {
        if (bestName=="") { bestName=n; bestURL=u }
      } else {
        # 备选常见格式
        if (match(n, /\.(sh|pkg|appimage|zip|tar\.(gz|xz|bz2)|bin)$/i)) {
          if (fallbackName=="") { fallbackName=n; fallbackURL=u }
        }
      }
    }
    END{
      if (bestName!="") { printf("%s\t%s\n", bestName, bestURL) }
      else if (fallbackName!="") { printf("%s\t%s\n", fallbackName, fallbackURL) }
    }
  '
}

if command -v jq >/dev/null 2>&1; then
  sel="$(select_asset_with_jq || true)"
else
  sel="$(select_asset_without_jq || true)"
fi

if [[ -z "$sel" ]]; then
  echo "未在最新 Release 中找到可用资产（优先 TJUEcardSetup*）。" >&2
  exit 1
fi

ASSET_NAME="$(printf "%s" "$sel" | cut -f1)"
ASSET_URL="$(printf "%s" "$sel" | cut -f2-)"
echo "将下载：$ASSET_NAME"
echo "URL：$ASSET_URL"

# --- 下载文件 ---
OUT="$INSTALL_DIR/$ASSET_NAME"
echo "下载到：$OUT"
curl -fL --retry 3 -H "User-Agent: $UA" -o "$OUT" "$ASSET_URL"
echo "下载完成。"

# --- 解压/准备，并寻找 TJUEcardSetup 安装器 ---
workdir="$INSTALL_DIR"
mount_dmg=""
mounted_vol=""

cleanup() {
  # 卸载 dmg（若有）
  if [[ -n "$mount_dmg" && -n "$mounted_vol" && -d "$mounted_vol" ]]; then
    echo "卸载：$mounted_vol"
    hdiutil detach "$mounted_vol" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

find_setup_candidate() {
  local search_dir="$1"
  # 1) 先找 TJUEcardSetup* 可执行 / .sh / .pkg / .app / .AppImage / .bin
  local first
  first="$(find "$search_dir" -maxdepth 3 -type f \( -iname 'TJUEcardSetup*' -o -iname 'TJUEcardSetup*.sh' -o -iname 'TJUEcardSetup*.pkg' -o -iname 'TJUEcardSetup*.appimage' -o -iname 'TJUEcardSetup*.bin' \) | head -n1)"
  if [[ -n "$first" ]]; then echo "$first"; return 0; fi

  # 2) 退而求其次：任意名字但常见安装格式
  first="$(find "$search_dir" -maxdepth 3 -type f \( -iname '*.sh' -o -iname '*.pkg' -o -iname '*.appimage' -o -iname '*.bin' \) | head -n1)"
  if [[ -n "$first" ]]; then echo "$first"; return 0; fi

  # 3) macOS .app（用 open 打开）
  first="$(find "$search_dir" -maxdepth 2 -type d -iname 'TJUEcardSetup*.app' | head -n1)"
  if [[ -n "$first" ]]; then echo "$first"; return 0; fi

  # 4) 兜底：名字里带 TJUEcardSetup 的任何文件
  first="$(find "$search_dir" -maxdepth 3 -type f -iname 'TJUEcardSetup*' | head -n1)"
  if [[ -n "$first" ]]; then echo "$first"; return 0; fi

  return 1
}

INSTALLER_PATH=""

case "$ASSET_NAME" in
  *.zip)
    echo "检测到 zip，解压中..."
    dest="$INSTALL_DIR/$(basename "$ASSET_NAME" .zip)"
    mkdir -p "$dest"
    if command -v unzip >/dev/null 2>&1; then
      unzip -q -o "$OUT" -d "$dest"
    else
      echo "未找到 unzip，macOS 可用 'ditto -x -k' 解压；尝试使用 ditto..."
      if [[ "$OS" == "darwin" ]]; then
        ditto -x -k "$OUT" "$dest"
      else
        echo "请安装 unzip 后重试。" >&2
        exit 1
      fi
    fi
    workdir="$dest"
    ;;
  *.tar.gz|*.tgz)
    echo "检测到 tar.gz，解压中..."
    dest="$INSTALL_DIR/$(basename "$ASSET_NAME" .tar.gz)"
    mkdir -p "$dest"
    tar -xzf "$OUT" -C "$dest"
    workdir="$dest"
    ;;
  *.tar.xz)
    echo "检测到 tar.xz，解压中..."
    dest="$INSTALL_DIR/$(basename "$ASSET_NAME" .tar.xz)"
    mkdir -p "$dest"
    tar -xJf "$OUT" -C "$dest"
    workdir="$dest"
    ;;
  *.dmg)
    if [[ "$OS" == "darwin" ]]; then
      echo "检测到 dmg，挂载中..."
      # -nobrowse 避免弹 Finder
      mount_output="$(hdiutil attach -nobrowse "$OUT")"
      mounted_vol="$(echo "$mount_output" | awk '/\/Volumes\//{print $3; exit}')"
      if [[ -z "$mounted_vol" ]]; then
        echo "挂载 dmg 失败。" >&2
        exit 1
      fi
      echo "已挂载：$mounted_vol"
      workdir="$mounted_vol"
      mount_dmg="1"
    else
      echo "下载的是 .dmg，但当前非 macOS，无法自动安装。" >&2
      exit 1
    fi
    ;;
  *)
    # 直接在当前目录搜索
    workdir="$INSTALL_DIR"
    ;;
esac

# 查找安装器
if INSTALLER_PATH="$(find_setup_candidate "$workdir")"; then
  echo "找到安装器：$INSTALLER_PATH"
else
  echo "未找到 TJUEcardSetup 安装器。请检查 Release 内容。" >&2
  exit 1
fi

# macOS .app 用 open；.pkg 用 installer；其他文件尝试直接执行
run_installer() {
  local p="$1"
  if [[ -d "$p" && "$p" == *.app && "$OS" == "darwin" ]]; then
    echo "启动应用：$p"
    open "$p"
    return 0
  fi
  if [[ "$OS" == "darwin" && "$p" == *.pkg ]]; then
    echo "以系统安装器安装 .pkg（可能需要管理员密码）..."
    sudo /usr/sbin/installer -pkg "$p" -target /
    return 0
  fi
  if [[ -f "$p" ]]; then
    chmod +x "$p" || true
    echo "执行安装器：$p"
    "$p"
    return 0
  fi
  echo "未知的安装器类型：$p" >&2
  return 1
}

run_installer "$INSTALLER_PATH"
echo "安装器已运行完成。脚本结束。"
