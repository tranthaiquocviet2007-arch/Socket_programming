"""
Quản lý kết nối TCP Chat Server và Client giữa các Peer.
Đảm bảo mỗi peer chỉ có tối đa 1 kết nối chat 2 chiều ổn định.
"""

import collections
import socket
import threading
from typing import Callable, Dict, Optional, Tuple
from src.protocol import (
    format_hi,
    format_msg,
    format_bye,
    parse_tcp_frame,
)

CHAT_CONNECT_TIMEOUT = 3
CHAT_HANDSHAKE_TIMEOUT = 5


class ChatManager:
    """
    Điều phối các phiên kết nối TCP:
    - Acceptor Thread: lắng nghe kết nối đến từ các peer khác.
    - Connection Registry: lưu trữ socket kết nối 2 chiều cho từng peer.
    - Receiver Thread: tiếp nhận bản tin MSG, BYE theo thời gian thực.
    - Hàng đợi tin nhắn chưa đọc (unread_messages) cho các đối tác không active.
    """

    def __init__(
        self,
        name: str,
        tcp_port: int,
        peer_manager,
        on_message_received: Callable[[str, str, bool], None],
        on_system_notify: Callable[[str], None],
        file_transfer_handler: Optional[Callable[[socket.socket, str, str, int], None]] = None,
        history_store=None,
    ):
        self.name = name
        self.requested_tcp_port = tcp_port
        self.peer_manager = peer_manager
        self.on_message_received = on_message_received
        self.on_system_notify = on_system_notify
        self.file_transfer_handler = file_transfer_handler
        self.history_store = history_store

        # Đối tác đang mở khung chat trực tiếp
        self.active_partner: Optional[str] = None

        # Danh sách kết nối chat TCP: peer_name -> socket
        self.connections: Dict[str, socket.socket] = {}
        self.conn_lock = threading.Lock()

        # Tin nhắn chưa đọc: peer_name -> list[str]
        self.unread_messages = collections.defaultdict(list)
        self.unread_lock = threading.Lock()

        self._running = False
        self._server_sock: Optional[socket.socket] = None
        self._acceptor_thread: Optional[threading.Thread] = None

    def start(self) -> int:
        """Khởi động TCP Server lắng nghe kết nối. Trả về TCP Port thực tế được bind."""
        self._running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("0.0.0.0", self.requested_tcp_port))
        self._server_sock.listen(10)

        # Lấy port thực tế (rất hữu ích khi bind port 0)
        actual_port = self._server_sock.getsockname()[1]

        self._acceptor_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._acceptor_thread.start()
        return actual_port

    def stop(self):
        """Đóng mọi kết nối TCP và dừng server."""
        self._running = False

        with self.conn_lock:
            for peer_name, sock in list(self.connections.items()):
                try:
                    sock.sendall(format_bye())
                    sock.close()
                except Exception:
                    pass
            self.connections.clear()

        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass

    def _accept_loop(self):
        """Luồng tiếp nhận các kết nối TCP mới."""
        while self._running:
            try:
                client_sock, addr = self._server_sock.accept()
                threading.Thread(
                    target=self._handle_new_connection,
                    args=(client_sock, addr),
                    daemon=True,
                ).start()
            except Exception:
                if not self._running:
                    break

    def _handle_new_connection(self, sock: socket.socket, addr: Tuple[str, int]):
        """Xác thực Handshake HI và phân loại kết nối (Chat hoặc File)."""
        try:
            sock.settimeout(CHAT_HANDSHAKE_TIMEOUT)
            frame_type, data = parse_tcp_frame(sock)
            if frame_type != "HI":
                sock.close()
                return

            peer_name, peer_port, purpose = data

            # Nếu là kết nối truyền file chuyên dụng
            if purpose == "FILE":
                next_frame, file_info = parse_tcp_frame(sock)
                if next_frame == "FILE" and self.file_transfer_handler:
                    filename, filesize = file_info
                    self.file_transfer_handler(sock, peer_name, filename, filesize)
                else:
                    sock.close()
                return

            # Nếu là kết nối chat thông thường
            # Gửi lại Handshake HI phản hồi
            actual_port = self._server_sock.getsockname()[1]
            sock.sendall(format_hi(self.name, actual_port, "CHAT"))
            sock.settimeout(None)  # Chat đang rảnh không phải lỗi handshake.

            with self.conn_lock:
                # Đóng kết nối cũ nếu có để tránh dư thừa socket
                if peer_name in self.connections:
                    try:
                        self.connections[peer_name].close()
                    except Exception:
                        pass
                self.connections[peer_name] = sock

            # Bắt đầu luồng nhận tin nhắn cho peer này
            self._receive_loop(sock, peer_name)

        except Exception:
            try:
                sock.close()
            except Exception:
                pass

    def get_or_create_connection(self, peer_name: str) -> Optional[socket.socket]:
        """Tái sử dụng socket đang mở hoặc chủ động kết nối TCP tới peer nếu chưa có."""
        with self.conn_lock:
            if peer_name in self.connections:
                return self.connections[peer_name]

        peer_info = self.peer_manager.get_peer(peer_name)
        if not peer_info:
            return None

        ip = peer_info["ip"]
        port = peer_info["tcp_port"]

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CHAT_CONNECT_TIMEOUT)
            sock.connect((ip, port))

            # Gửi Handshake HI
            sock.settimeout(CHAT_HANDSHAKE_TIMEOUT)
            actual_port = self._server_sock.getsockname()[1]
            sock.sendall(format_hi(self.name, actual_port, "CHAT"))

            # Chờ phản hồi Handshake từ phía peer
            frame_type, data = parse_tcp_frame(sock)
            if frame_type != "HI":
                sock.close()
                self.on_system_notify(f"Không nhận được phản hồi bắt tay hợp lệ từ {peer_name}.")
                return None

            sock.settimeout(None)
            with self.conn_lock:
                if peer_name in self.connections:
                    sock.close()
                    return self.connections[peer_name]
                self.connections[peer_name] = sock

            # Bắt đầu luồng nhận tin nhắn từ peer này
            threading.Thread(
                target=self._receive_loop,
                args=(sock, peer_name),
                daemon=True,
            ).start()

            return sock
        except Exception as e:
            if sock is not None:
                sock.close()
            self.on_system_notify(f"Không thể kết nối TCP tới {peer_name} ({ip}:{port}): {e}")
            return None

    def _receive_loop(self, sock: socket.socket, peer_name: str):
        """Luồng đọc liên tục các frame TCP từ peer."""
        while self._running:
            frame_type, data = parse_tcp_frame(sock)
            if not frame_type or frame_type == "BYE":
                # Đối phương ngắt kết nối
                break

            if frame_type == "MSG":
                text = data
                # Ghi lịch sử TRƯỚC khi hiển thị để không mất tin nếu UI gặp lỗi
                if self.history_store:
                    self.history_store.log_text(peer_name, "received", text)
                is_active = (self.active_partner == peer_name)
                if is_active:
                    self.on_message_received(peer_name, text, True)
                else:
                    with self.unread_lock:
                        self.unread_messages[peer_name].append(text)
                        unread_count = len(self.unread_messages[peer_name])
                    self.on_message_received(peer_name, text, False)

        # Dọn dẹp kết nối khi thoát vòng lặp
        with self.conn_lock:
            was_current = self.connections.get(peer_name) == sock
            if was_current:
                del self.connections[peer_name]
        try:
            sock.close()
        except Exception:
            pass

        if was_current and self.active_partner == peer_name:
            self.active_partner = None
            self.on_system_notify(f"[{peer_name} đã ngắt kết nối chat]")

    def send_chat(self, text: str) -> bool:
        """Gửi tin nhắn text tới đối tác đang active."""
        partner = self.active_partner
        if not partner:
            self.on_system_notify("Bạn chưa chọn người để chat. Dùng lệnh /chat <tên> để bắt đầu.")
            return False

        sock = self.get_or_create_connection(partner)
        if not sock:
            self.on_system_notify(f"Không thể tạo kết nối đến {partner}.")
            return False

        try:
            sock.sendall(format_msg(text))
            # Chỉ ghi lịch sử khi gửi thành công thực sự
            if self.history_store:
                self.history_store.log_text(partner, "sent", text)
            return True
        except Exception as e:
            self.on_system_notify(f"Lỗi gửi tin nhắn: {e}")
            with self.conn_lock:
                if partner in self.connections:
                    del self.connections[partner]
            return False

    def switch_partner(self, peer_name: str) -> bool:
        """Chuyển đổi đối tác chat hiện tại sang peer_name."""
        sock = self.get_or_create_connection(peer_name)
        if not sock:
            return False

        self.active_partner = peer_name

        # Đọc và dọn dẹp các tin nhắn chưa đọc
        with self.unread_lock:
            unreads = list(self.unread_messages.get(peer_name, []))
            self.unread_messages[peer_name].clear()

        # Nếu có kho lịch sử, UI sẽ in toàn bộ hội thoại (đã gồm cả tin chưa đọc),
        # nên không replay ở đây để tránh in trùng.
        if unreads and self.history_store is None:
            self.on_system_notify(f"--- {len(unreads)} tin nhắn chưa đọc từ {peer_name} ---")
            for msg in unreads:
                self.on_message_received(peer_name, msg, True)
            self.on_system_notify("------------------------------------------")

        return True

    def leave_chat(self):
        """Rời khỏi cuộc trò chuyện hiện tại và đóng kết nối sạch sẽ."""
        if not self.active_partner:
            self.on_system_notify("Bạn hiện không ở trong phòng chat nào.")
            return

        target = self.active_partner
        self.active_partner = None

        with self.conn_lock:
            sock = self.connections.pop(target, None)
            if sock:
                try:
                    sock.sendall(format_bye())
                    sock.close()
                except Exception:
                    pass

        self.on_system_notify(f"Đã rời cuộc trò chuyện với {target}.")
