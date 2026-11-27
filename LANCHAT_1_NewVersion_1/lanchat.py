#!/usr/bin/env python3
"""
Entry point chính khởi chạy ứng dụng P2P LAN Chat & File Sharing.
Chấp nhận các tham số dòng lệnh tùy chỉnh cấu hình mạng.
"""

import argparse
import getpass
import os
import signal
import sys

from src.config import DEFAULT_UDP_PORT, DEFAULT_TCP_PORT, DEFAULT_BCAST_IP
from src.peer_manager import PeerManager
from src.chat_manager import ChatManager
from src.file_transfer import FileTransferManager
from src.history import ChatHistory
from src.ui import TerminalUI


def parse_arguments():
    """Thiết lập và phân tích tham số dòng lệnh."""
    parser = argparse.ArgumentParser(
        description="Ứng dụng P2P LAN Chat & File Sharing qua Python Socket Programming."
    )
    default_name = getpass.getuser() or f"User_{os.getpid()}"

    parser.add_argument(
        "--name",
        type=str,
        default=default_name,
        help=f"Tên định danh hiển thị của bạn trong mạng LAN (mặc định: {default_name})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help="Port TCP dùng để nhận chat/file (mặc định 0 để OS tự cấp phát port ngẫu nhiên khả dụng)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=DEFAULT_UDP_PORT,
        help=f"Port UDP phát và nhận bản tin Discovery (mặc định: {DEFAULT_UDP_PORT})",
    )
    parser.add_argument(
        "--bcast",
        type=str,
        default=DEFAULT_BCAST_IP,
        help=f"Địa chỉ IP Broadcast (mặc định: {DEFAULT_BCAST_IP}. Nhập 127.255.255.255 nếu test loopback)",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    print(f"\n=======================================================")
    print(f"  KHỞI ĐỘNG P2P LAN CHAT - NODE: [{args.name}]")
    print(f"=======================================================")

    # 1. Khởi tạo Giao diện người dùng Terminal UI
    ui = TerminalUI(name=args.name)

    # 2. Khởi tạo kho lịch sử cục bộ (tạo file/thư mục nếu chưa tồn tại)
    history_store = ChatHistory()
    print(f"[*] Tin nhắn đã gửi lưu tại : {history_store.sent_file}")
    print(f"[*] Tin nhắn đã nhận lưu tại: {history_store.received_file}")
    print(f"[*] File nhận được lưu tại  : {history_store.downloads_dir}")

    # 3. Khởi tạo Chat Manager và bind TCP Port
    # Dùng placeholder cho file_transfer_handler và peer_manager, sẽ cập nhật ngay sau đây
    chat_mgr = ChatManager(
        name=args.name,
        tcp_port=args.port,
        peer_manager=None,
        on_message_received=ui.on_message_received,
        on_system_notify=ui.on_system_notify,
        file_transfer_handler=None,
        history_store=history_store,
    )
    actual_tcp_port = chat_mgr.start()
    print(f"[*] TCP Chat Server đang lắng nghe tại port: {actual_tcp_port}")

    # 4. Khởi tạo Peer Manager (Discovery UDP)
    peer_mgr = PeerManager(
        name=args.name,
        tcp_port=actual_tcp_port,
        udp_port=args.udp_port,
        bcast_ip=args.bcast,
        on_peer_change=ui.on_peer_change,
    )
    chat_mgr.peer_manager = peer_mgr

    # 5. Khởi tạo File Transfer Manager
    file_mgr = FileTransferManager(
        my_name=args.name,
        my_tcp_port=actual_tcp_port,
        peer_manager=peer_mgr,
        notify_func=ui.on_system_notify,
        history_store=history_store,
    )
    chat_mgr.file_transfer_handler = file_mgr.handle_incoming_file

    # 6. Liên kết UI với các Manager
    ui.bind_controllers(peer_mgr, chat_mgr, file_mgr, history_store=history_store)

    # 7. Khởi động khám phá Peer qua UDP Broadcast
    peer_mgr.start()
    print(f"[*] UDP Discovery đang phát và lắng nghe tại port: {args.udp_port} (Bcast: {args.bcast})")

    # 8. Đăng ký tín hiệu tắt sạch sẽ (SIGINT)
    def signal_handler(sig, frame):
        ui.print_message("\nĐang dọn dẹp và thoát...")
        peer_mgr.stop()
        chat_mgr.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 9. Bắt đầu vòng lặp tương tác giao diện người dùng
    try:
        ui.run()
    finally:
        peer_mgr.stop()
        chat_mgr.stop()
        print("[✓] Đã đóng mọi socket an toàn. Tạm biệt!")


if __name__ == "__main__":
    main()
