"""
=============================================================================
LANCHAT_FUNDAMENTAL: P2P LAN CHAT (MÔ HÌNH NGANG HÀNG TRÊN MẠNG CỤC BỘ)
=============================================================================
Mục đích giáo trình:
- Minh họa cách kết hợp hài hòa 2 giao thức mạng cốt lõi:
  1. UDP (SOCK_DGRAM): Khám phá các peer trong mạng LAN qua cơ chế Broadcast.
  2. TCP (SOCK_STREAM): Thiết lập phiên trò chuyện 1-1 tin cậy, không mất gói.
- Lập trình thuần Python Standard Library, không phụ thuộc thư viện ngoài.
- Giải thích bản chất socket, họ địa chỉ IPv4, luồng (threads) và blocking I/O.
=============================================================================
"""

import socket
import threading
import time
import sys

# --- CẤU HÌNH THÔNG SỐ MẠNG ---
UDP_PORT = 50005           # Cổng UDP thống nhất để các node phát hiện (discover) nhau
BROADCAST_INTERVAL = 3     # Chu kỳ phát gói tin HELLO (giây)
PEER_TIMEOUT = 10          # Quá thời gian này không thấy HELLO thì coi như đã offline
BUFFER_SIZE = 1024         # Kích thước bộ đệm nhận gói tin (bytes)

class P2PChatNode:
    """Đại diện cho một nút (Node/Peer) độc lập trong mạng P2P LAN Chat."""

    def __init__(self, name: str, tcp_port: int = 0, udp_port: int = UDP_PORT):
        self.name = name
        self.udp_port = udp_port
        self.running = True
        
        # Danh bạ các peer online: {peer_name: {'ip': ip, 'port': tcp_port, 'last_seen': timestamp}}
        self.peers = {}
        # Lock đồng bộ hóa danh bạ tránh xung đột (race condition) giữa các luồng
        self.peers_lock = threading.Lock()
        
        # Phiên kết nối TCP hiện tại đang trò chuyện
        self.active_conn = None
        self.active_peer_name = None
        self.conn_lock = threading.Lock()
        
        # Callback phục vụ kiểm thử tự động (nếu có gán)
        self.on_message_received = None

        # ---------------------------------------------------------------------
        # 1. KHỞI TẠO TCP SERVER SOCKET (Lắng nghe kết nối trò chuyện đến)
        # - AF_INET: Sử dụng họ địa chỉ IPv4 (ví dụ 192.168.1.x)
        # - SOCK_STREAM: Giao thức TCP hướng kết nối, đảm bảo toàn vẹn dữ liệu
        # ---------------------------------------------------------------------
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Cho phép tái sử dụng địa chỉ/cổng ngay lập tức sau khi dừng chương trình
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Gán socket vào tất cả interface mạng ('0.0.0.0'). Nếu port=0, HĐH tự cấp port rảnh
        self.tcp_server.bind(('0.0.0.0', tcp_port))
        self.tcp_server.listen(5) # Hàng đợi tối đa 5 kết nối đang chờ duyệt
        self.tcp_port = self.tcp_server.getsockname()[1]

        # ---------------------------------------------------------------------
        # 2. KHỞI TẠO UDP SOCKET (Phát và nhận gói tin Discovery - Broadcast)
        # - SOCK_DGRAM: Giao thức UDP phi kết nối, truyền gói tin độc lập (datagram)
        # ---------------------------------------------------------------------
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bật cờ SO_BROADCAST: Cho phép gửi gói tin đến địa chỉ quảng bá (255.255.255.255)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # SO_REUSEPORT (Linux/macOS): Nhiều tiến trình trên cùng 1 máy có thể cùng bind cổng UDP
        if hasattr(socket, 'SO_REUSEPORT'):
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.udp_sock.bind(('', self.udp_port))

    def start(self):
        """Khởi chạy các luồng nền phục vụ giao tiếp song song không gây nghẽn."""
        # Luồng 1: Định kỳ phát sóng UDP HELLO quảng bá sự hiện diện của mình
        threading.Thread(target=self._broadcast_loop, daemon=True).start()
        # Luồng 2: Lắng nghe các gói UDP HELLO từ các peer khác trong LAN
        threading.Thread(target=self._listen_udp_loop, daemon=True).start()
        # Luồng 3: Chấp nhận các kết nối TCP đến từ bạn bè muốn chat
        threading.Thread(target=self._tcp_server_loop, daemon=True).start()
        print(f"[*] Node '{self.name}' đã khởi động thành công!")
        print(f"[*] TCP Port: {self.tcp_port} | UDP Discovery Port: {self.udp_port}")
        print("[*] Gõ /help để xem hướng dẫn lệnh.\n")

    def _broadcast_loop(self):
        """Phát tín hiệu UDP HELLO mỗi 3 giây thông báo: Tên và Cổng TCP."""
        while self.running:
            try:
                # Gói tin định dạng text: HELLO|<Tên>|<Cổng TCP>
                # Cần .encode('utf-8') vì Socket chỉ truyền nhận dòng byte nhị phân (bytes)
                msg = f"HELLO|{self.name}|{self.tcp_port}".encode('utf-8')
                self.udp_sock.sendto(msg, ('<broadcast>', self.udp_port))
            except Exception:
                pass
            time.sleep(BROADCAST_INTERVAL)

    def _listen_udp_loop(self):
        """Nhận gói UDP từ mạng LAN và cập nhật vào danh bạ peer."""
        while self.running:
            try:
                # recvfrom() bị BLOCK (chặn dừng luồng) cho đến khi có gói tin bay tới
                data, addr = self.udp_sock.recvfrom(BUFFER_SIZE)
                text = data.decode('utf-8', errors='ignore')
                if text.startswith("HELLO|"):
                    parts = text.split("|")
                    if len(parts) == 3:
                        _, peer_name, peer_tcp_port = parts
                        # Bỏ qua gói tin do chính máy mình phát ra
                        if peer_name != self.name:
                            with self.peers_lock:
                                self.peers[peer_name] = {
                                    'ip': addr[0],
                                    'port': int(peer_tcp_port),
                                    'last_seen': time.time()
                                }
            except Exception:
                break

    def get_active_peers(self):
        """Lọc và trả về danh sách các peer còn sống (gửi HELLO trong vòng 10s)."""
        now = time.time()
        active = {}
        with self.peers_lock:
            for name, info in list(self.peers.items()):
                if now - info['last_seen'] <= PEER_TIMEOUT:
                    active[name] = info
                else:
                    del self.peers[name] # Loại bỏ peer đã hết thời gian phản hồi
        return active

    def _tcp_server_loop(self):
        """Luồng TCP Server: Chấp nhận yêu cầu kết nối chat 1-1 từ peer khác."""
        while self.running:
            try:
                # accept() bị BLOCK chờ client kết nối tới. Trả về: (socket mới, địa chỉ client)
                conn, addr = self.tcp_server.accept()
                threading.Thread(target=self._handle_incoming_conn, args=(conn, addr), daemon=True).start()
            except Exception:
                break

    def _handle_incoming_conn(self, conn, addr):
        """Xử lý kết nối TCP từ một peer khác gọi tới mình."""
        peer_name = f"{addr[0]}:{addr[1]}"
        try:
            # Gói tin đầu tiên là handshake định danh người gọi: CONNECT|<Tên>
            handshake = conn.recv(BUFFER_SIZE).decode('utf-8')
            if handshake.startswith("CONNECT|"):
                peer_name = handshake.split("|")[1]

            with self.conn_lock:
                if self.active_conn:
                    try:
                        self.active_conn.close()
                    except Exception:
                        pass
                self.active_conn = conn
                self.active_peer_name = peer_name

            print(f"\n[Kết nối] Peer '{peer_name}' ({addr[0]}) đã mở kênh chat với bạn!")
            print(f"[*] Giờ bạn có thể gõ tin nhắn trực tiếp để gửi tới '{peer_name}'.\n> ", end="", flush=True)

            # Vòng lặp đọc tin nhắn liên tục trên socket TCP đã kết nối
            while self.running:
                # recv() sẽ BLOCK cho đến khi đối phương gửi dữ liệu qua TCP
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    # Trong TCP, recv() trả về rỗng (b'') nghĩa là đối phương đã đóng kết nối (FIN)
                    print(f"\n[Ngắt kết nối] Peer '{peer_name}' đã đóng phiên chat.\n> ", end="", flush=True)
                    break
                decoded_msg = data.decode('utf-8')
                if self.on_message_received:
                    self.on_message_received(peer_name, decoded_msg)
                print(f"\n[{peer_name}]: {decoded_msg}\n> ", end="", flush=True)
        except Exception:
            pass
        finally:
            with self.conn_lock:
                if self.active_conn == conn:
                    self.active_conn = None
                    self.active_peer_name = None
            conn.close()

    def connect_to_peer(self, target_name: str):
        """Chủ động mở kết nối TCP tới một peer đã khám phá được trong danh bạ."""
        peers = self.get_active_peers()
        if target_name not in peers:
            print(f"[-] Không tìm thấy '{target_name}'. Gõ /list để kiểm tra danh bạ.")
            return

        target = peers[target_name]
        try:
            # Tạo TCP socket để thực hiện kết nối chủ động (Client mode)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # connect() thực hiện bắt tay 3 bước TCP (3-way handshake: SYN, SYN-ACK, ACK)
            sock.connect((target['ip'], target['port']))
            # Gửi gói handshake thông báo tên của mình
            sock.sendall(f"CONNECT|{self.name}".encode('utf-8'))

            with self.conn_lock:
                if self.active_conn:
                    try:
                        self.active_conn.close()
                    except Exception:
                        pass
                self.active_conn = sock
                self.active_peer_name = target_name

            print(f"[+] Đã kết nối TCP thành công tới '{target_name}' ({target['ip']}:{target['port']}).")
            print("[+] Nhập nội dung và Enter để gửi tin nhắn.")

            # Bật luồng phụ để đón nhận câu trả lời phản hồi từ đối phương qua socket này
            threading.Thread(target=self._recv_loop_client, args=(sock, target_name), daemon=True).start()
        except Exception as e:
            print(f"[-] Kết nối tới '{target_name}' thất bại: {e}")

    def _recv_loop_client(self, sock, peer_name):
        """Luồng đọc phản hồi từ socket TCP do chính mình chủ động kết nối đi."""
        while self.running:
            try:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    print(f"\n[Ngắt kết nối] '{peer_name}' đã ngắt kết nối.\n> ", end="", flush=True)
                    break
                decoded_msg = data.decode('utf-8')
                if self.on_message_received:
                    self.on_message_received(peer_name, decoded_msg)
                print(f"\n[{peer_name}]: {decoded_msg}\n> ", end="", flush=True)
            except Exception:
                break
        with self.conn_lock:
            if self.active_conn == sock:
                self.active_conn = None
                self.active_peer_name = None
        sock.close()

    def send_chat(self, text: str):
        """Gửi chuỗi văn bản qua kết nối TCP hiện hành bằng sendall()."""
        with self.conn_lock:
            if not self.active_conn:
                print("[-] Bạn chưa kết nối với ai. Dùng lệnh /chat <tên> để bắt đầu trò chuyện.")
                return
            try:
                # sendall() đảm bảo toàn bộ chuỗi byte được đẩy hết vào kernel buffer của TCP
                self.active_conn.sendall(text.encode('utf-8'))
            except Exception as e:
                print(f"[-] Gửi tin nhắn thất bại: {e}")
                self.active_conn = None
                self.active_peer_name = None

    def stop(self):
        """Dừng node và giải phóng mọi tài nguyên socket của hệ điều hành."""
        self.running = False
        with self.conn_lock:
            if self.active_conn:
                try:
                    self.active_conn.close()
                except Exception:
                    pass
        try:
            self.tcp_server.close()
            self.udp_sock.close()
        except Exception:
            pass

def main():
    print("=====================================================")
    print("      LANCHAT_FUNDAMENTAL: P2P LAN CHAT NODE         ")
    print("=====================================================")
    name = input("Nhập tên hiển thị của bạn (username): ").strip()
    while not name or "|" in name:
        name = input("Tên không được rỗng hoặc chứa ký tự '|'. Nhập lại: ").strip()

    node = P2PChatNode(name=name)
    node.start()

    try:
        while True:
            cmd = input("> ").strip()
            if not cmd:
                continue
            if cmd == "/quit":
                print("[*] Đang thoát chương trình...")
                break
            elif cmd == "/help":
                print("--- BẢNG LỆNH HỖ TRỢ ---")
                print("  /list         : Hiển thị các peer đang online trong mạng LAN")
                print("  /chat <tên>   : Kết nối TCP 1-1 tới peer được chỉ định")
                print("  /help         : Xem hướng dẫn sử dụng")
                print("  /quit         : Đóng kết nối và thoát ứng dụng")
            elif cmd == "/list":
                peers = node.get_active_peers()
                if not peers:
                    print("[i] Hiện chưa tìm thấy peer nào khác trong mạng LAN (đang dò UDP...).")
                else:
                    print(f"--- DANH SÁCH PEER ONLINE ({len(peers)}) ---")
                    now = time.time()
                    for peer_name, info in peers.items():
                        diff = int(now - info['last_seen'])
                        print(f" - {peer_name:<15} IP: {info['ip']:<15} TCP Port: {info['port']:<6} (vừa thấy {diff}s trước)")
            elif cmd.startswith("/chat "):
                target_name = cmd[6:].strip()
                node.connect_to_peer(target_name)
            else:
                node.send_chat(cmd)
    except (KeyboardInterrupt, EOFError):
        print("\n[*] Nhận tín hiệu ngắt (Ctrl+C). Đang thoát...")
    finally:
        node.stop()
        print("[*] Tạm biệt!")

if __name__ == "__main__":
    main()