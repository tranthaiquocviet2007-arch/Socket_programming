#!/usr/bin/env python3
"""
Kịch bản kiểm thử tích hợp tự động (End-to-End Simulation):
Khởi tạo 2 Peer (Alice và Bob), trao đổi UDP Discovery, kết nối TCP Chat,
gửi tin nhắn tiếng Việt, gửi file nhị phân và kiểm tra tính toàn vẹn 100%.
"""

import os
import time
from src.config import DOWNLOAD_DIR
from src.peer_manager import PeerManager
from src.chat_manager import ChatManager
from src.file_transfer import FileTransferManager


def run_e2e_simulation():
    print("\n" + "=" * 65)
    print(" BẮT ĐẦU KIỂM THỬ GIẢ LẬP TÍCH HỢP 2 PEER (ALICE & BOB)")
    print("=" * 65)

    test_udp_port = 19999
    bcast_ip = "127.255.255.255"

    alice_received_msgs = []
    bob_received_msgs = []

    # 1. Khởi tạo Peer 1: Alice
    print("[1] Khởi tạo Node Alice...")
    chat_alice = ChatManager(
        name="Alice",
        tcp_port=0,
        peer_manager=None,
        on_message_received=lambda sender, msg, active: alice_received_msgs.append((sender, msg)),
        on_system_notify=lambda msg: None,
    )
    alice_tcp_port = chat_alice.start()

    peer_alice = PeerManager(
        name="Alice",
        tcp_port=alice_tcp_port,
        udp_port=test_udp_port,
        bcast_ip=bcast_ip,
    )
    chat_alice.peer_manager = peer_alice

    ft_alice = FileTransferManager("Alice", alice_tcp_port, peer_alice, lambda msg: None)
    chat_alice.file_transfer_handler = ft_alice.handle_incoming_file

    peer_alice.start()

    # 2. Khởi tạo Peer 2: Bob
    print("[2] Khởi tạo Node Bob...")
    chat_bob = ChatManager(
        name="Bob",
        tcp_port=0,
        peer_manager=None,
        on_message_received=lambda sender, msg, active: bob_received_msgs.append((sender, msg)),
        on_system_notify=lambda msg: None,
    )
    bob_tcp_port = chat_bob.start()

    peer_bob = PeerManager(
        name="Bob",
        tcp_port=bob_tcp_port,
        udp_port=test_udp_port,
        bcast_ip=bcast_ip,
    )
    chat_bob.peer_manager = peer_bob

    ft_bob = FileTransferManager("Bob", bob_tcp_port, peer_bob, lambda msg: None)
    chat_bob.file_transfer_handler = ft_bob.handle_incoming_file

    peer_bob.start()

    # 3. Chờ UDP Discovery tìm thấy nhau
    print("[3] Chờ UDP Discovery nhận diện peers (khoảng 3 giây)...")
    for _ in range(40):
        if peer_alice.get_peer("Bob") and peer_bob.get_peer("Alice"):
            break
        time.sleep(0.1)

    assert peer_alice.get_peer("Bob") is not None, "Alice không tìm thấy Bob qua UDP Discovery!"
    assert peer_bob.get_peer("Alice") is not None, "Bob không tìm thấy Alice qua UDP Discovery!"
    print("    -> UDP Discovery thành công: Alice và Bob đã thấy nhau!")

    # 4. Kiểm thử TCP Chat 2 chiều
    print("[4] Kiểm thử kết nối TCP Chat và trao đổi tin nhắn...")
    chat_alice.switch_partner("Bob")
    chat_bob.switch_partner("Alice")

    # Alice gửi tin nhắn cho Bob
    chat_alice.send_chat("Chào Bob! Đồ án Mạng máy tính chạy tốt chứ?")
    # Bob gửi phản hồi cho Alice
    chat_bob.send_chat("Chào Alice! Mọi thứ chạy rất mượt mà 🇻🇳")

    time.sleep(0.5)

    assert any("Chào Bob" in msg for sender, msg in bob_received_msgs), "Bob không nhận được tin nhắn từ Alice!"
    assert any("Chào Alice" in msg for sender, msg in alice_received_msgs), "Alice không nhận được phản hồi từ Bob!"
    print("    -> TCP Chat thành công: Tin nhắn tiếng Việt trao đổi hoàn hảo!")

    # 5. Kiểm thử Truyền nhận File
    print("[5] Kiểm thử truyền nhận file nhị phân qua luồng nền TCP riêng biệt...")
    test_file = "test_payload.bin"
    test_data = b"HELLOP2P_SOCKET_NETWORKING_" * 2048  # File mẫu kích thước ~53 KB
    with open(test_file, "wb") as f:
        f.write(test_data)

    ft_alice.send_file_async("Bob", test_file)

    time.sleep(1.0)

    received_file = os.path.join(DOWNLOAD_DIR, test_file)
    assert os.path.exists(received_file), f"File không tồn tại ở thư mục đích: {received_file}"
    with open(received_file, "rb") as f:
        content = f.read()
    assert content == test_data, "Nội dung file nhận được không khớp byte-for-byte với file gốc!"
    print("    -> File Transfer thành công: Dữ liệu toàn vẹn 100%!")

    # Dọn dẹp dữ liệu test (chỉ xóa file test, không xóa cả thư mục downloads của người dùng)
    if os.path.exists(test_file):
        os.remove(test_file)
    if os.path.exists(received_file):
        os.remove(received_file)

    # Dừng các node
    print("[6] Dọn dẹp và đóng sạch các Socket...")
    peer_alice.stop()
    peer_bob.stop()
    chat_alice.stop()
    chat_bob.stop()

    print("\n" + "=" * 65)
    print(" [✓] TẤT CẢ CÁC BƯỚC KIỂM THỬ GIẢ LẬP ĐỀU VƯỢT QUA 100%!")
    print("=" * 65)


if __name__ == "__main__":
    run_e2e_simulation()
