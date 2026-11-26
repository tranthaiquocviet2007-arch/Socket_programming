"""
=============================================================================
CLIENT-SERVER DEMO: CHATROOM SERVER (MÔ HÌNH MÁY CHỦ TRUNG TÂM)
=============================================================================
Theo đúng slide 20-25 bài giảng 'Seminar_Socket Programming.pdf':
- 1 Server trung tâm phục vụ N Client đồng thời.
- Quy trình chuẩn của TCP Server:
    socket() -> bind() -> listen() -> accept() -> recv()/sendall() -> close()
- Sử dụng mô hình Đa luồng (Multi-threading): Mỗi client kết nối vào được cấp
  một luồng (thread) riêng để xử lý, không làm nghẽn các client khác.
- Server làm nhiệm vụ chuyển tiếp (broadcast) tin nhắn từ một client đến tất
  cả các thành viên còn lại trong phòng.
=============================================================================
"""

import socket
import threading
import sys

# Cấu hình địa chỉ IP và Cổng dịch vụ
HOST = '0.0.0.0'   # Lắng nghe trên mọi card mạng (LAN, Loopback, WiFi)
PORT = 50000       # Cổng TCP của dịch vụ Chatroom
BUFFER_SIZE = 1024 # Kích thước bộ đệm nhận tin nhắn (bytes)

# Danh sách quản lý các client đang online: {client_socket: nickname}
clients = {}
# Khóa (Lock) đồng bộ để bảo vệ cấu trúc dữ liệu clients khi nhiều luồng cùng thêm/xóa
clients_lock = threading.Lock()

def broadcast(message: str, sender_socket=None):
    """
    Gửi tin nhắn broadcast đến tất cả các client đang online trong phòng chat.
    Nếu có chỉ định sender_socket, sẽ không gửi ngược lại cho chính người gửi đó.
    """
    data = message.encode('utf-8')
    with clients_lock:
        for client_sock in list(clients.keys()):
            if client_sock != sender_socket:
                try:
                    # sendall() đảm bảo toàn bộ dữ liệu byte được gửi hết qua mạng TCP
                    client_sock.sendall(data)
                except Exception:
                    # Nếu socket client bị lỗi hoặc rớt mạng đột ngột, đóng và loại bỏ
                    client_sock.close()
                    if client_sock in clients:
                        del clients[client_sock]

def handle_client(client_socket: socket.socket, client_address: tuple):
    """
    Hàm thực thi trong luồng riêng biệt của từng client.
    Nhiệm vụ: Đọc tin nhắn từ client_socket và chuyển tiếp (broadcast) cho phòng chat.
    """
    nickname = f"{client_address[0]}:{client_address[1]}"
    try:
        # Bước 1: Nhận thông điệp đầu tiên từ Client là Nickname
        # recv() là BLOCKING CALL: Luồng này sẽ dừng ở đây chờ đến khi client gửi dữ liệu
        raw_nick = client_socket.recv(BUFFER_SIZE)
        if not raw_nick:
            return
        nickname = raw_nick.decode('utf-8').strip()

        with clients_lock:
            clients[client_socket] = nickname

        # Thông báo tới toàn bộ phòng chat có thành viên mới tham gia
        join_msg = f"[Hệ thống] >>> {nickname} ({client_address[0]}:{client_address[1]}) đã tham gia phòng chat!"
        print(join_msg)
        broadcast(join_msg, sender_socket=client_socket)

        # Gửi lời chào riêng tới client mới tham gia
        welcome_msg = f"[Hệ thống] Chào mừng {nickname}! Gõ /quit để rời phòng chat.\n"
        client_socket.sendall(welcome_msg.encode('utf-8'))

        # Bước 2: Vòng lặp nhận tin nhắn từ client và broadcast
        while True:
            # recv() đọc dữ liệu byte từ bộ đệm socket của hệ điều hành
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                # Trong giao thức TCP, khi client gọi close(), Server nhận được gói tin FIN.
                # Lúc này recv() sẽ lập tức trả về chuỗi rỗng b'' báo hiệu kết thúc luồng dữ liệu (EOF).
                break
            
            msg = data.decode('utf-8').strip()
            if msg.lower() == "/quit":
                break
            
            formatted_msg = f"[{nickname}]: {msg}"
            print(formatted_msg)
            broadcast(formatted_msg, sender_socket=client_socket)

    except ConnectionResetError:
        print(f"[!] Client {nickname} ngắt kết nối đột ngột.")
    except Exception as e:
        print(f"[Lỗi xử lý client {nickname}]: {e}")
    finally:
        # Bước 3: Dọn dẹp tài nguyên khi client thoát
        with clients_lock:
            if client_socket in clients:
                del clients[client_socket]
        client_socket.close()
        
        leave_msg = f"[Hệ thống] <<< {nickname} đã rời phòng chat."
        print(leave_msg)
        broadcast(leave_msg)

def main():
    print("=====================================================")
    print("       CHATROOM SERVER - MÔ HÌNH CLIENT/SERVER       ")
    print("=====================================================")

    # 1. Tạo socket TCP (SOCK_STREAM) sử dụng IPv4 (AF_INET)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 2. Bật cờ SO_REUSEADDR để có thể bind lại ngay cổng mà không bị lỗi 'Address already in use'
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 3. Gắn (bind) socket với IP và Port của máy chủ
    server_socket.bind((HOST, PORT))

    # 4. Chuyển socket sang trạng thái lắng nghe (listen) với hàng đợi kết nối là 5
    server_socket.listen(5)
    print(f"[*] Server đang lắng nghe tại {HOST}:{PORT}...")
    print("[*] Nhấn Ctrl+C để dừng server.\n")

    try:
        while True:
            # 5. accept() bị BLOCK chờ client kết nối tới.
            # Khi có kết nối, hệ điều hành hoàn thành TCP 3-Way Handshake và trả về socket giao tiếp mới
            client_sock, client_addr = server_socket.accept()
            print(f"[+] Nhận kết nối mới từ {client_addr[0]}:{client_addr[1]}")

            # 6. Khởi tạo một Thread mới để phục vụ client này mà không làm nghẽn accept()
            # daemon=True: Khi tiến trình server chính dừng, luồng con tự động tắt theo
            thread = threading.Thread(
                target=handle_client,
                args=(client_sock, client_addr),
                daemon=True
            )
            thread.start()
            print(f"[*] Tổng số client đang online: {threading.active_count() - 1}")

    except KeyboardInterrupt:
        print("\n[*] Server nhận tín hiệu dừng (Ctrl+C). Đang đóng socket...")
    finally:
        with clients_lock:
            for s in clients:
                try:
                    s.close()
                except Exception:
                    pass
            clients.clear()
        server_socket.close()
        print("[*] Server đã dừng an toàn.")

if __name__ == "__main__":
    main()