"""
Xử lý truyền nhận file qua luồng kết nối TCP riêng biệt.
Không gây nghẽn hoặc gián đoạn luồng chat chính.
"""

import os
import socket
import threading
from typing import Callable
from src.config import FILE_CHUNK_SIZE, DOWNLOAD_DIR
from src.protocol import (
    format_hi,
    format_file_header,
    recv_exact,
)


def _get_unique_filepath(directory: str, filename: str) -> str:
    """Tự động đổi tên nếu file đã tồn tại để tránh ghi đè dữ liệu."""
    base, ext = os.path.splitext(filename)
    dest = os.path.join(directory, filename)
    counter = 1
    while os.path.exists(dest):
        dest = os.path.join(directory, f"{base}_{counter}{ext}")
        counter += 1
    return dest


class FileTransferManager:
    """
    Quản lý việc gửi và nhận file qua TCP:
    - Gửi file trên luồng nền (Background Thread), hiển thị tiến độ (25%, 50%, 75%, 100%).
    - Nhận file lưu vào thư mục downloads/ qua file tạm .part.
    - Xóa file .part nếu đứt kết nối giữa chừng để bảo toàn tính toàn vẹn dữ liệu.
    """

    def __init__(self, my_name: str, my_tcp_port: int, peer_manager, notify_func: Callable[[str], None]):
        self.my_name = my_name
        self.my_tcp_port = my_tcp_port
        self.peer_manager = peer_manager
        self.notify = notify_func

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

            self.notify(f"[✓] Gửi file '{filename}' tới {peer_name} thành công hoàn toàn!")

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
        """Tiến trình nhận file, ghi vào file tạm .part và hoàn tất."""
        safe_filename = os.path.basename(filename)
        dest_path = _get_unique_filepath(DOWNLOAD_DIR, safe_filename)
        part_path = dest_path + ".part"

        self.notify(f"[*] Đang nhận file '{safe_filename}' ({filesize:,} bytes) từ {sender_name}...")

        received_bytes = 0
        milestones = {25: False, 50: False, 75: False, 100: False}
        success = False

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

            # Đổi tên file tạm .part thành file chính thức khi nhận đủ 100%
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(part_path, dest_path)
            success = True
            self.notify(f"[✓] Đã nhận thành công file: '{safe_filename}' từ {sender_name}!\n    Vị trí lưu: {dest_path}")

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
