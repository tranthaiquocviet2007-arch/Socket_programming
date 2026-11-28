"""
Unit test cho phần nhận file (src/file_transfer.py):
- File nhận được lưu vào downloads/<tên_peer>/ (mỗi peer một thư mục).
- Hai peer cùng gửi một tên file vẫn tách biệt.
- Trùng tên trong cùng một peer được thêm hậu tố _1, _2... và lịch sử ghi đúng tên thật.
- Tên peer/file do mạng gửi tới không thể thoát khỏi thư mục downloads/.
- Cấp phát tên file kiểu atomic (O_CREAT|O_EXCL) không trả trùng đường dẫn.
"""

import os
import socket
import tempfile
import threading
import unittest
from unittest import mock

from src.file_transfer import (
    FileTransferManager,
    _reserve_unique_filepath,
    _safe_filename,
    _sanitize_peer_component,
)
from src.protocol import parse_tcp_frame


class _StubHistory:
    """Kho lịch sử giả: chỉ cần downloads_dir và log_file để kiểm thử."""

    def __init__(self, downloads_dir):
        self.downloads_dir = downloads_dir
        self.records = []

    def log_file(self, *args):
        self.records.append(args)


class TestFileTransfer(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.downloads = self._tmp.name
        self.history = _StubHistory(self.downloads)
        self.manager = FileTransferManager(
            "Me",
            0,
            peer_manager=None,
            notify_func=lambda msg: None,
            history_store=self.history,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _receive(self, sender_name, filename, payload):
        """Gửi payload qua socketpair rồi chạy worker nhận file đồng bộ."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(payload)
            self.manager._receive_file_worker(s2, sender_name, filename, len(payload))
        finally:
            s1.close()

    def test_received_file_goes_to_peer_subdir(self):
        payload = b"hello peer folder"
        self._receive("Alice", "note.txt", payload)

        path = os.path.join(self.downloads, "Alice", "note.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as f:
            self.assertEqual(f.read(), payload)

        sender, direction, name, size, logged_path = self.history.records[-1]
        self.assertEqual(sender, "Alice")
        self.assertEqual(direction, "received")
        self.assertEqual(name, "note.txt")
        self.assertEqual(size, len(payload))
        self.assertEqual(logged_path, os.path.abspath(path))

    def test_same_filename_from_different_peers_stays_separate(self):
        self._receive("Alice", "same.txt", b"A")
        self._receive("Bob", "same.txt", b"B")

        with open(os.path.join(self.downloads, "Alice", "same.txt"), "rb") as f:
            self.assertEqual(f.read(), b"A")
        with open(os.path.join(self.downloads, "Bob", "same.txt"), "rb") as f:
            self.assertEqual(f.read(), b"B")

    def test_collision_within_same_peer_gets_suffix_and_logs_real_name(self):
        self._receive("Alice", "same.txt", b"1")
        self._receive("Alice", "same.txt", b"2")

        self.assertTrue(os.path.isfile(os.path.join(self.downloads, "Alice", "same.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.downloads, "Alice", "same_1.txt")))
        # Lịch sử phải ghi tên thật trên đĩa, không phải tên gốc bị trùng
        self.assertEqual(self.history.records[-1][2], "same_1.txt")

    def test_peer_name_cannot_escape_download_dir(self):
        self._receive("../../etc", "passwd", b"x")

        safe_dir = _sanitize_peer_component("../../etc")
        self.assertTrue(os.path.isfile(os.path.join(self.downloads, safe_dir, "passwd")))
        self.assertFalse(os.path.exists(os.path.join(self.downloads, "..", "etc", "passwd")))

    def test_failed_transfer_leaves_no_files(self):
        """Đứt kết nối giữa chừng: không còn .part, cũng không có file đích rỗng."""
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(b"12345")
            s1.close()  # Đóng trước khi gửi đủ 10 bytes
            self.manager._receive_file_worker(s2, "Alice", "x.bin", 10)
        finally:
            if s1.fileno() != -1:
                s1.close()

        peer_dir = os.path.join(self.downloads, "Alice")
        self.assertTrue(os.path.isdir(peer_dir))
        self.assertEqual(os.listdir(peer_dir), [])

    def test_receiver_sends_ack_after_saving(self):
        """Receiver phải gửi OK|<size>| sau khi file đã nằm trên đĩa."""
        payload = b"ack me"
        s1, s2 = socket.socketpair()
        try:
            s1.sendall(payload)
            self.manager._receive_file_worker(s2, "Alice", "a.bin", len(payload))
            tag, size = parse_tcp_frame(s1)
            self.assertEqual(tag, "OK")
            self.assertEqual(size, len(payload))
        finally:
            s1.close()

    def test_sender_does_not_report_success_without_ack(self):
        """Receiver nhận đủ dữ liệu nhưng không ACK → sender phải báo lỗi, không báo thành công."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def fake_receiver():
            conn, _ = server.accept()
            try:
                parse_tcp_frame(conn)              # HI
                tag, (name, size) = parse_tcp_frame(conn)  # FILE
                remaining = size
                while remaining > 0:
                    chunk = conn.recv(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                # Cố tình KHÔNG gửi ACK rồi đóng
            finally:
                conn.close()
                server.close()

        worker = threading.Thread(target=fake_receiver, daemon=True)
        worker.start()

        class _PeerManager:
            def get_peer(self, name):
                return {"ip": "127.0.0.1", "tcp_port": port}

        messages = []
        manager = FileTransferManager("Me", 0, _PeerManager(), messages.append)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"payload")
            file_path = f.name

        try:
            with mock.patch("src.file_transfer.FILE_IO_TIMEOUT", 0.2):
                manager._send_file_worker("Peer", file_path)
            worker.join(timeout=2)
            self.assertTrue(any("Lỗi gửi file" in m for m in messages), messages)
            self.assertFalse(any("thành công" in m for m in messages), messages)
        finally:
            os.remove(file_path)

    def test_reserve_unique_filepath_is_atomic(self):
        peer_dir = os.path.join(self.downloads, "x")
        os.makedirs(peer_dir)

        first = _reserve_unique_filepath(peer_dir, "a.txt")
        second = _reserve_unique_filepath(peer_dir, "a.txt")

        self.assertNotEqual(first, second)
        self.assertEqual(os.path.basename(first), "a.txt")
        self.assertEqual(os.path.basename(second), "a_1.txt")

    def test_sanitizers(self):
        self.assertEqual(_safe_filename("..\\..\\evil.txt"), "evil.txt")
        self.assertEqual(_safe_filename("/etc/passwd"), "passwd")
        self.assertEqual(_safe_filename(""), "unnamed_file")

        for bad in ["../../etc", ".", "..", "", "a/b", "a\\b"]:
            component = _sanitize_peer_component(bad)
            self.assertNotIn("/", component)
            self.assertNotIn("\\", component)
            self.assertNotIn(component, ("", ".", ".."))


if __name__ == "__main__":
    unittest.main()
