"""
Cấu hình hằng số toàn cục cho hệ thống P2P LAN Chat.
"""
import os

# Cấu hình mạng mặc định
DEFAULT_UDP_PORT = 9999            # Port UDP lắng nghe bản tin Broadcast Discovery
DEFAULT_TCP_PORT = 0               # Port TCP chat/file (0 để OS tự cấp phát port ngẫu nhiên khả dụng)
DEFAULT_BCAST_IP = "255.255.255.255"  # Địa chỉ IP Broadcast toàn mạng LAN (dùng 127.255.255.255 nếu test loopback)

# Thời gian và chu kỳ (giây)
BROADCAST_INTERVAL = 3             # Chu kỳ phát gói tin HELLO (3 giây)
PEER_TIMEOUT = 10                  # Thời gian không nhận heartbeat để đánh dấu offline (10 giây)

# Kích thước bộ đệm và chunk
DEFAULT_BUFFER_SIZE = 4096         # Bộ đệm nhận dữ liệu cơ bản (4 KB)
FILE_CHUNK_SIZE = 65536            # Kích thước mỗi khối khi gửi/nhận file (64 KB)

# Thư mục lưu trữ
# Neo theo thư mục hiện tại lúc chạy lệnh: chạy script ở đâu thì dữ liệu tạo ở đó.
DATA_ROOT = os.getcwd()
DOWNLOAD_DIR = os.path.join(DATA_ROOT, "downloads")                     # File nhận được
SENT_MESSAGES_FILE = os.path.join(DATA_ROOT, "sent_messages.json")      # Tin nhắn/file đã gửi
RECEIVED_MESSAGES_FILE = os.path.join(DATA_ROOT, "received_messages.json")  # Tin nhắn/file đã nhận

# Bảng mã
ENCODING = "utf-8"

# Trạng thái người dùng
STATUS_ONLINE = "online"
STATUS_AWAY = "away"
VALID_STATUSES = {STATUS_ONLINE, STATUS_AWAY}
