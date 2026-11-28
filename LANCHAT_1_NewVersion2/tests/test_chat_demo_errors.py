"""Các tình huống lỗi TCP cần cho demo: timeout, EOF và gói đầu sai."""

import socket
import threading
import unittest
from unittest import mock

from src.chat_manager import ChatManager
from src.protocol import format_hi, format_msg, parse_tcp_frame


class _Peers:
    def get_peer(self, name):
        return {"ip": "127.0.0.1", "tcp_port": 10001}


class TestChatDemoErrors(unittest.TestCase):
    def make_manager(self):
        notices = []
        manager = ChatManager("Quan", 0, _Peers(), lambda *args: None, notices.append)
        manager._running = True
        return manager, notices

    def test_chat_connect_timeout_reports_error_and_returns(self):
        manager, notices = self.make_manager()
        fake_socket = mock.Mock()
        fake_socket.connect.side_effect = socket.timeout("timed out")
        with mock.patch("src.chat_manager.socket.socket", return_value=fake_socket):
            self.assertIsNone(manager.get_or_create_connection("Minh"))
        fake_socket.settimeout.assert_called()
        fake_socket.close.assert_called_once()
        self.assertTrue(any("Minh" in msg for msg in notices))

    def test_chat_handshake_timeout_reports_error_and_returns(self):
        manager, notices = self.make_manager()
        manager._server_sock = mock.Mock()
        manager._server_sock.getsockname.return_value = ("127.0.0.1", 10000)
        fake_socket = mock.Mock()
        fake_socket.recv.side_effect = socket.timeout("timed out")
        with mock.patch("src.chat_manager.socket.socket", return_value=fake_socket):
            self.assertIsNone(manager.get_or_create_connection("Minh"))
        fake_socket.settimeout.assert_called()
        fake_socket.close.assert_called_once()
        self.assertTrue(any("Minh" in msg for msg in notices))

    def test_peer_closing_socket_returns_to_idle_prompt(self):
        manager, notices = self.make_manager()
        peer, local = socket.socketpair()
        try:
            manager.active_partner = "Minh"
            manager.connections["Minh"] = local
            peer.close()  # Crash: không gửi BYE
            manager._receive_loop(local, "Minh")
            self.assertIsNone(manager.active_partner)
            self.assertNotIn("Minh", manager.connections)
            self.assertTrue(any("ngắt kết nối" in msg for msg in notices))
        finally:
            peer.close()
            local.close()

    def test_partial_first_frame_times_out_and_closes_only_that_connection(self):
        manager, _ = self.make_manager()
        peer, local = socket.socketpair()
        try:
            peer.settimeout(0.2)
            with mock.patch("src.chat_manager.CHAT_HANDSHAKE_TIMEOUT", 0.05):
                thread = threading.Thread(
                    target=manager._handle_new_connection,
                    args=(local, ("127.0.0.1", 12345)),
                    daemon=True,
                )
                thread.start()
                peer.sendall(b"abc")  # Không có dấu |; nc vẫn giữ socket mở
                thread.join(timeout=1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(peer.recv(1), b"")
            self.assertTrue(manager._running)
        finally:
            peer.close()
            local.close()

    def test_valid_chat_can_stay_idle_longer_than_handshake_timeout(self):
        manager, _ = self.make_manager()
        manager._server_sock = mock.Mock()
        manager._server_sock.getsockname.return_value = ("127.0.0.1", 10000)
        messages = []
        manager.on_message_received = lambda name, text, active: messages.append(text)
        peer, local = socket.socketpair()
        try:
            with mock.patch("src.chat_manager.CHAT_HANDSHAKE_TIMEOUT", 0.05):
                thread = threading.Thread(
                    target=manager._handle_new_connection,
                    args=(local, ("127.0.0.1", 12345)),
                    daemon=True,
                )
                thread.start()
                peer.sendall(format_hi("Minh", 10001))
                self.assertEqual(parse_tcp_frame(peer)[0], "HI")
                # Đợi thread chờ recv() đủ lâu để timeout handshake đã hết.
                peer.settimeout(1)
                threading.Event().wait(0.1)
                peer.sendall(format_msg("Vẫn còn ở đây"))
                peer.shutdown(socket.SHUT_WR)
                thread.join(timeout=1)
            self.assertEqual(messages, ["Vẫn còn ở đây"])
        finally:
            peer.close()
            local.close()


if __name__ == "__main__":
    unittest.main()
