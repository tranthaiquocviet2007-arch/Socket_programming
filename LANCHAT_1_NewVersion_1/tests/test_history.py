"""
Unit test cho kho lịch sử chat cục bộ (src/history.py):
- Chỉ khởi tạo file/thư mục khi chưa tồn tại, không ghi đè dữ liệu cũ.
- Ghi tin đã gửi/đã nhận, đọc lại được sau khi tạo instance mới.
- Gộp và sắp xếp hội thoại theo thời gian, lọc đúng theo peer.
- File JSON hỏng được sao lưu thay vì xóa mất dữ liệu.
"""

import json
import os
import tempfile
import time
import unittest

from src.history import ChatHistory


class TestChatHistory(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = self._tmp.name
        self.downloads = os.path.join(base, "downloads")
        self.sent_file = os.path.join(base, "sent_messages.json")
        self.received_file = os.path.join(base, "received_messages.json")
        self.history = ChatHistory(self.downloads, self.sent_file, self.received_file)

    def tearDown(self):
        self._tmp.cleanup()

    def _read_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_initializes_only_when_missing(self):
        """Tạo downloads/ và 2 file JSON rỗng khi chưa có."""
        self.assertTrue(os.path.isdir(self.downloads))
        self.assertEqual(self._read_json(self.sent_file), [])
        self.assertEqual(self._read_json(self.received_file), [])

    def test_does_not_overwrite_existing_files(self):
        """Khởi tạo lại không được ghi đè dữ liệu đã có."""
        old_records = [{"peer": "Bob", "type": "text", "text": "tin cũ", "ts": 1.0}]
        with open(self.sent_file, "w", encoding="utf-8") as f:
            json.dump(old_records, f, ensure_ascii=False)

        ChatHistory(self.downloads, self.sent_file, self.received_file)

        self.assertEqual(self._read_json(self.sent_file), old_records)

    def test_log_and_reload_from_disk(self):
        """Tin đã gửi/nhận được lưu xuống đĩa và đọc lại bởi instance mới."""
        self.history.log_text("Bob", "sent", "Chào Bob")
        self.history.log_text("Bob", "received", "Chào cậu")

        conversation = self.history.get_conversation("Bob")
        self.assertEqual([r["text"] for r in conversation], ["Chào Bob", "Chào cậu"])
        self.assertEqual([r["direction"] for r in conversation], ["sent", "received"])

        reloaded = ChatHistory(self.downloads, self.sent_file, self.received_file)
        again = reloaded.get_conversation("Bob")
        self.assertEqual([r["text"] for r in again], ["Chào Bob", "Chào cậu"])

    def test_conversation_sorted_and_filtered_by_peer(self):
        """Chỉ lấy đúng peer và sắp xếp theo timestamp."""
        self.history.log_text("Bob", "sent", "m1")
        time.sleep(0.002)
        self.history.log_text("Bob", "received", "r1")
        time.sleep(0.002)
        self.history.log_text("Bob", "sent", "m2")
        self.history.log_text("Alice", "sent", "tin của Alice")

        bob = self.history.get_conversation("Bob")
        self.assertEqual([r["text"] for r in bob], ["m1", "r1", "m2"])

        alice = self.history.get_conversation("Alice")
        self.assertEqual([r["text"] for r in alice], ["tin của Alice"])

    def test_log_file_records(self):
        """Sự kiện file được lưu kèm tên, kích thước và đường dẫn."""
        self.history.log_file("Bob", "received", "a.pdf", 1234, "/tmp/downloads/a.pdf")
        self.history.log_file("Bob", "sent", "b.txt", 99, "/tmp/b.txt")

        conversation = self.history.get_conversation("Bob")
        self.assertEqual(len(conversation), 2)
        self.assertEqual(conversation[0]["type"], "file")
        self.assertEqual(conversation[0]["name"], "a.pdf")
        self.assertEqual(conversation[0]["size"], 1234)
        self.assertEqual(conversation[0]["path"], "/tmp/downloads/a.pdf")
        self.assertEqual(conversation[1]["name"], "b.txt")

    def test_corrupt_json_is_backed_up(self):
        """File JSON hỏng không bị xóa mất; được đổi tên .broken-* trước khi ghi mới."""
        with open(self.sent_file, "w", encoding="utf-8") as f:
            f.write("{day khong phai json hop le")

        history = ChatHistory(self.downloads, self.sent_file, self.received_file)
        self.assertEqual(history.get_conversation("Bob"), [])

        history.log_text("Bob", "sent", "tin mới")

        base_dir = os.path.dirname(self.sent_file)
        backups = [
            name for name in os.listdir(base_dir)
            if name.startswith("sent_messages.json.broken-")
        ]
        self.assertEqual(len(backups), 1)
        self.assertEqual(self._read_json(self.sent_file)[0]["text"], "tin mới")


if __name__ == "__main__":
    unittest.main()
