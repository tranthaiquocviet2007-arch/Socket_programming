"""
Định nghĩa giao thức truyền thông, cấu trúc frame và các hàm parser TCP/UDP.

Định dạng frame:
- UDP Discovery: HELLO|<name>|<tcp_port>|<status>
- TCP Handshake: HI|<name>|<tcp_port>|
- TCP Chat Message: MSG|<length_bytes>|<utf-8 text>
- TCP File Header: FILE|<filename>|<filesize>|
- TCP File ACK: OK|<filesize>|
- TCP Bye: BYE|

Các hàm helper giải quyết triệt để vấn đề phân mảnh (fragmentation), dính gói
(concatenation) và hỗ trợ ký tự UTF-8 tiếng Việt đa byte an toàn.
"""

import socket
from typing import Optional, Tuple
from src.config import ENCODING


# ==================== ĐÓNG GÓI GIAO THỨC (FORMATTERS) ====================

def format_hello(name: str, tcp_port: int, status: str = "online") -> bytes:
    """Đóng gói bản tin UDP Discovery: HELLO|<name>|<tcp_port>|<status>"""
    return f"HELLO|{name}|{tcp_port}|{status}".encode(ENCODING)


def format_hi(name: str, tcp_port: int, purpose: str = "CHAT") -> bytes:
    """
    Đóng gói bản tin TCP Handshake: HI|<name>|<tcp_port>|[purpose]|
    purpose có thể là CHAT hoặc FILE.
    """
    return f"HI|{name}|{tcp_port}|{purpose}|".encode(ENCODING)


def format_msg(text: str) -> bytes:
    """
    Đóng gói bản tin TCP Chat Message: MSG|<length_bytes>|<utf-8 text>
    LƯU Ý: length_bytes là độ dài chuỗi byte UTF-8 thực tế, không phải số ký tự (hỗ trợ tiếng Việt).
    """
    payload = text.encode(ENCODING)
    header = f"MSG|{len(payload)}|".encode(ENCODING)
    return header + payload


def format_file_header(filename: str, filesize: int) -> bytes:
    """Đóng gói header thông báo gửi file TCP: FILE|<filename>|<filesize>|"""
    return f"FILE|{filename}|{filesize}|".encode(ENCODING)


def format_bye() -> bytes:
    """Đóng gói bản tin ngắt kết nối TCP: BYE|"""
    return b"BYE|"


def format_ok(filesize: int) -> bytes:
    """Đóng gói xác nhận đã nhận đủ file: OK|<filesize>|"""
    return f"OK|{filesize}|".encode(ENCODING)


# ==================== PHÂN TÍCH GIAO THỨC UDP ====================

def parse_hello(data: bytes) -> Optional[Tuple[str, int, str]]:
    """
    Phân tích gói tin UDP HELLO.
    Trả về: (name, tcp_port, status) hoặc None nếu dữ liệu không hợp lệ.
    """
    try:
        text = data.decode(ENCODING).strip()
        parts = text.split("|")
        if len(parts) >= 4 and parts[0] == "HELLO":
            name = parts[1].strip()
            tcp_port = int(parts[2].strip())
            status = parts[3].strip()
            return name, tcp_port, status
    except Exception:
        pass
    return None


# ==================== PARSER TCP CHỐNG DÍNH GÓI & VỠ GÓI ====================

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """
    Đọc chính xác n bytes từ TCP socket stream.
    Nếu đối phương đóng socket trước khi nhận đủ n bytes, trả về b'' (báo hiệu ngắt kết nối).
    Giải quyết triệt để vấn đề vỡ gói (fragmentation) của TCP.
    """
    if n <= 0:
        return b""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return b""  # Kết nối đã đóng
        buf.extend(chunk)
    return bytes(buf)


def recv_until(sock: socket.socket, delimiter: bytes = b"|", max_len: int = 4096) -> bytes:
    """
    Đọc từng byte từ TCP stream cho tới khi gặp delimiter (mặc định là '|').
    Trả về dữ liệu trước delimiter (đã cắt delimiter).
    Nếu socket đóng mà chưa có dữ liệu, trả về b''.
    Cơ chế đọc byte-by-byte trên header đảm bảo không đọc lẹm vào payload nhị phân hoặc chuỗi UTF-8 theo sau.
    """
    buf = bytearray()
    delim_len = len(delimiter)
    while True:
        b = sock.recv(1)
        if not b:
            return bytes(buf) if buf else b""
        buf.extend(b)
        if buf.endswith(delimiter):
            return bytes(buf[:-delim_len])
        if len(buf) >= max_len:
            raise ValueError(f"Header field vượt quá giới hạn tối đa {max_len} bytes")


def parse_tcp_frame(sock: socket.socket) -> Tuple[Optional[str], Optional[any]]:
    """
    Đọc và trích xuất một frame TCP hoàn chỉnh từ socket stream.

    Trả về:
    - ("HI", (name, tcp_port, purpose))
    - ("MSG", text_content)
    - ("FILE", (filename, filesize))
    - ("OK", filesize)
    - ("BYE", None)
    - (None, None): Khi đối phương đóng kết nối hoặc frame lỗi.
    """
    try:
        # 1. Đọc loại gói tin (Header tag)
        tag_bytes = recv_until(sock, b"|")
        if not tag_bytes:
            return None, None
        tag = tag_bytes.decode(ENCODING).strip()

        # 2. Xử lý từng loại frame
        if tag == "HI":
            name = recv_until(sock, b"|").decode(ENCODING)
            port_bytes = recv_until(sock, b"|")
            tcp_port = int(port_bytes.decode(ENCODING))
            # Trường purpose tùy chọn (CHAT / FILE)
            purpose_bytes = recv_until(sock, b"|")
            purpose = purpose_bytes.decode(ENCODING) if purpose_bytes else "CHAT"
            return "HI", (name, tcp_port, purpose)

        elif tag == "MSG":
            len_bytes = recv_until(sock, b"|")
            length = int(len_bytes.decode(ENCODING))
            payload = recv_exact(sock, length)
            if len(payload) < length:
                return None, None
            text = payload.decode(ENCODING)
            return "MSG", text

        elif tag == "FILE":
            filename = recv_until(sock, b"|").decode(ENCODING)
            filesize = int(recv_until(sock, b"|").decode(ENCODING))
            return "FILE", (filename, filesize)

        elif tag == "OK":
            filesize = int(recv_until(sock, b"|").decode(ENCODING))
            return "OK", filesize

        elif tag == "BYE":
            return "BYE", None

        else:
            # Gặp tag không hợp lệ
            return None, None

    except (ConnectionResetError, BrokenPipeError, ValueError, OSError):
        return None, None
