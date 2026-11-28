"""
Xử lý truyền nhận file qua luồng kết nối TCP riêng biệt.
Không gây nghẽn hoặc gián đoạn luồng chat chính.
"""

import os
import socket
import threading
import uuid
from typing import Callable
from src.config import FILE_CHUNK_SIZE, FILE_IO_TIMEOUT, DOWNLOAD_DIR
from src.protocol import (
    format_hi,
    format_file_header,
    format_ok,
    parse_tcp_frame,
    recv_exact,
)


# Ký tự không an toàn khi đưa tên peer (do mạng gửi tới) vào đường dẫn.
_UNSAFE_PATH_CHARS = set('\\/:*?"<>|')
_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _sanitize_peer_component(peer_name: str) -> str:
    """
    Biến tên peer thành MỘT thành phần thư mục an toàn.

    Tên peer đến từ gói tin mạng nên không được tin tưởng: nếu chứa '/', '..'
    hoặc ký tự điều khiển, nó có thể thoát khỏi thư mục downloads/.
    """
    cleaned = "".join(
        "_" if (ch in _UNSAFE_PATH_CHARS or ord(ch) < 32 or ch == "\x7f") else ch
        for ch in (peer_name or "")
    )
    cleaned = cleaned.strip().strip(".")
    if not cleaned:
        return "unknown_peer"
    if cleaned.split(".")[0].upper() in _WINDOWS_RESERVED_NAMES:
        cleaned = "_" + cleaned
    return cleaned[:80]


def _safe_filename(filename: str) -> str:
    """Lấy phần tên file thuần, chặn cả kiểu tấn công '..\\..\\evil' của Windows."""
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = "".join(ch for ch in name if ord(ch) >= 32 and ch != "\x7f")
    name = name.strip().strip(".")
    if not name:
        name = "unnamed_file"
    return name[:200]


def _reserve_unique_filepath(directory: str, filename: str) -> str:
    """
    Giữ chỗ một tên file duy nhất theo kiểu atomic bằng O_CREAT|O_EXCL.

    Khác với 'kiểm tra tồn tại rồi mới ghi' (TOCTOU), cách này đảm bảo hai
    luồng/tiến trình cùng lúc không bao giờ nhận trùng một đường dẫn — kể cả
    khi hai peer cùng gửi một file tên giống nhau.

    File rỗng được tạo trước như một "vé giữ chỗ"; ngay sau đó os.replace()
    ghi đè nó bằng nội dung thật. Nếu tiến trình bị kill giữa lúc nhận, chỉ
    còn file .part (không để lại file đích rỗng).
    """
    base, ext = os.path.splitext(filename)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    counter = 0
    while True:
        candidate = filename if counter == 0 else f"{base}_{counter}{ext}"
        dest = os.path.join(directory, candidate)
        try:
            fd = os.open(dest, flags, 0o644)
        except FileExistsError:
            counter += 1
            continue
        os.close(fd)
        return dest


class FileTransferManager:
    """
    Quản lý việc gửi và nhận file qua TCP:
    - Gửi file trên luồng nền (Background Thread), hiển thị tiến độ (25%, 50%, 75%, 100%).
    - Nhận file lưu vào downloads/<tên_peer>/ để mỗi cuộc trò chuyện có thư mục riêng.
    - Ghi vào file tạm .part rồi mới đổi tên, tránh file đích bị dở dang.
    - Xóa file .part nếu đứt kết nối giữa chừng để bảo toàn tính toàn vẹn dữ liệu.
    """

    def __init__(self, my_name: str, my_tcp_port: int, peer_manager, notify_func: Callable[[str], None],
                 history_store=None):
        self.my_name = my_name
        self.my_tcp_port = my_tcp_port
        self.peer_manager = peer_manager
        self.notify = notify_func
        self.history_store = history_store

        # Dùng chung thư mục downloads với kho lịch sử (nếu có) để nhất quán
        self.download_dir = (
            history_store.downloads_dir if history_store is not None else DOWNLOAD_DIR
        )
        os.makedirs(self.download_dir, exist_ok=True)

    def send_file_async(self, peer_name: str, file_path: str):
        """Khởi chạy luồng gửi file độc lập."""
        threading.Thread(
            target=self._send_file_worker,
            args=(peer_name, file_path),
            daemon=True,
        ).start()

    def _send_file_worker(self, peer_name: str, file_path: str):
        """Tiến trình gửi file qua kết nối TCP riêng biệt."""
        if not os.path.isfile(file_path):
            self.notify(f"[Gửi file thất bại]: File '{file_path}' không tồn tại.")
            return

        peer_info = self.peer_manager.get_peer(peer_name)
        if not peer_info:
            self.notify(f"[Gửi file thất bại]: Không tìm thấy thông tin mạng của {peer_name}.")
            return

        ip = peer_info["ip"]
        port = peer_info["tcp_port"]
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)

        self.notify(f"[*] Bắt đầu gửi '{filename}' ({filesize:,} bytes) đến {peer_name}...")

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # ISSUE-05: chặn connect/send/recv treo vô hạn khi mạng đứt
            sock.settimeout(FILE_IO_TIMEOUT)
            sock.connect((ip, port))

            # 1. Gửi Handshake chuyên dụng với mục đích FILE
            sock.sendall(format_hi(self.my_name, self.my_tcp_port, "FILE"))

            # 2. Gửi File Header
            sock.sendall(format_file_header(filename, filesize))

            # 3. Đọc và truyền dữ liệu theo từng khối (chunk)
            sent_bytes = 0
            milestones = {25: False, 50: False, 75: False, 100: False}

            with open(file_path, "rb") as f:
                while sent_bytes < filesize:
                    chunk = f.read(FILE_CHUNK_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    sent_bytes += len(chunk)

                    percent = int((sent_bytes / filesize) * 100) if filesize > 0 else 100
                    for m in [25, 50, 75, 100]:
                        if percent >= m and not milestones[m]:
                            milestones[m] = True
                            self.notify(f"[Tiến độ gửi tới {peer_name}]: {filename} -> {m}%")

            if sent_bytes != filesize:
                raise IOError(
                    f"File thay đổi kích thước khi đang gửi ({sent_bytes}/{filesize} bytes)."
                )

            # 4. ISSUE-06: chờ ACK từ receiver — chỉ báo thành công khi bên kia đã lưu xong
            ack_type, ack_size = parse_tcp_frame(sock)
            if ack_type != "OK" or ack_size != filesize:
                raise ConnectionError(
                    f"Không nhận được xác nhận (ACK) hợp lệ từ {peer_name} "
                    f"(nhận: {ack_type}/{ack_size}, cần: OK/{filesize})."
                )

            self.notify(f"[✓] Gửi file '{filename}' tới {peer_name} thành công hoàn toàn!")
            if self.history_store:
                self.history_store.log_file(
                    peer_name, "sent", filename, filesize, os.path.abspath(file_path)
                )

        except Exception as e:
            self.notify(f"[Lỗi gửi file tới {peer_name}]: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def handle_incoming_file(self, sock: socket.socket, sender_name: str, filename: str, filesize: int):
        """Xử lý nhận file được gọi từ ChatManager Acceptor trên luồng riêng."""
        threading.Thread(
            target=self._receive_file_worker,
            args=(sock, sender_name, filename, filesize),
            daemon=True,
        ).start()

    def _receive_file_worker(self, sock: socket.socket, sender_name: str, filename: str, filesize: int):
        """Tiến trình nhận file, ghi vào downloads/<peer>/ và hoàn tất."""
        # ISSUE-05: không chờ recv vô hạn nếu mạng đứt giữa chừng
        sock.settimeout(FILE_IO_TIMEOUT)

        safe_filename = _safe_filename(filename)

        # Mỗi peer có thư mục riêng: downloads/<tên_peer>/<tên_file>
        peer_dir = os.path.join(self.download_dir, _sanitize_peer_component(sender_name))
        os.makedirs(peer_dir, exist_ok=True)

        # Tên .part ngẫu nhiên: hai luồng nhận cùng lúc không bao giờ ghi chung một file tạm
        part_path = os.path.join(peer_dir, f".lanchat-{uuid.uuid4().hex}.part")

        self.notify(f"[*] Đang nhận file '{safe_filename}' ({filesize:,} bytes) từ {sender_name}...")

        received_bytes = 0
        milestones = {25: False, 50: False, 75: False, 100: False}
        completed = False
        dest_path = None

        try:
            with open(part_path, "wb") as f:
                while received_bytes < filesize:
                    to_read = min(FILE_CHUNK_SIZE, filesize - received_bytes)
                    chunk = sock.recv(to_read)
                    if not chunk:
                        raise ConnectionResetError("Kết nối bị ngắt đột ngột trong khi đang nhận file.")
                    f.write(chunk)
                    received_bytes += len(chunk)

                    percent = int((received_bytes / filesize) * 100) if filesize > 0 else 100
                    for m in [25, 50, 75, 100]:
                        if percent >= m and not milestones[m]:
                            milestones[m] = True
                            self.notify(f"[Tiến độ nhận từ {sender_name}]: {safe_filename} -> {m}%")

            # Chỉ khi đã nhận đủ 100% mới giữ chỗ tên đích và đổi tên atomically
            dest_path = _reserve_unique_filepath(peer_dir, safe_filename)
            try:
                os.replace(part_path, dest_path)
            except Exception:
                # Không để lại file rỗng giữ chỗ nếu bước đổi tên thất bại
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except Exception:
                        pass
                raise
            completed = True

            # ISSUE-06: báo ACK để sender chỉ báo thành công khi file đã lưu xong
            try:
                sock.sendall(format_ok(filesize))
            except Exception as e:
                self.notify(
                    f"[Cảnh báo] Đã lưu file nhưng không gửi được ACK tới {sender_name}: {e}"
                )

        except Exception as e:
            self.notify(f"[Lỗi nhận file từ {sender_name}]: {e}")
            # Xóa file .part để đảm bảo không để lại dữ liệu lỗi
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass
        finally:
            try:
                sock.close()
            except Exception:
                pass

        if completed:
            # Ghi đúng tên file thực tế trên đĩa (có thể đã được thêm _1, _2 khi trùng tên)
            saved_name = os.path.basename(dest_path)
            self.notify(
                f"[✓] Đã nhận thành công file: '{saved_name}' từ {sender_name}!\n"
                f"    Vị trí lưu: {dest_path}"
            )
            if self.history_store:
                self.history_store.log_file(
                    sender_name, "received", saved_name, filesize, os.path.abspath(dest_path)
                )
