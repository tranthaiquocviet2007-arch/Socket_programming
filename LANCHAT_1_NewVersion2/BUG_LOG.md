# NHẬT KÝ LỖI — NHỮNG PHẦN CHƯA SỬA

- **Ngày rà soát:** 27/11/2026
- **Phạm vi:** 5 tình huống kiểm thử trong rubric + rà soát tổng quát toàn bộ luồng TCP/UDP/file/lịch sử.
- **Môi trường:** Python 3.14, Linux, mô hình P2P LAN (UDP Discovery + TCP Chat/File).
- **Quy ước:**
  - ❌ **Chưa sửa** — còn nguyên trong code hiện tại.
  - ⚠️ **Chưa sửa hoàn toàn** — có xử lý một phần nhưng chưa đủ.
  - ✅ **Đã sửa** — chỉ dùng ở mục 0 để đối chiếu.

> Mục tiêu của file này: ghi lại **trung thực** những gì hiện tại còn thiếu/lỗi, để chuẩn bị kịch bản demo và trả lời giảng viên. Không đánh dấu "đã sửa" cho phần chưa kiểm chứng.

---

## 0. Những phần ĐÃ sửa trong đợt gần nhất (để đối chiếu)

| # | Nội dung | Trạng thái |
| :--- | :--- | :--- |
| 0.1 | Lưu lịch sử chat bằng `sent_messages.json` + `received_messages.json`, tạo tại thư mục đang chạy lệnh, chỉ tạo khi chưa có | ✅ |
| 0.2 | Ghi JSON atomic (file tạm + `os.replace`), không ghi đè file đã tồn tại | ✅ |
| 0.3 | File JSON hỏng được đổi tên `*.broken-<timestamp>` thay vì xóa mất dữ liệu | ✅ |
| 0.4 | Khóa liên tiến trình `flock` để 2 node chạy cùng thư mục không ghi đè lịch sử của nhau | ✅ |
| 0.5 | File nhận lưu vào `downloads/<tên_peer>/`, ghi metadata file gửi/nhận vào lịch sử | ✅ |
| 0.6 | `parse_tcp_frame()` bắt thêm `OSError` — giảm traceback khi socket bị đóng đột ngột | ✅ |
| 0.7 | `test_simulation.py` chỉ xóa file test, không xóa cả thư mục `downloads/` của người dùng | ✅ |
| 0.8 | `/chat <peer>` in lại lịch sử đã gửi + đã nhận | ✅ |
| 0.9 | File nhận tách thư mục theo peer (`downloads/<peer>/`), tên file ghi vào lịch sử khớp với đĩa | ✅ |
| 0.10 | Socket truyền file có timeout 30 giây cho connect/send/recv/ACK (ISSUE-05) | ✅ |
| 0.11 | Receiver gửi `OK\|<size>\|` sau khi lưu xong; sender chỉ báo thành công khi nhận ACK (ISSUE-06) | ✅ |
| 0.12 | `/chat` có timeout kết nối 3s/handshake 5s; gói đầu TCP không hoàn chỉnh bị đóng sau 5s (ISSUE-01, một phần ISSUE-08) | ✅ |
| 0.13 | Khi kết nối chat hiện tại đóng/EOF, quay về prompt chưa chọn peer (ISSUE-04) | ✅ |

**Các mục khác vẫn còn mở hoặc chỉ mới được sửa một phần; xem bảng dưới.**

---

## 1. Bảng tổng hợp mức độ ưu tiên

| ID | Mức độ | Tình huống rubric | Trạng thái |
| :--- | :--- | :--- | :--- |
| ISSUE-01 | 🔴 Cao | Chat với người vừa offline | ✅ Đã sửa |
| ISSUE-02 | 🔴 Cao | Chat / gửi tin khi mạng chập chờn | ❌ Chưa sửa |
| ISSUE-03 | 🔴 Cao | Peer crash / mất mạng im lặng | ❌ Chưa sửa |
| ISSUE-04 | 🟠 Trung bình | Peer crash giữa lúc chat | ✅ Đã sửa khi TCP đóng/EOF |
| ISSUE-05 | 🔴 Cao | Mất kết nối khi gửi file | ✅ Đã sửa |
| ISSUE-06 | 🔴 Cao | Mất kết nối khi gửi file | ✅ Đã sửa |
| ISSUE-07 | 🟠 Trung bình | File đứt giữa chừng / app bị kill | ❌ Chưa sửa |
| ISSUE-08 | 🟠 Trung bình | Gói sai định dạng (`nc`) | ⚠️ Chưa sửa hoàn toàn |
| ISSUE-09 | 🟠 Trung bình | Gói sai định dạng / DoS | ❌ Chưa sửa |
| ISSUE-10 | 🟡 Thấp | Lệnh sai, file không có | ⚠️ Chưa sửa hoàn toàn |
| ISSUE-11 | 🟠 Trung bình | Gửi tin thất bại | ❌ Chưa sửa |
| ISSUE-12 | 🟡 Thấp | Gửi file | ✅ Đã sửa |
| ISSUE-13 | 🟡 Thấp | Lịch sử chat | ❌ Chưa sửa |
| ISSUE-14 | 🟡 Thấp | Thoát chương trình | ❌ Chưa sửa |
| ISSUE-15 | 🟠 Trung bình | Bảo mật / danh tính peer | ❌ Chưa sửa |
| ISSUE-16 | 🟡 Thấp | Trùng tên peer | ❌ Chưa sửa |
| ISSUE-17 | 🟠 Trung bình | Offline / đứt file | ❌ Chưa sửa |

---

## 2. Chi tiết các vấn đề và trạng thái hiện tại

### ISSUE-01 — TCP `connect()` và handshake không có timeout

- **Mức độ:** 🔴 Cao
- **Tình huống rubric:** *Chat với người vừa offline* — "Tắt Minh, Quan gõ ngay `/chat Minh`".
- **Hiện tượng:**
  - Minh tắt **app** nhưng máy vẫn bật → `ConnectionRefused` → báo lỗi ngay, không crash. ✅
  - Minh tắt **máy / Wi-Fi** → `connect()` treo theo timeout của OS (Linux thường 1–2 phút). UI đứng im, không có prompt, không thông báo. ❌
  - Kết nối được nhưng bên kia không gửi `HI` → `parse_tcp_frame()` chờ vô hạn.
- **Vị trí code trước khi sửa:** `get_or_create_connection()` trong `src/chat_manager.py` không đặt timeout trước `connect()` hoặc `parse_tcp_frame()`.
- **Ảnh hưởng:** `cmd_chat` chạy trên luồng nhập lệnh nên cả terminal bị treo; giảng viên có thể tưởng chương trình "đơ".
- **Hướng sửa tối thiểu:**
  ```python
  sock.settimeout(3.0)      # trước connect
  ...
  sock.settimeout(5.0)      # cho handshake
  ```
  Timeout/lỗi → thông báo và trả `None`.
- **Cách kiểm tra:** tắt Wi-Fi máy Minh, chạy `/chat Minh` → phải báo timeout sau ~3–5 giây, prompt còn hoạt động.
- **Trạng thái:** ✅ **Đã sửa cho kịch bản demo.** Socket chat chủ động có timeout 3 giây khi `connect`, 5 giây khi gửi/đợi handshake; sau handshake trở về chế độ chờ bình thường để cuộc trò chuyện im lặng không bị ngắt. Nếu không có phản hồi hợp lệ thì báo lỗi và trả prompt. Kết nối TCP phía nhận cũng có timeout 5 giây ở bước gói đầu.

---

### ISSUE-02 — `sendall()` chat chạy trên UI thread, không timeout

- **Mức độ:** 🔴 Cao
- **Tình huống rubric:** *Peer crash giữa lúc chat*, *mất mạng khi đang chat*.
- **Hiện tượng:** Khi mạng chập chờn, `sock.sendall(format_msg(text))` có thể block. Vì được gọi trực tiếp từ `_handle_user_input()` (luồng nhập lệnh), toàn bộ prompt bị treo theo.
- **Vị trí code:**
  - `src/chat_manager.py:242–247` — `sock.sendall(...)`.
  - `src/ui.py:272` — gọi `send_chat()` trực tiếp trong luồng UI.
- **Ảnh hưởng:** Không có thông báo, không thể Ctrl+C sạch, trải nghiệm giống "crash".
- **Hướng sửa:** đặt timeout gửi (ví dụ 5–10 giây) hoặc đẩy việc gửi sang thread nền; nếu lỗi thì hiển thị lại tin nhắn để người dùng gửi lại.
- **Trạng thái:** ❌ **Chưa sửa.** Việc gửi tin chat vẫn chạy trên luồng UI; không nằm trong 5 kịch bản demo đã chốt.

---

### ISSUE-03 — Không phát hiện peer chết "im lặng" (không FIN/RST)

- **Mức độ:** 🔴 Cao
- **Tình huống rubric:** *Peer crash giữa lúc chat* — "Đóng cửa sổ của Minh, không gửi BYE".
- **Hiện tượng:**
  - Đóng app bình thường → OS gửi FIN → phát hiện được. ✅
  - Rút mạng / tắt nguồn / mất Wi-Fi → không có FIN; `recv()` trong `_receive_loop` chờ vô hạn (TCP keepalive mặc định ~2 giờ).
- **Vị trí code:**
  - `src/chat_manager.py:196–228` — vòng `_receive_loop`.
  - `src/peer_manager.py:160–172` — đã phát hiện peer offline sau 10 giây nhưng **chỉ in thông báo**, không báo cho `ChatManager`.
  - `src/lanchat.py` — `on_peer_change=ui.on_peer_change`, chưa nối sang ChatManager.
- **Ảnh hưởng:** Hai bên vẫn nghĩ phiên chat còn sống; gửi tin sẽ thất bại âm thầm hoặc treo.
- **Hướng sửa:**
  - Bật `SO_KEEPALIVE` + tinh chỉnh `TCP_KEEPIDLE=10`, `TCP_KEEPINTVL=3`, `TCP_KEEPCNT=3` (Linux), **hoặc**
  - Khi `PeerManager` báo `offline`, gọi `ChatManager.handle_peer_offline(name)` để đóng socket + reset trạng thái + notify.
  - Có thể thêm app-level `PING/PONG` mỗi 5–10 giây.
- **Trạng thái:** ❌ **Chưa sửa cho trường hợp mất mạng im lặng.** Demo đóng cửa sổ ứng dụng: TCP trả EOF/lỗi và prompt được reset theo ISSUE-04.

---

### ISSUE-04 — `active_partner` không được reset khi mất kết nối

- **Mức độ:** 🟠 Trung bình
- **Tình huống rubric:** *Peer crash giữa lúc chat* — kỳ vọng "về prompt".
- **Hiện tượng:** Sau khi peer ngắt kết nối, `active_partner` vẫn giữ tên peer. Prompt vẫn hiện `[Minh -> Quan] >` dù Quan đã offline. Gõ tin tiếp theo sẽ cố kết nối lại (có thể treo theo ISSUE-01).
- **Vị trí code trước khi sửa:** cuối `_receive_loop()` trong `src/chat_manager.py` chỉ notify, không đổi trạng thái.
- **Hướng sửa:** đặt `active_partner = None` hoặc thêm trạng thái `offline` riêng; cập nhật prompt tương ứng.
- **Trạng thái:** ✅ **Đã sửa cho trường hợp TCP đóng/EOF.** Khi socket chat hiện tại ngắt, `active_partner` về `None`, thông báo mất kết nối và prompt quay về trạng thái chưa chat. Mất mạng im lặng không có FIN/RST vẫn thuộc ISSUE-03.

---

### ISSUE-05 — Socket truyền file không có timeout

- **Mức độ:** 🔴 Cao
- **Tình huống rubric:** *Mất kết nối mạng khi gửi file* — "Tắt Wi-Fi của Quan lúc đang 50%".
- **Hiện tượng:**
  - `sendall(chunk)` / `recv()` có thể block rất lâu khi mạng mất mà không có RST. Hai bên không báo lỗi kịp thời.
  - Nếu mạng chỉ rớt ngắn và cùng socket TCP sống lại → file tiếp tục trên cùng kết nối. Đây là hành vi đúng của TCP nhưng dễ gây ngộ nhận là "resume".
- **Vị trí code:**
  - `src/file_transfer.py:80` — `sock.connect` không timeout.
  - `src/file_transfer.py:91–98` — `sendall` không timeout.
  - `src/file_transfer.py:145` — `sock.recv` không timeout.
- **Hướng sửa:** `sock.settimeout(30)`; timeout → notify + đóng + để receiver xóa `.part`. Cân nhắc `SO_KEEPALIVE`.
- **Trạng thái:** ✅ **Đã sửa.** Thêm `FILE_IO_TIMEOUT = 30` trong `src/config.py`; cả `_send_file_worker` và `_receive_file_worker` đều gọi `sock.settimeout(FILE_IO_TIMEOUT)` trước khi connect/recv/send. Khi timeout, sender báo lỗi; receiver xóa `.part` như cũ.

---

### ISSUE-06 — Không có ACK/hash cuối file; sender có thể báo 100% giả

- **Mức độ:** 🔴 Cao
- **Tình huống rubric:** *Mất kết nối mạng khi gửi file* — kỳ vọng cả hai bên báo lỗi.
- **Hiện tượng:** Sender báo "Gửi file thành công" ngay sau khi `sendall()` hết dữ liệu. `sendall` chỉ đẩy vào kernel buffer; nếu mạng đứt sau đó hoặc receiver ghi đĩa lỗi, sender vẫn báo thành công.
- **Vị trí code:** `src/file_transfer.py:91–108` — không chờ phản hồi từ receiver; protocol không có frame ACK sau dữ liệu.
- **Hướng sửa:** receiver gửi `OK|<size>` sau `os.rename`; sender chờ ACK với timeout rồi mới báo thành công. Nên thêm SHA-256 để kiểm tra toàn vẹn.
- **Trạng thái:** ✅ **Đã sửa (không dùng SHA-256 theo phạm vi đồ án).** Receiver gửi `OK|<filesize>|` sau khi `os.replace` thành công; sender chờ ACK (timeout 30 giây) và so khớp đúng `filesize` rồi mới notify thành công + ghi lịch sử. Không có ACK / sai kích thước → sender báo lỗi, không ghi "đã gửi".

---

### ISSUE-07 — `.part` mồ côi không được dọn; đứt file không resume

- **Mức độ:** 🟠 Trung bình
- **Tình huống rubric:** *Mất kết nối mạng khi gửi file* — "Minh xóa `slides.pdf.part`".
- **Hiện tượng:**
  - Đứt kết nối bình thường → `_receive_file_worker` xóa `.part` trong `except`. ✅
  - Receiver bị **kill / mất điện** → không chạy `finally` → `.part` nằm lại vĩnh viễn; lần khởi động sau không dọn.
  - Không có resume: lần gửi sau ghi lại `.part` từ đầu.
- **Vị trí code:** `src/file_transfer.py:129–174` — chỉ xóa `.part` khi bắt được exception trong tiến trình. Từ bản sửa ISSUE-12, file tạm nằm trong `downloads/<tên_peer>/.lanchat-<uuid>.part` (có thư mục con), nên bước dọn lúc khởi động phải quét đệ quy.
- **Hướng sửa:** lúc khởi động quét `downloads/**/*.part` và xóa (hoặc báo); nếu muốn resume thật thì lưu offset + `file_id` và giữ `.part` có kiểm soát.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-08 — `nc` giữ kết nối mở làm treo thread; không log kết nối bị từ chối

- **Mức độ:** 🟠 Trung bình
- **Tình huống rubric:** *Gói sai định dạng* — `nc 192.168.1.12 6000`, gõ `abc`.
- **Hiện tượng:**
  - Trước khi sửa, `nc` gửi `abc` rồi **để kết nối mở** → `recv_until()` chờ dấu `|` vô hạn.
  - `abc|` hoặc đóng kết nối → bị từ chối, đóng socket, app chạy tiếp. ✅
  - Không có dòng log "đã từ chối kết nối sai định dạng từ IP:port".
- **Vị trí code:** `src/chat_manager.py:108–147`, `src/protocol.py:94–111`.
- **Hướng sửa:** `sock.settimeout(5.0)` cho handshake; log rõ nguồn gửi; gửi `BYE|` trước khi đóng nếu muốn lịch sự.
- **Trạng thái:** ⚠️ **Đạt yêu cầu demo:** handshake có timeout 5 giây nên gói `abc` không hoàn chỉnh bị đóng, chương trình vẫn chạy. Chưa log lý do/IP của kết nối bị từ chối; không giới hạn số kết nối (ISSUE-09).

---

### ISSUE-09 — Không giới hạn kích thước message/file và số kết nối

- **Mức độ:** 🟠 Trung bình
- **Tình huống rubric:** *Gói sai định dạng* / tấn công đơn giản bằng `nc`.
- **Hiện tượng:**
  - `MSG|<length>|` do bên gửi tự khai; `recv_exact()` cấp phát theo `length` → gửi `MSG|999999999|` có thể làm tốn RAM.
  - Không giới hạn `filesize`; không giới hạn số kết nối đồng thời (mỗi kết nối một thread).
- **Vị trí code:** `src/protocol.py:77–111`, `src/chat_manager.py:92–101`.
- **Hướng sửa:** thêm `MAX_MESSAGE_SIZE` (ví dụ 1 MB), `MAX_FILE_SIZE`, `MAX_CONNECTIONS`; kiểm tra trước khi cấp phát/ghi.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-10 — Xử lý lỗi đường dẫn file chưa thân thiện

- **Mức độ:** 🟡 Thấp
- **Tình huống rubric:** *Lệnh sai, file không có* — `/send khongco.pdf`.
- **Hiện tượng:**
  - File không tồn tại → báo đúng "File ... không tồn tại". ✅
  - `~/Downloads/a.pdf` không được expand → báo sai là không tồn tại.
  - Đường dẫn là **thư mục** vẫn báo "không tồn tại" → dễ hiểu nhầm.
  - Không phân biệt "không có quyền đọc".
- **Vị trí code:** `src/ui.py:175–181`, `src/file_transfer.py:61–63`.
- **Hướng sửa:** `os.path.expanduser`, kiểm tra `os.path.isdir`, `os.access(path, os.R_OK)` và thông báo cụ thể từng trường hợp.
- **Trạng thái:** ⚠️ **Đạt yêu cầu demo:** `/chta` báo lệnh không xác định và hướng dẫn dùng `/help`; `/send khongco.pdf` báo file không tồn tại, kể cả khi chưa mở chat. Chưa hỗ trợ `~` hay báo lỗi chi tiết với thư mục/quyền đọc.

---

### ISSUE-11 — Gửi tin thất bại làm mất nội dung đã gõ

- **Mức độ:** 🟠 Trung bình
- **Tình huống rubric:** *Peer crash giữa lúc chat*.
- **Hiện tượng:** `send_chat()` trả `False`, UI không hiển thị lại tin nhắn, người dùng phải gõ lại. Tin thất bại không được lưu lịch sử (đúng về mặt dữ liệu, nhưng trải nghiệm kém).
- **Vị trí code:** `src/ui.py:269–272`, `src/chat_manager.py:248–253`.
- **Hướng sửa:** khi gửi lỗi, in lại `[Gửi thất bại] <nội dung>` hoặc lưu nháp; có thể thêm hàng đợi gửi lại.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-12 — Hai file cùng tên đến đồng thời có thể tranh nhau `.part`

- **Mức độ:** 🟡 Thấp
- **Tình huống:** Hai peer cùng gửi `slides.pdf` một lúc.
- **Hiện tượng:** `_get_unique_filepath()` kiểm tra tồn tại rồi mới trả đường dẫn (TOCTOU). Hai thread có thể nhận cùng `dest_path` và cùng ghi một `.part`.
- **Vị trí code:** `src/file_transfer.py:18–26` (trước khi sửa).
- **Hướng sửa:** thêm hậu tố duy nhất (`timestamp`/`uuid`/`thread id`) hoặc khóa khi cấp phát tên.
- **Trạng thái:** ✅ **Đã sửa.** Dùng `_reserve_unique_filepath()` với `os.open(..., O_CREAT|O_EXCL)` để giữ chỗ tên file atomically tại thời điểm hoàn tất; file tạm `.part` mang tên ngẫu nhiên (UUID) nên hai luồng không ghi chung. File nhận được tách vào `downloads/<tên_peer>/` nên hai peer cùng tên file không còn tranh nhau. Tên file ghi vào lịch sử lấy từ đường dẫn thực tế sau khi giải quyết trùng tên.

---

### ISSUE-13 — Lịch sử JSON phình to, ghi lại toàn bộ file mỗi tin

- **Mức độ:** 🟡 Thấp
- **Tình huống:** Chat lâu, nhiều tin.
- **Hiện tượng:** Mỗi lần ghi, `ChatHistory` đọc và `json.dump` **toàn bộ** mảng ra file. Với N tin, chi phí ghi tăng dần (tổng ~O(N²)); file không có giới hạn kích thước.
- **Vị trí code:** `src/history.py:198–210`, `src/history.py:186`.
- **Hướng sửa:** dùng JSONL append-only, hoặc giới hạn N bản ghi gần nhất / xoay vòng file.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-14 — Thoát chương trình không broadcast offline

- **Mức độ:** 🟡 Thấp
- **Tình huống:** `/quit` hoặc đóng app.
- **Hiện tượng:** `PeerManager.stop()` chỉ đóng socket UDP; không gửi gói "offline". Người khác vẫn thấy peer online thêm tối đa 10 giây (PEER_TIMEOUT).
- **Vị trí code:** `src/peer_manager.py:81–88`.
- **Hướng sửa:** gửi một gói `HELLO|name|port|offline` (hoặc `BYE`) trước khi đóng; phía nhận xóa ngay khỏi bảng.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-15 — Không xác thực, không mã hóa, có thể giả tên peer

- **Mức độ:** 🟠 Trung bình (tùy yêu cầu môn học)
- **Tình huống:** Bất kỳ máy nào trong LAN gửi `HELLO|Minh|...` đều có thể giả làm Minh; `nc` có thể gửi frame tùy ý.
- **Vị trí code:** `src/peer_manager.py` (UDP không auth), `src/protocol.py` (plaintext).
- **Hướng sửa:** ngoài phạm vi đồ án cơ bản; nếu cần có thể thêm token/secret chia sẻ hoặc TLS.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-16 — Tên peer không unique

- **Mức độ:** 🟡 Thấp
- **Tình huống:** Hai máy chạy cùng `--name Minh`.
- **Hiện tượng:** `PeerManager.peers` dùng `name` làm khóa → node sau ghi đè node trước; chat/file có thể đi nhầm máy.
- **Vị trí code:** `src/peer_manager.py:141–158`.
- **Hướng sửa:** dùng `name#uuid` hoặc `(name, ip, port)` làm định danh; cảnh báo trùng tên.
- **Trạng thái:** ❌ **Chưa sửa.**

---

### ISSUE-17 — Không có resume file / hàng đợi offline

- **Mức độ:** 🟠 Trung bình
- **Tình huống:** Đứt file ở 50%, hoặc gửi tin cho peer offline.
- **Hiện tượng:** Đứt file → gửi lại từ 0%. Gửi tin cho peer offline → báo lỗi, không lưu chờ.
- **Vị trí code:** `src/file_transfer.py`, `src/chat_manager.py`.
- **Hướng sửa:** lưu `pending_transfers.json` + offset; khi peer online lại thì `seek(offset)` và gửi tiếp. Tin nhắn có thể thêm outbox tương tự.
- **Trạng thái:** ❌ **Chưa sửa.**

---

## 3. Đối chiếu nhanh với 5 tình huống rubric

| Tình huống | Kết quả hiện tại | Còn thiếu |
| :--- | :--- | :--- |
| Chat với người vừa offline | Kết nối bị từ chối hoặc timeout (3s connect/5s handshake) → báo lỗi, prompt tiếp tục. | Không có trong demo |
| Peer crash giữa lúc chat | Đóng cửa sổ → TCP EOF/lỗi → báo mất kết nối, reset prompt. | Mất mạng im lặng không có EOF (ISSUE-03) nằm ngoài tình huống này |
| Mất mạng khi gửi file | Timeout 30s cho thao tác socket, receiver dọn `.part` khi bắt được lỗi; sender chỉ báo thành công sau ACK. | Kill ứng dụng có thể để `.part` mồ côi (ISSUE-07); tên tạm hiện là `.lanchat-<uuid>.part` trong `downloads/<peer>/` |
| Gói sai định dạng | `abc` giữ kết nối → timeout 5s rồi đóng socket đó; app tiếp tục. | Chưa log từ chối hoặc giới hạn số kết nối (ISSUE-08/09) |
| Lệnh sai, file không có | `/chta` báo lệnh sai và nhắc dùng `/help`; `/send khongco.pdf` báo không tồn tại. | `~`, thư mục, quyền đọc (ISSUE-10) ngoài demo |

---

## 4. Kịch bản demo đề xuất (ngắn)

1. **Offline:** tắt app Minh → `/chat Minh` → lỗi ngay. Tắt Wi-Fi Minh → `/chat Minh` → chờ timeout (sau khi sửa ISSUE-01) → báo lỗi, prompt sống.
2. **Peer crash:** kill app Minh giữa lúc chat → Quan nhận thông báo mất kết nối; gõ tin tiếp → báo không kết nối, không crash.
3. **File:** gửi file lớn, tắt Wi-Fi ở ~50% → sau timeout cả hai báo lỗi; kiểm tra `downloads/` không còn `.part`.
4. **Sai định dạng:** `nc <ip> <port>`, gõ `abc|` → app từ chối, vẫn chat bình thường; gõ `abc` rồi để mở → chờ timeout rồi đóng.
5. **Lệnh sai:** `/chta Minh`, `/send khongco.pdf`, `/send ~/khongco.pdf` → thông báo rõ, không crash.

---

## 5. Lệnh kiểm tra lại

```bash
# Unit test
python3 -m unittest discover -s tests -v

# Mô phỏng 2 peer end-to-end
python3 test_simulation.py

# Kiểm tra cú pháp toàn bộ
python3 -m py_compile lanchat.py test_simulation.py src/*.py tests/*.py
```

---

*File này chỉ ghi nhận hiện trạng. Khi sửa xong một mục, đổi trạng thái tương ứng và ghi ngày + cách kiểm chứng.*
