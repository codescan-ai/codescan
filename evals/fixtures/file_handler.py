"""
file_handler.py — File upload, export, and report generation service.
Handles user-submitted documents, archives, and scheduled exports.
"""

import os
import pickle
import subprocess
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional


UPLOAD_DIR = "/var/app/uploads"
EXPORT_DIR = "/var/app/exports"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".csv"}
MAX_FILE_SIZE_MB = 10


def get_upload_path(user_id: int, filename: str) -> Path:
    return Path(UPLOAD_DIR) / str(user_id) / filename


def allowed_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def human_readable_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ------------------------------------------------------------------ #
# VULNERABILITY 1: Path Traversal — filename from user input is joined
# directly onto the base upload dir. A filename like
# `../../etc/passwd` lets the caller read or overwrite arbitrary files.
# ------------------------------------------------------------------ #
def save_upload(user_id: int, filename: str, data: bytes) -> str:
    # Dangerous: filename is not sanitised — allows directory traversal
    dest = os.path.join(UPLOAD_DIR, str(user_id), filename)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def safe_save_upload(user_id: int, filename: str, data: bytes) -> str:
    safe_name = Path(filename).name  # strip any directory components
    dest = Path(UPLOAD_DIR) / str(user_id) / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return str(dest)


# ------------------------------------------------------------------ #
# VULNERABILITY 2: Command Injection — the filename is interpolated
# directly into a shell command string. A filename like
# `file.pdf; rm -rf /` will execute arbitrary shell commands.
# ------------------------------------------------------------------ #
def generate_thumbnail(filename: str, width: int = 200) -> str:
    output = filename.replace(".", "_thumb.")
    # Dangerous: unsanitised filename in shell command
    os.system(f"convert {filename} -resize {width}x {output}")
    return output


def generate_thumbnail_safe(filename: str, width: int = 200) -> str:
    output = filename.replace(".", "_thumb.")
    # Safe: passes args as a list — no shell interpolation
    subprocess.run(
        ["convert", filename, "-resize", f"{width}x", output],
        check=True,
        shell=False,
    )
    return output


# ------------------------------------------------------------------ #
# VULNERABILITY 3: Insecure Deserialization — pickle.loads on untrusted
# data allows arbitrary code execution. An attacker-crafted payload can
# run any Python code on the server at deserialization time.
# ------------------------------------------------------------------ #
def load_user_session(session_blob: bytes) -> dict:
    # Dangerous: pickle.loads on attacker-controlled bytes
    return pickle.loads(session_blob)


def load_user_session_safe(session_blob: bytes) -> dict:
    import json
    return json.loads(session_blob.decode("utf-8"))


# ------------------------------------------------------------------ #
# VULNERABILITY 4: Zip/Tar Slip — extracting a tar archive without
# checking member paths allows files to be written outside the target
# directory (e.g. overwriting ~/.bashrc or /etc/cron.d entries).
# ------------------------------------------------------------------ #
def extract_archive(archive_path: str, dest_dir: str):
    # Dangerous: no path validation on archive members
    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(path=dest_dir)


def extract_archive_safe(archive_path: str, dest_dir: str):
    dest = Path(dest_dir).resolve()
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            member_path = (dest / member.name).resolve()
            if not str(member_path).startswith(str(dest)):
                raise ValueError(f"Path traversal detected in archive: {member.name}")
        tar.extractall(path=dest_dir)


def delete_upload(user_id: int, filename: str) -> bool:
    path = get_upload_path(user_id, filename)
    if path.exists():
        path.unlink()
        return True
    return False


def list_uploads(user_id: int) -> list:
    base = Path(UPLOAD_DIR) / str(user_id)
    if not base.exists():
        return []
    return [f.name for f in base.iterdir() if f.is_file()]


def get_file_metadata(path: str) -> Optional[dict]:
    p = Path(path)
    if not p.exists():
        return None
    stat = p.stat()
    return {
        "name": p.name,
        "size": human_readable_size(stat.st_size),
        "modified": stat.st_mtime,
    }
