"""
Giao diện dòng lệnh người dùng (Terminal UI).
Sử dụng prompt_toolkit kết hợp patch_stdout() để chống xé rách giao diện
khi có tin nhắn mới hoặc thông báo hệ thống đến bất đồng bộ.
Tự động fallback sang chế độ in đồng bộ tiêu chuẩn nếu thiếu prompt_toolkit.
"""

import sys
import threading
import time
from typing import Optional
from src.config import STATUS_ONLINE, STATUS_AWAY, VALID_STATUSES

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
    HAS_PROMPT_TOOLKIT = True
except ImportError:
    HAS_PROMPT_TOOLKIT = False


class TerminalUI:
    """Điều khiển giao diện Terminal và xử lý các lệnh tương tác của người dùng."""

    def __init__(self, name: str):
        self.name = name
        self.peer_manager = None
        self.chat_manager = None
        self.file_transfer = None

        self._running = False
        self._print_lock = threading.Lock()
        self._peer_index_cache = {}  # Lưu số thứ tự STT -> tên peer

    def bind_controllers(self, peer_manager, chat_manager, file_transfer):
        """Liên kết UI với các bộ điều khiển logic."""
        self.peer_manager = peer_manager
        self.chat_manager = chat_manager
        self.file_transfer = file_transfer

    def print_message(self, text: str):
        """In thông báo ra terminal an toàn giữa các luồng."""
        with self._print_lock:
            print(text)
            sys.stdout.flush()

    def on_peer_change(self, peer_name: str, event_type: str, info: dict):
        """Callback khi bảng peer có thay đổi."""
        if event_type == "online":
            self.print_message(f"\n[+] Peer mới online: {peer_name} ({info['ip']}:{info['tcp_port']})")
        elif event_type == "status_change":
            self.print_message(f"\n[*] {peer_name} đổi trạng thái: [{info['status']}]")
        elif event_type == "offline":
            self.print_message(f"\n[-] Peer offline (timeout): {peer_name}")

    def on_message_received(self, peer_name: str, text: str, is_active: bool):
        """Callback khi có tin nhắn TCP đến."""
        if is_active:
            self.print_message(f"\n[{peer_name}]: {text}")
        else:
            with self.chat_manager.unread_lock:
                count = len(self.chat_manager.unread_messages[peer_name])
            self.print_message(f"\n[Tin nhắn mới từ {peer_name}]: {text} (Có {count} tin chưa đọc. Gõ /chat {peer_name} để xem)")

    def on_system_notify(self, text: str):
        """Callback thông báo chung của hệ thống."""
        self.print_message(f"\n{text}")

    def show_help(self):
        """In bảng hướng dẫn sử dụng."""
        help_text = """
============================= CÁC LỆNH HỖ TRỢ =============================
  /list                 : Xem danh sách các peer đang online/away kèm số thứ tự
  /chat <tên|STT>       : Bắt đầu chat riêng với peer
  /send <đường_dẫn_file>: Gửi file cho peer đang chat hiện tại
  /status <online|away> : Cập nhật trạng thái bản thân và broadcast ngay
  /leave                : Rời khỏi cuộc trò chuyện hiện tại
  /help                 : Xem hướng dẫn lệnh
  /quit                 : Đóng mọi socket và thoát chương trình
===========================================================================
"""
        self.print_message(help_text)

    def cmd_list(self):
        """Hiển thị danh sách peer đẹp mắt kèm STT."""
        peers = self.peer_manager.get_all_peers()
        if not peers:
            self.print_message("\n[i] Hiện chưa phát hiện peer nào khác trong mạng LAN.")
            return

        self._peer_index_cache.clear()
        now = time.time()

        lines = [
            "\n" + "=" * 75,
            f"{'STT':<4} | {'Tên Peer':<15} | {'Địa chỉ IP':<16} | {'TCP Port':<8} | {'Trạng thái':<10} | {'Heartbeat'}",
            "-" * 75,
        ]

        idx = 1
        for peer_name, info in sorted(peers.items()):
            self._peer_index_cache[str(idx)] = peer_name
            ago = int(now - info["last_seen"])
            status_str = info["status"]
            lines.append(
                f"{idx:<4} | {peer_name:<15} | {info['ip']:<16} | {info['tcp_port']:<8} | {status_str:<10} | {ago}s trước"
            )
            idx += 1

        lines.append("=" * 75)
        lines.append("[Mẹo]: Bạn có thể gõ /chat <STT> hoặc /chat <tên> để bắt đầu chat.")
        self.print_message("\n".join(lines))

    def cmd_chat(self, target: str):
        """Bắt đầu phiên chat với peer."""
        target_name = self._peer_index_cache.get(target, target)
        if target_name == self.name:
            self.print_message("[!] Không thể tự chat với chính mình.")
            return

        peer_info = self.peer_manager.get_peer(target_name)
        if not peer_info:
            self.print_message(f"[!] Không tìm thấy peer '{target_name}'. Gõ /list để xem danh sách.")
            return

        success = self.chat_manager.switch_partner(target_name)
        if success:
            self.print_message(f"\n[✓] Đã kết nối và mở phiên chat với '{target_name}'. Gõ tin nhắn và Enter để gửi.")

    def cmd_send(self, file_path: str):
        """Gửi file cho partner hiện tại."""
        active = self.chat_manager.active_partner
        if not active:
            self.print_message("[!] Bạn chưa mở chat với ai. Hãy dùng /chat <tên> trước khi gửi file.")
            return
        self.file_transfer.send_file_async(active, file_path)

    def cmd_status(self, new_status: str):
        """Đổi trạng thái của bản thân."""
        status_clean = new_status.lower().strip()
        if status_clean not in VALID_STATUSES:
            self.print_message(f"[!] Trạng thái không hợp lệ. Chọn giữa: {', '.join(VALID_STATUSES)}")
            return
        self.peer_manager.set_status(status_clean)
        self.print_message(f"[✓] Đã cập nhật trạng thái thành: [{status_clean}]")

    def run(self):
        """Khởi chạy vòng lặp nhận lệnh từ bàn phím."""
        self._running = True
        self.show_help()

        if HAS_PROMPT_TOOLKIT:
            self._run_prompt_toolkit()
        else:
            self._run_standard_input()

    def _get_prompt_string(self) -> str:
        """Tạo chuỗi nhắc lệnh hiển thị partner đang chat."""
        active = self.chat_manager.active_partner if self.chat_manager else None
        if active:
            return f"[{self.name} -> {active}] > "
        return f"[{self.name}] > "

    def _run_prompt_toolkit(self):
        """Chế độ giao diện cao cấp với prompt_toolkit + patch_stdout."""
        session = PromptSession()
        while self._running:
            try:
                with patch_stdout():
                    line = session.prompt(self._get_prompt_string())
                self._handle_user_input(line.strip())
            except (EOFError, KeyboardInterrupt):
                self._handle_user_input("/quit")
                break

    def _run_standard_input(self):
        """Chế độ fallback tiêu chuẩn sử dụng input() thông thường."""
        while self._running:
            try:
                line = input(self._get_prompt_string())
                self._handle_user_input(line.strip())
            except (EOFError, KeyboardInterrupt):
                self._handle_user_input("/quit")
                break

    def _handle_user_input(self, raw: str):
        """Phân tích và điều hướng input của người dùng."""
        if not raw:
            return

        if raw.startswith("/"):
            parts = raw.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "/list":
                self.cmd_list()
            elif cmd == "/chat":
                if not arg:
                    self.print_message("[!] Cú pháp: /chat <tên|STT>")
                else:
                    self.cmd_chat(arg)
            elif cmd == "/send":
                if not arg:
                    self.print_message("[!] Cú pháp: /send <đường_dẫn_file>")
                else:
                    self.cmd_send(arg)
            elif cmd == "/status":
                if not arg:
                    self.print_message("[!] Cú pháp: /status <online|away>")
                else:
                    self.cmd_status(arg)
            elif cmd == "/leave":
                self.chat_manager.leave_chat()
            elif cmd == "/help":
                self.show_help()
            elif cmd == "/quit":
                self.print_message("\nĐang thoát chương trình, đóng toàn bộ kết nối...")
                self._running = False
            else:
                self.print_message(f"[!] Lệnh không xác định: '{cmd}'. Gõ /help để xem danh sách lệnh.")
        else:
            # Gửi tin nhắn chat thông thường
            if not self.chat_manager.active_partner:
                self.print_message("[!] Bạn chưa chọn người để chat. Gõ /list và /chat <tên> để bắt đầu.")
            else:
                self.chat_manager.send_chat(raw)
