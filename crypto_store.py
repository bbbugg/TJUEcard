"""
本地密钥文件 + AES-256-GCM 加解密：
- 数据密钥存放在 config.py 配置的 _KEY_FILE_PATH（默认 BASE_DIR/.tjuecard_key）。
- JSON 内仅保存密文对象（含算法、版本、nonce、密文）。
警告：
- 删除或丢失密钥文件将导致现有 JSON 中的密文无法解密，需要重新运行 setup 重新生成配置。
"""
from __future__ import annotations

import os
import json
import base64
from typing import Dict, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import _KEY_FILE_PATH, _KID, _ALG


def get_key_file_path() -> str:
    """返回本地密钥文件路径。"""
    return _KEY_FILE_PATH


def _read_key_from_file() -> bytes:
    with open(_KEY_FILE_PATH, "rb") as f:
        data = f.read().strip()
    return base64.b64decode(data)


def _write_key_to_file(key: bytes) -> None:
    """
    以尽可能严格的权限写入密钥文件：
    - POSIX: 0600
    - Windows: os.chmod 作用有限，仍建议依赖用户账户隔离
    """
    os.makedirs(os.path.dirname(_KEY_FILE_PATH) or ".", exist_ok=True)

    if os.name == "posix":
        fd = os.open(_KEY_FILE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(base64.b64encode(key))
        finally:
            try:
                os.close(fd)
            except Exception:
                pass
    else:
        with open(_KEY_FILE_PATH, "wb") as f:
            f.write(base64.b64encode(key))
        try:
            os.chmod(_KEY_FILE_PATH, 0o600)
        except Exception:
            pass  # Windows 上不强制


def _load_key(create: bool) -> bytes:
    """
    载入本地数据密钥。
    - create=True：不存在则生成并写入文件
    - create=False：不存在则抛出异常
    """
    if os.path.exists(_KEY_FILE_PATH):
        return _read_key_from_file()
    if create:
        key = os.urandom(32)  # 256-bit
        _write_key_to_file(key)
        return key
    raise FileNotFoundError(f"未找到本地密钥文件：{_KEY_FILE_PATH}")


def encrypt_for_storage(plaintext: str) -> Dict[str, Any]:
    """
    使用本地数据密钥加密，返回可直接写入 JSON 的密文对象。
    """
    key = _load_key(create=True)  # 加密时若不存在则创建
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "v": 1,
        "alg": _ALG,
        "kid": _KID,
        "nonce": base64.b64encode(nonce).decode(),
        "ct": base64.b64encode(ct).decode(),
    }


def decrypt_from_storage(blob: Dict[str, Any]) -> str:
    """
    解密 JSON 中的密文对象，返回明文字符串。
    """
    if not isinstance(blob, dict):
        raise ValueError("密文对象格式错误")
    if blob.get("alg") != _ALG:
        raise ValueError(f"不支持的算法: {blob.get('alg')}")
    key = _load_key(create=False)  # 解密时必须已有密钥
    aes = AESGCM(key)
    nonce = base64.b64decode(blob["nonce"])
    ct = base64.b64decode(blob["ct"])
    pt = aes.decrypt(nonce, ct, None)
    return pt.decode("utf-8")


def migrate_plaintext_to_encrypted(config_path: str) -> bool:
    """
    将已有 JSON 配置中的明文字段迁移为加密字段：
      - credentials.password -> credentials.password_enc
      - email_notifier.auth_code -> email_notifier.auth_code_enc
    迁移成功会覆盖写回原文件。返回是否发生了修改。
    """
    if not os.path.exists(config_path):
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False

    changed = False

    # 迁移登录密码
    creds = data.get("credentials") or {}
    if isinstance(creds, dict):
        if "password_enc" not in creds and "password" in creds and creds.get("password"):
            try:
                enc = encrypt_for_storage(str(creds["password"]))
                creds["password_enc"] = enc
                del creds["password"]
                changed = True
            except Exception as e:
                print(f"[警告] 迁移密码时出错: {e}")
        data["credentials"] = creds

    # 迁移邮箱授权码
    notifier = data.get("email_notifier") or {}
    if isinstance(notifier, dict):
        if "auth_code_enc" not in notifier and "auth_code" in notifier and notifier.get("auth_code"):
            try:
                enc = encrypt_for_storage(str(notifier["auth_code"]))
                notifier["auth_code_enc"] = enc
                del notifier["auth_code"]
                changed = True
            except Exception as e:
                print(f"[警告] 迁移邮箱授权码时出错: {e}")
        data["email_notifier"] = notifier

    if changed:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            return False

    return changed