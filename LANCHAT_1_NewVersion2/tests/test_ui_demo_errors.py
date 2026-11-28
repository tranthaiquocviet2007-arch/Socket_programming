"""Lệnh sai và file không có phải cho phản hồi rõ trong demo."""

import unittest

from src.ui import TerminalUI


class TestUIDemoErrors(unittest.TestCase):
    def setUp(self):
        self.ui = TerminalUI("Quan")
        self.messages = []
        self.ui.print_message = self.messages.append

    def test_unknown_command_only_suggests_help(self):
        self.ui._handle_user_input("/chta Minh")
        self.assertEqual(
            self.messages,
            ["[!] Lệnh không xác định: '/chta'. Gõ /help để xem các lệnh hỗ trợ."],
        )

    def test_missing_file_is_reported_even_without_active_chat(self):
        self.ui.chat_manager = type("ChatStub", (), {"active_partner": None})()
        self.ui._handle_user_input("/send khongco.pdf")
        self.assertTrue(any("khongco.pdf" in msg and "không tồn tại" in msg for msg in self.messages))


if __name__ == "__main__":
    unittest.main()
