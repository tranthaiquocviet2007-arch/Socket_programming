"""
Lưu lịch sử chat cục bộ bằng file JSON.

Cơ chế "bộ nhớ đệm + đĩa":
- Dữ liệu được giữ trong RAM (cache) để thao tác nhanh trong cùng tiến trình.
- Mỗi lần đọc/ghi đều lấy bản mới nhất từ đĩa và khóa liên tiến trình
  (flock) để nhiều node chạy CÙNG thư mục không ghi đè lịch sử của nhau.
- Ghi kiểu atomic: file tạm + os.replace, tránh hỏng JSON khi tắt đột ngột.

Hai kho riêng biệt, tạo tại thư mục đang chạy lệnh (os.getcwd()):
- sent_messages.json     : tin nhắn / file do máy này gửi đi
- received_messages.json : tin nhắn / file do peer gửi đến máy này

Mỗi file là một mảng JSON:
[
  {"peer": "Bob", "type": "text", "text": "Chào Bob", "ts": 1690000000.1},
  {"peer": "Bob", "type": "file", "name": "a.pdf", "size": 1234,
   "path": "/.../downloads/Bob/a.pdf", "ts": 1690000010.5}
]

Lưu ý:
- Chỉ tạo file khi chưa tồn tại, không bao giờ ghi đè dữ liệu đã có.
- Nếu file JSON hỏng, đổi tên thành *.broken-<timestamp> trước khi ghi mới.
- Khi nhiều node dùng chung file, mỗi bản ghi có trường "peer" để phân biệt;
  nhờ vậy bộ lọc theo peer vẫn trả đúng hội thoại của từng node.
"""

import hashlib
import json
import os
import tempfile
import threading
import time
from typing import Dict, List, Optional, Tuple

from src.config import DOWNLOAD_DIR, RECEIVED_MESSAGES_FILE, SENT_MESSAGES_FILE

try:
    import fcntl  # POSIX: khóa liên tiến trình
except ImportError:  # pragma: no cover - Windows
    fcntl = None

# Hướng của bản ghi
DIRECTION_SENT = "sent"
DIRECTION_RECEIVED = "received"


class _ProcessFileLock:
    """
    Khóa độc quyền giữa các tiến trình cho một file dữ liệu.

    Lock file được đặt trong thư mục tạm hệ thống (không tạo thêm file rác
    trong thư mục chạy lệnh), tên dựa trên hash đường dẫn tuyệt đối.
    Trên nền tảng không có fcntl, lớp này chỉ hoạt động như no-op.
    """

    def __init__(self, data_path: str):
        digest = hashlib.sha1(os.path.abspath(data_path).encode("utf-8")).hexdigest()[:16]
        self.lock_path = os.path.join(tempfile.gettempdir(), f"lanchat_history_{digest}.lock")
        self._handle = None

    def __enter__(self):
        if fcntl is None:
            return self
        try:
            self._handle = open(self.lock_path, "a+")
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        except OSError:
            self._handle = None
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._handle is not None:
            try:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                self._handle.close()
            except OSError:
                pass
            self._handle = None
        return False


class ChatHistory:
    """Quản lý lịch sử chat theo từng peer, an toàn giữa nhiều luồng/tiến trình."""

    def __init__(
        self,
        downloads_dir: Optional[str] = None,
        sent_file: Optional[str] = None,
        received_file: Optional[str] = None,
    ):
        self.downloads_dir = downloads_dir or DOWNLOAD_DIR
        self.sent_file = sent_file or SENT_MESSAGES_FILE
        self.received_file = received_file or RECEIVED_MESSAGES_FILE

        self._lock = threading.Lock()

        # Bộ nhớ đệm: "sent"/"received" -> list[dict]
        self._cache: Dict[str, List[dict]] = {}

        # Chỉ khởi tạo những gì chưa tồn tại
        os.makedirs(self.downloads_dir, exist_ok=True)
        self._ensure_json_file(self.sent_file)
        self._ensure_json_file(self.received_file)

    # ==================== KHỞI TẠO ====================

    @staticmethod
    def _ensure_json_file(path: str):
        """Tạo file JSON rỗng nếu chưa có. Tuyệt đối không ghi đè file đã tồn tại."""
        if os.path.exists(path):
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            # "x" = chỉ tạo mới, báo lỗi nếu file xuất hiện giữa lúc kiểm tra và lúc mở
            with open(path, "x", encoding="utf-8") as f:
                f.write("[]")
                f.flush()
        except FileExistsError:
            pass
        except OSError:
            pass

    def _file_for(self, direction: str) -> str:
        return self.sent_file if direction == DIRECTION_SENT else self.received_file

    # ==================== ĐỌC / GHI ====================

    def _read_from_disk(self, direction: str) -> Tuple[List[dict], bool]:
        """
        Đọc mới nhất từ đĩa. Trả về (records, is_corrupt).
        Không sửa/xóa file của người dùng ở bước đọc.
        """
        path = self._file_for(direction)
        records: List[dict] = []

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except FileNotFoundError:
            return records, False
        except OSError:
            return records, False

        if not content:
            return records, False

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return records, True

        if not isinstance(data, list):
            return records, True

        for item in data:
            if (
                isinstance(item, dict)
                and item.get("type") in ("text", "file")
                and "peer" in item
            ):
                records.append(item)

        return records, False

    def _backup_broken_file(self, direction: str):
        """Đổi tên file hỏng thành .broken-<timestamp> để không mất dữ liệu người dùng."""
        path = self._file_for(direction)
        backup = f"{path}.broken-{int(time.time())}"
        try:
            os.replace(path, backup)
        except OSError:
            pass

    def _save_to_disk(self, direction: str, records: List[dict]):
        """Ghi toàn bộ danh sách ra file JSON theo kiểu atomic (temp + replace)."""
        path = self._file_for(direction)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        tmp_path = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except OSError:
            # Không để lỗi ghi đĩa làm sập luồng chat
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass

    def _append(self, direction: str, record: dict):
        with self._lock:
            with _ProcessFileLock(self._file_for(direction)):
                # Luôn đọc lại từ đĩa: tiến trình khác có thể vừa ghi thêm
                records, is_corrupt = self._read_from_disk(direction)

                if is_corrupt:
                    # Sao lưu file hỏng trước khi ghi dữ liệu mới
                    self._backup_broken_file(direction)
                    records = []

                records.append(record)
                self._save_to_disk(direction, records)
                self._cache[direction] = records

    # ==================== API CÔNG KHAI ====================

    def log_text(self, peer_name: str, direction: str, text: str):
        """Lưu một tin nhắn text. direction: DIRECTION_SENT hoặc DIRECTION_RECEIVED."""
        self._append(
            direction,
            {
                "peer": peer_name,
                "type": "text",
                "text": text,
                "ts": time.time(),
            },
        )

    def log_file(self, peer_name: str, direction: str, name: str, size: int, path: str):
        """Lưu sự kiện truyền/nhận file thành công."""
        self._append(
            direction,
            {
                "peer": peer_name,
                "type": "file",
                "name": name,
                "size": size,
                "path": path,
                "ts": time.time(),
            },
        )

    def get_conversation(self, peer_name: str) -> List[dict]:
        """
        Trả về lịch sử chat với một peer: gộp tin đã gửi + đã nhận,
        sắp xếp theo thời gian tăng dần. Mỗi bản ghi có thêm khóa "direction".
        """
        with self._lock:
            with _ProcessFileLock(self.sent_file):
                sent, _ = self._read_from_disk(DIRECTION_SENT)
            with _ProcessFileLock(self.received_file):
                received, _ = self._read_from_disk(DIRECTION_RECEIVED)

            self._cache[DIRECTION_SENT] = sent
            self._cache[DIRECTION_RECEIVED] = received

        merged = [
            dict(record, direction=DIRECTION_SENT)
            for record in sent
            if record.get("peer") == peer_name
        ]
        merged.extend(
            dict(record, direction=DIRECTION_RECEIVED)
            for record in received
            if record.get("peer") == peer_name
        )

        merged.sort(key=lambda record: record.get("ts", 0))
        return merged
