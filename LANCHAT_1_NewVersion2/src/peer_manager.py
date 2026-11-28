"""
Quản lý danh sách Peer (Discovery & Liveness).
Sử dụng UDP Broadcast để tìm kiếm và duy trì trạng thái của các node trong mạng LAN.
"""

import socket
import threading
import time
from typing import Callable, Dict, Optional
from src.config import (
    DEFAULT_UDP_PORT,
    BROADCAST_INTERVAL,
    PEER_TIMEOUT,
    DEFAULT_BUFFER_SIZE,
    STATUS_ONLINE,
    DEFAULT_BCAST_IP,
)
from src.protocol import format_hello, parse_hello


class PeerManager:
    """
    Điều phối việc phát hiện và theo dõi các peer:
    - Luồng Broadcaster: phát gói HELLO định kỳ.
    - Luồng Listener: tiếp nhận HELLO, cập nhật bảng peer và quét timeout.
    """

    def __init__(
        self,
        name: str,
        tcp_port: int,
        udp_port: int = DEFAULT_UDP_PORT,
        bcast_ip: str = DEFAULT_BCAST_IP,
        on_peer_change: Optional[Callable[[str, str, dict], None]] = None,
    ):
        self.name = name
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.bcast_ip = bcast_ip
        self.status = STATUS_ONLINE
        self.on_peer_change = on_peer_change

        # Bảng danh sách peers: name -> {'ip': str, 'tcp_port': int, 'status': str, 'last_seen': float}
        self.peers: Dict[str, dict] = {}
        self.peers_lock = threading.Lock()

        self._running = False
        self._broadcaster_thread: Optional[threading.Thread] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._udp_sock: Optional[socket.socket] = None

    def start(self):
        """Khởi động các luồng UDP Broadcaster và Listener."""
        self._running = True

        # Khởi tạo UDP Socket cho việc lắng nghe
        self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Hỗ trợ SO_REUSEPORT trên Linux/macOS để nhiều tiến trình chạy cùng port trên 1 máy
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self._udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass

        self._udp_sock.bind(("", self.udp_port))
        self._udp_sock.settimeout(1.0)

        # Chạy luồng Listener
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

        # Chạy luồng Broadcaster
        self._broadcaster_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._broadcaster_thread.start()

        # Phát thông báo chào mừng ngay khi khởi động
        self.broadcast_hello()

    def stop(self):
        """Dừng hoạt động và đóng socket."""
        self._running = False
        if self._udp_sock:
            try:
                self._udp_sock.close()
            except Exception:
                pass

    def set_status(self, new_status: str):
        """Cập nhật trạng thái người dùng (online/away) và phát broadcast ngay."""
        self.status = new_status
        self.broadcast_hello()

    def broadcast_hello(self):
        """Gửi ngay một gói UDP HELLO ra địa chỉ Broadcast."""
        data = format_hello(self.name, self.tcp_port, self.status)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(data, (self.bcast_ip, self.udp_port))
            sock.close()
        except Exception:
            pass

    def _broadcast_loop(self):
        """Luồng phát bản tin HELLO mỗi 3 giây."""
        while self._running:
            self.broadcast_hello()
            # Ngủ ngắt quãng để tắt nhanh khi stop()
            for _ in range(BROADCAST_INTERVAL * 10):
                if not self._running:
                    break
                time.sleep(0.1)

    def _listen_loop(self):
        """Luồng lắng nghe gói tin HELLO từ các peer và kiểm tra timeout."""
        last_cleanup = time.time()
        while self._running:
            try:
                data, addr = self._udp_sock.recvfrom(DEFAULT_BUFFER_SIZE)
                sender_ip = addr[0]
                parsed = parse_hello(data)
                if parsed:
                    peer_name, peer_tcp_port, peer_status = parsed
                    # Bỏ qua gói tin do chính bản thân gửi
                    if peer_name != self.name:
                        self._update_peer(peer_name, sender_ip, peer_tcp_port, peer_status)
            except socket.timeout:
                pass
            except Exception:
                if not self._running:
                    break

            # Quét dọn các peer quá hạn timeout (mỗi 1 giây)
            now = time.time()
            if now - last_cleanup >= 1.0:
                self._check_timeouts()
                last_cleanup = now

    def _update_peer(self, name: str, ip: str, tcp_port: int, status: str):
        """Cập nhật bảng peer khi nhận được gói HELLO hợp lệ."""
        with self.peers_lock:
            now = time.time()
            if name not in self.peers:
                info = {"ip": ip, "tcp_port": tcp_port, "status": status, "last_seen": now}
                self.peers[name] = info
                if self.on_peer_change:
                    self.on_peer_change(name, "online", info)
            else:
                peer = self.peers[name]
                old_status = peer["status"]
                peer["ip"] = ip
                peer["tcp_port"] = tcp_port
                peer["status"] = status
                peer["last_seen"] = now
                if old_status != status and self.on_peer_change:
                    self.on_peer_change(name, "status_change", peer)

    def _check_timeouts(self):
        """Quét và loại bỏ các peer không gửi heartbeat quá PEER_TIMEOUT giây."""
        now = time.time()
        expired = []
        with self.peers_lock:
            for name, info in list(self.peers.items()):
                if now - info["last_seen"] > PEER_TIMEOUT:
                    expired.append((name, info))
                    del self.peers[name]

        for name, info in expired:
            if self.on_peer_change:
                self.on_peer_change(name, "offline", info)

    def get_peer(self, name: str) -> Optional[dict]:
        """Lấy thông tin của một peer theo tên."""
        with self.peers_lock:
            return self.peers.get(name)

    def get_all_peers(self) -> Dict[str, dict]:
        """Trả về bản sao bảng danh sách peer hiện tại."""
        with self.peers_lock:
            return dict(self.peers)
