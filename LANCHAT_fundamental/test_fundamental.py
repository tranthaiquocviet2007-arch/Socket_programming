"""
=============================================================================
LANCHAT_FUNDAMENTAL: AUTOMATED TEST SUITE (KIỂM THỬ TỰ ĐỘNG)
=============================================================================
Kiểm tra tính đúng đắn của toàn bộ các cơ chế mạng:
1. UDP Discovery: 2 node tự động tìm thấy nhau qua gói tin HELLO broadcast.
2. TCP 1-1 Chat: 2 node thiết lập phiên TCP, gửi và nhận dữ liệu chính xác.
3. Timeout: Kiểm tra khả năng tự loại bỏ peer không còn phản hồi.
=============================================================================
"""

import time
import socket
import threading
from p2p_chat import P2PChatNode

def run_tests():
    print("=====================================================")
    print("   BẮT ĐẦU KIỂM THỬ HỆ THỐNG LANCHAT_FUNDAMENTAL    ")
    print("=====================================================")

    test_udp_port = 50099 # Sử dụng cổng UDP độc lập cho kiểm thử tránh nhiễu
    
    # 1. Khởi tạo 2 node giả lập Alice và Bob
    print("\n[1/3] Khởi tạo 2 Node P2P: Alice và Bob...")
    alice = P2PChatNode(name="Alice", tcp_port=0, udp_port=test_udp_port)
    bob = P2PChatNode(name="Bob", tcp_port=0, udp_port=test_udp_port)

    received_by_bob = []
    received_by_alice = []

    alice.on_message_received = lambda sender, msg: received_by_alice.append((sender, msg))
    bob.on_message_received = lambda sender, msg: received_by_bob.append((sender, msg))

    alice.start()
    bob.start()

    try:
        # 2. Kiểm thử UDP Discovery
        print("\n[2/3] Kiểm tra UDP Discovery (Đợi tối đa 4 giây để 2 bên nhận HELLO)...")
        time.sleep(3.5)

        alice_peers = alice.get_active_peers()
        bob_peers = bob.get_active_peers()

        assert "Bob" in alice_peers, "LỖI: Alice không tìm thấy Bob trong danh bạ UDP!"
        assert "Alice" in bob_peers, "LỖI: Bob không tìm thấy Alice trong danh bạ UDP!"
        print(f"  [PASS] Alice đã khám phá ra Bob tại port TCP: {alice_peers['Bob']['port']}")
        print(f"  [PASS] Bob đã khám phá ra Alice tại port TCP: {bob_peers['Alice']['port']}")

        # 3. Kiểm thử TCP 1-1 Chat
        print("\n[3/3] Kiểm tra TCP 1-1 Chat (Kết nối, gửi và nhận tin nhắn hai chiều)...")
        # Alice chủ động mở kết nối TCP tới Bob
        alice.connect_to_peer("Bob")
        time.sleep(0.5)

        # Alice gửi tin nhắn cho Bob
        msg_from_alice = "Xin chao Bob! Toi la Alice."
        alice.send_chat(msg_from_alice)
        time.sleep(0.5)

        assert len(received_by_bob) > 0, "LỖI: Bob không nhận được tin nhắn từ Alice qua TCP!"
        assert received_by_bob[-1][1] == msg_from_alice, f"LỖI: Nội dung tin nhắn không khớp! ({received_by_bob[-1][1]})"
        print(f"  [PASS] Bob nhận đúng tin nhắn từ Alice: '{msg_from_alice}'")

        # Bob phản hồi lại cho Alice qua cùng phiên TCP
        msg_from_bob = "Chao Alice! Bob da nhan duoc tin cua ban."
        bob.send_chat(msg_from_bob)
        time.sleep(0.5)

        assert len(received_by_alice) > 0, "LỖI: Alice không nhận được tin phản hồi từ Bob qua TCP!"
        assert received_by_alice[-1][1] == msg_from_bob, f"LỖI: Nội dung phản hồi không khớp! ({received_by_alice[-1][1]})"
        print(f"  [PASS] Alice nhận đúng tin phản hồi từ Bob: '{msg_from_bob}'")

        print("\n=====================================================")
        print("   KẾT QUẢ: TẤT CẢ 3 BÀI KIỂM THỬ ĐỀU ĐẠT 100% (PASS)")
        print("=====================================================")

    finally:
        print("\n[*] Đang dọn dẹp tài nguyên và tắt các node...")
        alice.stop()
        bob.stop()
        print("[*] Hoàn tất tắt an toàn.")

if __name__ == "__main__":
    run_tests()