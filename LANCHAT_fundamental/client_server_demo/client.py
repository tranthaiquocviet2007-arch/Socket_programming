"""
=============================================================================
CLIENT-SERVER DEMO: CHATROOM CLIENT (MÁY KHÁCH THAM GIA PHÒNG CHAT)
=============================================================================
Theo đúng slide 20-25 bài giảng 'Seminar_Socket Programming.pdf':
- Quy trình chuẩn của TCP Client:
    socket() -> connect() -> sendall()/recv() -> close()
- Cấu trúc 2 luồng song song (Concurrency):
    1. Luồng nhận (receive_thread): Chạy ngầm trong nền, chuyên gọi recv() để
       đón nhận tin nhắn từ server và in ra màn hình mà không bị nghẽn.
    2. Luồng gửi (main thread): Chạy vòng lặp đọc bàn phím input() từ người dùng
       và dùng sendall() để gửi lên server.
- Việc dùng 2 luồng giải quyết bài toán cốt lõi: Nếu chỉ dùng 1 luồng, khi gọi
  input() chương trình sẽ bị đứng chờ gõ phím, không thể hiển thị tin nhắn mới
  của bạn bè gửi tới!
=============================================================================
"""

import socket
import threading
import sys

DEFAULT_HOST = '127.0.0.1' # Mặc định kết nối loopback nội bộ máy
DEFAULT_PORT = 50000       # Cổng mặc định của Server
BUFFER_SIZE = 1024         # Kích thước bộ đệm nhận (bytes)

def receive_loop(sock: socket.socket):
    """
    Luồng nền chuyên đón nhận dữ liệu từ Server.
    Vì recv() là blocking call, ta phải tách vào một Thread riêng biệt.
    """
    while True:
        try:
            # recv() dừng chờ cho đến khi server đẩy dữ liệu xuống
            data = sock.recv(BUFFER_SIZE)
            if not data:
                # Server đã đóng kết nối (gói FIN)
                print("\n[Hệ thống] Mất kết nối tới máy chủ (Server closed connection).")
                break
            
            # Giải mã bytes thành ký tự unicode bằng UTF-8
            message = data.decode('utf-8')
            # In tin nhắn và hiển thị lại dấu nhắc lệnh '> '
            print(f"\n{message}\n> ", end="", flush=True)
        except ConnectionResetError:
            print("\n[Hệ thống] Kết nối tới máy chủ bị ngắt đột ngột.")
            break
        except Exception:
            break
    
    try:
        sock.close()
    except Exception:
        pass
    print("\n[*] Luồng nhận tin nhắn đã kết thúc. Nhấn Enter để thoát hoàn toàn.")

def main():
    print("=====================================================")
    print("       CHATROOM CLIENT - MÔ HÌNH CLIENT/SERVER       ")
    print("=====================================================")

    # Nhập thông tin cấu hình từ người dùng
    server_ip = input(f"Nhập IP của Server (mặc định '{DEFAULT_HOST}'): ").strip()
    if not server_ip:
        server_ip = DEFAULT_HOST

    port_input = input(f"Nhập Port của Server (mặc định {DEFAULT_PORT}): ").strip()
    server_port = int(port_input) if port_input.isdigit() else DEFAULT_PORT

    nickname = input("Nhập tên hiển thị (nickname) của bạn: ").strip()
    while not nickname:
        nickname = input("Nickname không được để trống. Vui lòng nhập: ").strip()

    # 1. Tạo socket TCP (SOCK_STREAM) với họ địa chỉ IPv4 (AF_INET)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 2. connect() thực hiện bắt tay 3 bước TCP tới Server
        print(f"[*] Đang kết nối tới Server {server_ip}:{server_port}...")
        client_socket.connect((server_ip, server_port))
        print("[+] Kết nối thành công!")

        # 3. Gửi Nickname làm gói tin định danh đầu tiên
        client_socket.sendall(nickname.encode('utf-8'))

        # 4. Khởi chạy Luồng Nhận tin nhắn chạy song song dưới nền
        recv_thread = threading.Thread(target=receive_loop, args=(client_socket,), daemon=True)
        recv_thread.start()

        # 5. Luồng chính (Main Thread): Đọc bàn phím và gửi dữ liệu lên Server
        print("[*] Nhập tin nhắn và nhấn Enter để gửi. Gõ /quit để rời phòng chat.\n")
        while True:
            msg = input("> ").strip()
            if not msg:
                continue
            
            # Gửi thông điệp đã encode UTF-8 qua socket
            client_socket.sendall(msg.encode('utf-8'))
            
            if msg.lower() == "/quit":
                print("[*] Đang rời phòng chat...")
                break

    except ConnectionRefusedError:
        print(f"[-] Không thể kết nối tới {server_ip}:{server_port}. Máy chủ chưa bật hoặc sai cổng.")
    except (KeyboardInterrupt, EOFError):
        print("\n[*] Ngắt kết nối theo yêu cầu người dùng.")
    except Exception as e:
        print(f"[-] Lỗi kết nối: {e}")
    finally:
        try:
            client_socket.close()
        except Exception:
            pass
        print("[*] Đã đóng kết nối Client. Tạm biệt!")

if __name__ == "__main__":
    main()