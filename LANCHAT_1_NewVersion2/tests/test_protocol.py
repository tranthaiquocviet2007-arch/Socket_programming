"""
Bộ Unit Test kiểm thử toàn diện giao thức truyền thông TCP/UDP:
- Kiểm thử đóng gói & phân tích HELLO, HI, MSG, FILE, BYE.
- Kiểm thử xử lý dính gói (TCP Concatenation): 'MSG|5|HelloMSG|5|World'.
- Kiểm thử xử lý vỡ gói (TCP Fragmentation): truyền từng byte một qua socket pair.
- Kiểm thử ký tự tiếng Việt UTF-8 đa byte (length_bytes khác length_chars).
- Kiểm thử recv_exact và xử lý đóng kết nối bất ngờ.
"""

import socket
import unittest
from src.protocol import (
    format_hello,
    parse_hello,
    format_hi,
    format_msg,
    format_file_header,
    format_ok,
    format_bye,
    recv_exact,
    recv_until,
    parse_tcp_frame,
)


class TestProtocol(unittest.TestCase):

    def test_udp_hello(self):
        """Kiểm thử định dạng bản tin UDP HELLO."""
        pkt = format_hello("Alice", 10001, "online")
        self.assertEqual(pkt, b"HELLO|Alice|10001|online")

        parsed = parse_hello(pkt)
        self.assertIsNotNone(parsed)
        name, port, status = parsed
        self.assertEqual(name, "Alice")
        self.assertEqual(port, 10001)
        self.assertEqual(status, "online")

    def test_udp_hello_invalid(self):
        """Kiểm thử bản tin UDP không hợp lệ."""
        self.assertIsNone(parse_hello(b"INVALID|DATA"))
        self.assertIsNone(parse_hello(b""))
        self.assertIsNone(parse_hello(b"HELLO|Bob|not_a_number|online"))

    def test_tcp_hi(self):
        """Kiểm thử bản tin TCP Handshake HI."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(format_hi("Bob", 10002, "CHAT"))
            tag, data = parse_tcp_frame(s2)
            self.assertEqual(tag, "HI")
            name, port, purpose = data
            self.assertEqual(name, "Bob")
            self.assertEqual(port, 10002)
            self.assertEqual(purpose, "CHAT")
        finally:
            s1.close()
            s2.close()

    def test_tcp_bye(self):
        """Kiểm thử bản tin TCP BYE."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(format_bye())
            tag, data = parse_tcp_frame(s2)
            self.assertEqual(tag, "BYE")
            self.assertIsNone(data)
        finally:
            s1.close()
            s2.close()

    def test_tcp_msg_vietnamese(self):
        """
        Kiểm thử tin nhắn chứa tiếng Việt UTF-8 đa byte:
        Ký tự tiếng Việt có dấu chiếm 2-3 bytes mỗi ký tự.
        Đảm bảo parser tính đúng byte length và không bị cắt cụt ký tự.
        """
        vietnamese_text = "Xin chào các bạn! Đồ án Lập trình Mạng Socket P2P 🇻🇳"
        encoded_len = len(vietnamese_text.encode("utf-8"))
        char_len = len(vietnamese_text)

        # Khẳng định độ dài byte lớn hơn độ dài ký tự
        self.assertGreater(encoded_len, char_len)

        s1, s2 = socket.socketpair()
        try:
            s1.sendall(format_msg(vietnamese_text))
            tag, text = parse_tcp_frame(s2)
            self.assertEqual(tag, "MSG")
            self.assertEqual(text, vietnamese_text)
        finally:
            s1.close()
            s2.close()

    def test_tcp_file_header(self):
        """Kiểm thử header thông báo gửi file TCP."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(format_file_header("tai_lieu.pdf", 1048576))
            tag, data = parse_tcp_frame(s2)
            self.assertEqual(tag, "FILE")
            filename, filesize = data
            self.assertEqual(filename, "tai_lieu.pdf")
            self.assertEqual(filesize, 1048576)
        finally:
            s1.close()
            s2.close()

    def test_tcp_file_ack(self):
        """Kiểm thử frame ACK xác nhận nhận đủ file: OK|<filesize>|."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(format_ok(1048576))
            tag, data = parse_tcp_frame(s2)
            self.assertEqual(tag, "OK")
            self.assertEqual(data, 1048576)
        finally:
            s1.close()
            s2.close()

    def test_tcp_concatenation_handling(self):
        """
        Kiểm thử chống dính gói (Concatenation):
        Hai gói tin MSG được gửi liền nhau trong một lần ghi socket.
        Bộ parser phải phân tách chính xác thành 2 frame riêng biệt.
        """
        raw = format_msg("Hello") + format_msg("World")
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(raw)

            tag1, text1 = parse_tcp_frame(s2)
            self.assertEqual(tag1, "MSG")
            self.assertEqual(text1, "Hello")

            tag2, text2 = parse_tcp_frame(s2)
            self.assertEqual(tag2, "MSG")
            self.assertEqual(text2, "World")
        finally:
            s1.close()
            s2.close()

    def test_tcp_fragmentation_handling(self):
        """
        Kiểm thử chống vỡ gói (Fragmentation):
        Gửi từng byte một với độ trễ để mô phỏng mạng bị phân mảnh.
        """
        msg = "Dữ liệu phân mảnh qua mạng TCP"
        raw = format_msg(msg)

        s1, s2 = socket.socketpair()
        try:
            # Gửi từng byte một
            for b in raw:
                s1.sendall(bytes([b]))

            tag, text = parse_tcp_frame(s2)
            self.assertEqual(tag, "MSG")
            self.assertEqual(text, msg)
        finally:
            s1.close()
            s2.close()

    def test_recv_exact_eof(self):
        """Kiểm thử recv_exact khi socket bị đóng giữa chừng."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(b"123")
            s1.close()  # Đóng kết nối khi đối phương yêu cầu đọc 5 bytes
            data = recv_exact(s2, 5)
            self.assertEqual(data, b"")
        finally:
            s2.close()


if __name__ == "__main__":
    unittest.main()
