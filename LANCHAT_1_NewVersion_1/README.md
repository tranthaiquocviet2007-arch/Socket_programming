# SỔ TAY KỸ THUẬT & HƯỚNG DẪN VẬN HÀNH: LANCHAT_1
## *P2P LAN Chat & File Sharing qua lăng kính tư duy bản chất Richard Feynman*

> *"Nếu bạn không thể giải thích một khái niệm cho một đứa trẻ 6 tuổi hiểu, thì chính bạn cũng chưa thực sự hiểu nó."*  
> — **Richard Feynman**

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG

`LANCHAT_1` là ứng dụng truyền thông ngang hàng (**Peer-to-Peer - P2P**) hoạt động trong mạng cục bộ (LAN), được xây dựng từ các Socket nguyên bản của Python (`socket`, `threading`, `select`) kết hợp thư viện điều khiển con trỏ dòng lệnh `prompt_toolkit`.

Hệ thống vận hành theo mô hình **P2P Đối xứng (Symmetric P2P)**: Mỗi tiến trình vừa đóng vai trò là một **Máy chủ (Server)** túc trực chờ cuộc gọi đến, vừa là một **Máy khách (Client)** chủ động mở kết nối tới bạn bè.

```
                      ┌────────────────────────────────────────────────────────┐
                      │              ĐÀI PHÁT THANH TOÀN MẠNG LAN              │
                      │           Địa chỉ Broadcast: 255.255.255.255           │
                      │                     Port UDP: 9999                     │
                      └───────────────────────────┬────────────────────────────┘
                                                  │
                        Gói tin HELLO định kỳ 3s  │  Nhận diện láng giềng
                        (Không cần biết ai nghe)  │  (Thu nhặt danh bạ)
                                                  ▼
      ┌───────────────────────────────────────────────────────────────────────────────────────┐
      │                                                                                       │
      ▼                                                                                       ▼
┌───────────────────────────────┐                                           ┌───────────────────────────────┐
│         NODE 1: ALICE         │ ◄═══════════════════════════════════════► │          NODE 2: BOB          │
│  - Cổng UDP Discovery: 9999   │     KÊNH TRÒ CHUYỆN TRỰC TIẾP (TCP)       │  - Cổng UDP Discovery: 9999   │
│  - Cổng TCP Lắng nghe: 10001  │      Bắt tay 3 bước -> Stream dữ liệu     │  - Cổng TCP Lắng nghe: 10002  │
└───────────────────────────────┘                                           └───────────────────────────────┘
```

---

## 2. HƯỚNG DẪN CÀI ĐẶT & VẬN HÀNH NHANH

### 2.1. Chuẩn bị môi trường
Ứng dụng yêu cầu Python 3.8+ và thư viện `prompt_toolkit` để hỗ trợ vẽ lại giao diện dòng lệnh thời gian thực.

Tại thư mục `LANCHAT_1/`:
```bash
pip install -r requirements.txt
```
*(Lưu ý: Nếu chạy trên hệ điều hành không cài được thư viện ngoài, chương trình có cơ chế tự động chuyển sang chế độ in chuẩn an toàn).*

---

### 2.2. Kịch bản chạy trên 1 máy tính (Môi trường Loopback Test)
Mở **2 cửa sổ Terminal** độc lập tại thư mục `LANCHAT_1/`:

* **Terminal 1 (Khởi động Alice):**
  ```bash
  python3 lanchat.py --name Alice --port 10001 --bcast 127.255.255.255
  ```
* **Terminal 2 (Khởi động Bob):**
  ```bash
  python3 lanchat.py --name Bob --port 10002 --bcast 127.255.255.255
  ```

> [!IMPORTANT]
> **Chú ý về địa chỉ Broadcast nội bộ:**  
> Khi kiểm thử trên 1 máy tính, bắt buộc sử dụng địa chỉ `--bcast 127.255.255.255` (địa chỉ broadcast của dải mạng loopback `127.0.0.0/8`). Nếu bạn gõ thiếu số (ví dụ: `127.255.25`), hệ điều hành sẽ báo lỗi không tìm thấy tuyến đường gửi gói tin.

---

### 2.3. Kịch bản chạy trên 2 máy tính thật trong cùng mạng LAN / Wi-Fi
* Đảm bảo cả 2 máy kết nối chung một Router Wi-Fi hoặc Switch mạng LAN.
* Mở tường lửa (Firewall) cho phép lưu lượng qua cổng UDP `9999` và các cổng TCP.
* **Máy A:**
  ```bash
  python3 lanchat.py --name May_A
  ```
* **Máy B:**
  ```bash
  python3 lanchat.py --name May_B
  ```
*(Chương trình sẽ tự động dò tìm IP card mạng thật và phát broadcast ra toàn mạng `255.255.255.255:9999`).*

---

### 2.4. Danh mục lệnh điều khiển trong ứng dụng

| Câu lệnh | Cú pháp | Ý nghĩa & Hành vi hệ thống |
| :--- | :--- | :--- |
| **Xem danh sách** | `/list` | Quét bảng danh bạ, in ra các peer đang online/away kèm IP, Port TCP và số thứ tự (STT). |
| **Mở phòng chat** | `/chat <tên\|STT>` | Mở kết nối TCP trực tiếp tới đối tác (hỗ trợ gõ tên hoặc gõ số STT từ danh sách `/list`) và in lại lịch sử chat đã lưu. |
| **Gửi tin nhắn** | `<nội dung text>` | Gõ văn bản bình thường và nhấn `Enter` để gửi tin cho đối tác đang chat. |
| **Gửi tệp tin** | `/send <đường_dẫn>` | Mở luồng TCP riêng biệt để truyền file, hiển thị thanh tiến độ phần trăm (25%, 50%, 75%, 100%). |
| **Đổi trạng thái** | `/status <online\|away>` | Đổi trạng thái bản thân và lập tức phát broadcast UDP để bạn bè cập nhật. |
| **Rời cuộc chat** | `/leave` | Gửi bản tin `BYE|`, đóng kết nối TCP với đối tác hiện tại và quay về màn hình chờ. |
| **Xem hướng dẫn** | `/help` | In bảng trợ giúp các lệnh. |
| **Thoát an toàn** | `/quit` | Đóng toàn bộ socket, giải phóng tài nguyên cổng và tắt chương trình. |

---

### 2.5. Vị trí lưu lịch sử chat & file

Ngay khi khởi động, chương trình tạo (chỉ khi **chưa tồn tại**) các mục sau tại **thư mục đang chạy lệnh** (`os.getcwd()`):

```text
<thư_mục_chạy_lệnh>/
├── downloads/                 # File nhận được từ peer
├── sent_messages.json         # Tin nhắn / file do máy này gửi đi
└── received_messages.json     # Tin nhắn / file do peer gửi đến
```

* Chạy `python3 lanchat.py` tại thư mục `LANCHAT_1/` thì dữ liệu nằm ngay trong `LANCHAT_1/`.
* Chạy script tại thư mục khác thì dữ liệu được tạo tại thư mục đó.
* **Không bao giờ ghi đè** file đã có; chỉ tạo file rỗng `[]` nếu thiếu.
* Ghi kiểu atomic (file tạm + `os.replace`) nên tắt đột ngột không làm hỏng JSON.
* Nếu file JSON bị hỏng, chương trình đổi tên nó thành `*.broken-<timestamp>` trước khi tạo dữ liệu mới — không xóa mất dữ liệu cũ.
* Khi chạy 2 node (Alice & Bob) trong **cùng thư mục**, cả hai dùng chung 2 file JSON; trường `peer` giúp tách đúng hội thoại và khóa liên tiến trình (`flock`) đảm bảo không node nào ghi đè mất lịch sử của node kia.

Mỗi file là một mảng JSON:

```json
[
  { "peer": "Bob", "type": "text", "text": "Chào Bob", "ts": 1764230000.12 },
  { "peer": "Bob", "type": "file", "name": "a.pdf", "size": 1048576,
    "path": "/.../downloads/a.pdf", "ts": 1764230010.5 }
]
```

Ý nghĩa:

| Trường | Mô tả |
| :--- | :--- |
| `peer` | Tên peer của cuộc hội thoại |
| `type` | `text` (tin nhắn) hoặc `file` (sự kiện truyền file) |
| `text` / `name` / `size` / `path` | Nội dung tin nhắn hoặc thông tin file |
| `ts` | Thời điểm ghi (Unix timestamp) |

Khi gõ `/chat <tên>`, chương trình đọc cả 2 file, lọc theo `peer`, gộp tin **đã gửi + đã nhận**, sắp xếp theo thời gian và in lại (tối đa 200 mục gần nhất). Vì mỗi bên tự lưu trên máy mình, khi bên A tắt rồi mở lại, A vẫn thấy đầy đủ những gì A đã gửi và đã nhận trước đó.

> [!NOTE]
> Với phạm vi lưu cục bộ, tin nhắn gửi cho một peer đang **offline** sẽ báo lỗi và không được ghi vào lịch sử (chưa có hàng đợi gửi lại). File gửi đi chỉ lưu metadata + đường dẫn gốc; file nhận được lưu thật trong `downloads/`.

> [!WARNING]
> Danh sách các lỗi/giới hạn còn tồn tại (timeout, file transfer, peer crash, gói sai định dạng...) được ghi tại [`BUG_LOG.md`](BUG_LOG.md).

---

## 3. GIẢI PHÃU KỸ THUẬT THEO PHƯƠNG PHÁP FEYNMAN

### 3.1. Socket thực sự là gì dưới góc độ Hệ điều hành (Kernel)?
* **Ảo tưởng học vẹt:** Socket là một "sợi dây cáp ảo" hoặc "một tệp tin văn bản trên ổ cứng".
* **Bản chất vật lý sơ cấp:**  
  Một Socket là một **Con Trỏ Điều Khiển (File Descriptor / Handle)** do nhân hệ điều hành cấp phát trong bảng quản lý tiến trình. Khi bạn tạo một TCP socket, hệ điều hành sẽ cấp phát ngay **2 hàng đợi bộ nhớ trong RAM (Kernel Buffers)**:
  1. **Send Buffer (Bộ đệm gửi):** Khi bạn gọi `sendall(b"Hello")`, lệnh này **KHÔNG** truyền sóng điện ra dây cáp ngay lập tức! Nó chỉ đơn giản là copy chuỗi byte `"Hello"` từ không gian người dùng (User Space) vào Kernel Send Buffer. Hệ điều hành sẽ quyết định thời điểm phát xung điện ra card mạng (NIC) dựa trên cửa sổ trượt (Sliding Window) và thuật toán gom gói Nagle.
  2. **Receive Buffer (Bộ đệm nhận):** Khi card mạng nhận được xung điện từ dây cáp, nó kiểm tra mã băm CRC, ghép thành byte và ném vào Kernel Receive Buffer. Khi chương trình của bạn gọi `recv(1024)`, bạn chỉ đang thò tay vào cái chậu này để múc bytes lên.

---

### 3.2. Chức năng 1: Khám phá láng giềng (Peer Discovery qua UDP)
* **Thí nghiệm chiếc loa phát thanh ở hội trường:**  
  Hãy tưởng tượng một hội trường lớn có 100 người. Không ai biết số điện thoại của ai. Thay vì đi gõ cửa từng phòng (quét từng IP rất chậm), mỗi người cứ cách 3 giây lại cầm một chiếc loa pin phát thanh hét to:  
  `HELLO|Alice|10001|online` ra toàn hội trường.
  Bất kỳ ai đang bật máy thu thanh trên cùng tần số đều nghe thấy. Họ lấy sổ tay ra ghi chép: *"Alice đang ở phòng 192.168.1.10, cổng gọi điện riêng là 10001, trạng thái khỏe mạnh"*.
* **Bản chất kỹ thuật Socket:**
  * `socket(AF_INET, SOCK_DGRAM)`: Tạo socket UDP. Giao thức phi kết nối (Connectionless) — không có bắt tay 3 bước, không tốn tài nguyên quản lý luồng.
  * `setsockopt(SOL_SOCKET, SO_BROADCAST, 1)`: Cấp quyền cho socket được phép bắn gói tin ra địa chỉ quảng bá toàn mạng (`255.255.255.255` hoặc `127.255.255.255`). Switch mạng khi nhận được frame có MAC đích `ff:ff:ff:ff:ff:ff` sẽ tự động nhân bản gói tin ra tất cả các cổng.
  * `setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)` & `SO_REUSEPORT`: Cho phép nhiều tiến trình trên cùng 1 máy tính cùng bind chung một cổng UDP `9999`. Hệ điều hành sẽ nhân bản mỗi gói tin broadcast gửi đến cổng 9999 cho tất cả các tiến trình đang lắng nghe.
  * **Cơ chế sống/chết (Lease Timeout):** Cứ 1 giây, luồng nền sẽ kiểm tra bảng peer. Nếu một người đã quá 10 giây không phát sóng `HELLO` (tương đương bị rơi mất 3 gói liên tiếp), hệ điều hành kết luận người đó đã tắt máy hoặc rút dây mạng và tự động xóa khỏi danh sách `/list`.

---

### 3.3. Chức năng 2: Trò chuyện trực tiếp & Bóc tách ngộ nhận Message Framing (TCP Chat)
* **Thí nghiệm dòng nước liên tục vs Gói hàng bưu điện:**  
  * **Ngộ nhận chết người của sinh viên:** Nghĩ rằng nếu bên gửi gọi `send("Hello")` rồi gọi tiếp `send("World")` thì bên nhận gọi `recv()` sẽ nhận được 2 lần: lần 1 ra `"Hello"`, lần 2 ra `"World"`.
  * **Thực tế:** TCP là một **Dòng Byte liên tục (Byte Stream)** giống như dòng nước trong ống nhựa. Nó không hề có khái niệm "ranh giới tin nhắn".
    * **Dính gói (Coalescing):** Hai lần gửi bị hệ điều hành gộp lại thành 1 gói to -> bên nhận `recv()` ra `"HelloWorld"`.
    * **Vỡ gói (Fragmentation):** Một tin nhắn dài bị mạng chia cắt -> lần `recv()` thứ nhất chỉ ra `"Hel"`, lần sau mới ra `"loWorld"`.
* **Giải pháp Message Framing trong `src/protocol.py`:**  
  Chúng ta thiết kế cấu trúc phong bì có Header độ dài:
  `MSG|<length_bytes>|<utf-8 payload>`  (Ví dụ: `MSG|12|Chào bạn!`)
  * Hàm `recv_until(sock, b"|")`: Đọc từng byte một cho đến khi gặp dấu gạch đứng `|` để trích xuất thẻ tag `MSG` và con số độ dài `12`. Việc đọc từng byte ở phần Header đảm bảo tuyệt đối không đọc lẹm vào phần thân tin nhắn.
  * Hàm `recv_exact(sock, 12)`: Chạy vòng lặp gọi `sock.recv()` liên tục cho đến khi gom đủ đúng `12` bytes thì mới đóng gói trả về chuỗi hoàn chỉnh. Nhờ vậy, hiện tượng dính gói hay vỡ gói bị triệt tiêu 100%.

---

### 3.4. Chức năng 3: Truyền tệp tin song song (TCP File Transfer)
* **Thí nghiệm đường cao tốc riêng và xe chở gạch nặng:**  
  Tại sao không truyền file 100MB trên cùng kết nối TCP chat hiện tại?
  * **Hiện tượng nghẽn đầu hàng (Head-of-Line Blocking):** Nếu bạn đổ 100 triệu bytes của file vào cùng một socket chat, toàn bộ các byte đó sẽ chiếm trọn đường ống FIFO của TCP. Trong lúc file đang tải, nếu bạn muốn nhắn một tin khẩn cấp: *"Khoan, file bị virus đừng mở!"*, tin nhắn đó buộc phải xếp hàng chờ tải xong 100MB thì mới đến lượt!
* **Giải pháp của đồ án:**
  * Khi gõ `/send <file>`, chương trình mở một **Socket TCP độc lập hoàn toàn** trên một luồng nền (`Thread`) mới.
  * Handshake nhận diện: `HI|Alice|10001|FILE|` -> Phía nhận lập tức bàn giao socket này cho luồng xử lý file `FileTransferManager`, không trộn lẫn vào luồng chat.
  * Dữ liệu file được băm nhỏ thành các khối `FILE_CHUNK_SIZE = 64KB` để gửi tuần tự, báo tiến độ định kỳ (25%, 50%, 75%, 100%).
  * **An toàn dữ liệu:** Phía nhận ghi vào file tạm `downloads/<tên_file>.part`. Nếu kết nối bị đứt giữa chừng, chương trình tự động xóa file `.part` để không làm ô nhiễm ổ đĩa bằng dữ liệu rác hỏng.

---

### 3.5. Chức năng 4: Cơ chế vẽ lại Terminal (Asynchronous Console Redraw)
* **Thí nghiệm chiếc bảng phấn và bàn tay thần tốc:**  
  * **Vấn đề nhức nhối:** Màn hình console chỉ có 1 con trỏ (cursor) duy nhất. Giả sử bạn đang gõ dở câu: `> Bạn có rảnh không ch_`. Đột nhiên tin nhắn của Bob bay tới: `[Bob]: Đi uống cà phê đi!`. Nếu in thẳng ra màn hình, dòng của Bob sẽ chèn đè lên chữ bạn đang gõ, tạo thành mớ rác hiển thị: `> Bạn có [Bob]: Đi uống cà phê đi! rảnh không ch_`.
* **Giải pháp kỹ thuật:**
  * Ứng dụng tích hợp `prompt_toolkit` với cơ chế `patch_stdout()`:
    1. Lập tức xóa dòng nhập hiện tại bằng mã ANSI escape: `\r\033[K` (`\r` kéo con trỏ về đầu dòng, `\033[K` quét sạch dòng).
    2. In tin nhắn mới của Bob vào dòng trống đó và xuống dòng `\n`.
    3. Vẽ lại dấu nhắc lệnh `> ` cùng toàn bộ các ký tự bạn đang gõ dở phía dưới, đặt con trỏ chuột về đúng vị trí cũ. Trải nghiệm gõ phím của bạn hoàn toàn mượt mà, không hề bị gián đoạn!

---

## 4. BẢN CHẤT VỀ MẠNG & TẠI SAO PHẢI DÙNG CẢ 2 PORT (TCP VÀ UDP)?

Khi khởi chạy chương trình, bạn sẽ luôn nhìn thấy hai dòng thông báo khởi tạo:
```text
[*] TCP Chat Server đang lắng nghe tại port: 10001
[*] UDP Discovery đang phát và lắng nghe tại port: 9999 (Bcast: 127.255.255.255)
```

Nhiều lập trình viên mới vào nghề thường đặt câu hỏi:  
> *"Tại sao phải rắc rối như vậy? Tại sao một phần mềm chat lại phải mở tới 2 Cổng (Port)? Tại sao không dùng 1 cổng duy nhất cho xong?"*

Dưới đây là lời giải bản chất từ tầng vật lý đến kiến trúc hệ thống:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CARD MẠNG VẬT LÝ (NIC)                                            │
│                         Tiếp nhận mọi xung điện / sóng vô tuyến từ mạng LAN                             │
└────────────────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         TẦNG MẠNG (IP LAYER)                                            │
│                     Kiểm tra địa chỉ IP đích: Có phải gửi cho máy tính này không?                       │
└──────────────────────────┬───────────────────────────────────────────────────┬──────────────────────────┘
                           │ Protocol = 17 (UDP)                               │ Protocol = 6 (TCP)
                           ▼                                                   ▼
┌─────────────────────────────────────────────────────┐ ┌─────────────────────────────────────────────────┐
│              BẢNG CỔNG UDP CỦA KERNEL               │ │            BẢNG CỔNG TCP CỦA KERNEL             │
│   (Tra cứu theo số hiệu cổng UDP Header: 16 bit)    │ │  (Tra cứu theo bộ tứ 4-Tuple: IP+Port nguồn/đích) │
├─────────────────────────────────────────────────────┤ ├─────────────────────────────────────────────────┤
│ Port 9999  ──► TIẾN TRÌNH LANCHAT (Luồng Discovery) │ │ Port 10001 ──► TIẾN TRÌNH LANCHAT (Luồng Chat)   │
│ Port 53    ──► Tiến trình DNS Resolver cục bộ       │ │ Port 80    ──► Web Server Nginx                 │
└─────────────────────────────────────────────────────┘ └─────────────────────────────────────────────────┘
```

### 4.1. Bản chất của "Port" trong nhân Hệ điều hành
1. **Địa chỉ IP đại diện cho một Tòa nhà (Thiết bị vật lý):** Giúp gói tin tìm đến đúng chiếc máy tính trong không gian mạng toàn cầu.
2. **Số hiệu Cổng (Port) đại diện cho một Căn phòng trong tòa nhà (Tiến trình phần mềm):**  
   Một máy tính có thể chạy đồng thời 100 ứng dụng có kết nối mạng (trình duyệt, game, chat, cập nhật hệ thống...). Khi một gói tin chui qua dây cáp vào card mạng, làm sao hệ điều hành biết phải chuyển dữ liệu này cho ai?  
   **Port chính là mã định danh ghép kênh/phân kênh (Demultiplexing Key) 16-bit** nằm trong Header tầng Giao vận.
3. **Cổng TCP và Cổng UDP là 2 thế giới hoàn toàn độc lập:**  
   Hệ điều hành quản lý **hai bảng băm (hash table) riêng biệt**: một bảng cho TCP và một bảng cho UDP. Do đó, việc bạn dùng cổng `9999` cho UDP và cổng `10001` cho TCP (thậm chí nếu bạn dùng cùng số `9999` cho cả hai) hoàn toàn không bao giờ xảy ra xung đột trong Kernel, vì số nhận diện giao thức ở tầng IP (IP Protocol ID: TCP là 6, UDP là 17) đã tách chúng ra từ trước.

---

### 4.2. Nghịch lý nếu "Chỉ dùng một giao thức duy nhất"

Hãy cùng thực hiện 2 thí nghiệm tư duy để thấy tại sao hệ thống sẽ sụp đổ nếu bạn cố chấp chỉ dùng 1 Port hoặc 1 Giao thức:

#### Kịch bản 1: Nếu cố tình CHỈ DÙNG TCP cho mọi việc
* Giả sử bạn muốn thiết kế ứng dụng P2P LAN Chat mà **chỉ dùng duy nhất giao thức TCP**:
  * TCP là giao thức **hướng kết nối điểm - điểm (Point-to-Point, Connection-Oriented)**. Bản chất của TCP là yêu cầu phải có một bên chủ động gọi `connect()` tới địa chỉ IP và Port cụ thể của bên kia để thực hiện bắt tay 3 bước (SYN -> SYN-ACK -> ACK).
  * **TCP KHÔNG BAO GIỜ hỗ trợ tính năng Broadcast (quảng bá toàn mạng).** Bạn không thể gửi một gói tin TCP SYN tới địa chỉ `255.255.255.255`.
  * **Nghịch lý "Con gà và quả trứng":** Bạn vừa bật laptop lên. Bạn muốn chat với bạn bè trong phòng lab. Nhưng bạn chưa hề biết IP của họ là bao nhiêu, họ đang mở cổng nào, họ có đang bật máy hay không. Để biết được điều đó qua TCP, chương trình của bạn buộc phải thực hiện quét cổng (Port Scan) tất cả 254 địa chỉ IP trong mạng LAN, mỗi IP thử kết nối hàng chục cổng. Quá trình này sẽ tốn vài phút, gây nghẽn toàn bộ router Wi-Fi và có thể bị hệ thống tường lửa cảnh báo là hành vi tấn công mạng!

#### Kịch bản 2: Nếu cố tình CHỈ DÙNG UDP cho mọi việc
* Giả sử bạn nói: *"Vậy thì tôi bỏ TCP luôn, chỉ dùng duy nhất UDP broadcast port 9999 để vừa tìm bạn bè vừa chat và gửi file!"*:
  * UDP là giao thức **phi kết nối, không tin cậy (Unreliable Datagram)**: Nó giống như bưu thiếp ném vào hòm thư, không có giấy báo nhận (ACK), không có cơ chế đánh số thứ tự (Sequence Number), và không có cơ chế tự động gửi lại khi mất gói.
  * Nếu bạn gửi một file ảnh hoặc file slide thuyết trình 50MB qua UDP broadcast trên cổng 9999:
    1. **Nghẽn mạng toàn bộ phòng lab:** Gói tin broadcast sẽ bị switch nhân bản gửi tới card mạng của tất cả mọi người trong phòng, khiến máy của thầy giáo và các sinh viên khác đều phải xử lý ngắt mạng liên tục.
    2. **Dữ liệu vỡ nát:** Trong mạng không dây, việc rơi rớt vài gói tin là chuyện bình thường. Vì UDP không có cơ chế phát hiện mất gói và truyền lại, bức ảnh bạn nhận được sẽ bị khuyết tật, file PDF bị hỏng cấu trúc nhị phân và không thể mở được!

---

### 4.3. Sự kết hợp hoàn hảo: "Đài phát thanh UDP + Đường dây nóng TCP"

Chính vì vậy, mọi kỹ sư mạng máy tính hàng đầu đều áp dụng công thức phân công vai trò kinh điển:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SỰ PHÂN CÔNG VAI TRÒ CỐT LÕI                              │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│           UDP CỔNG 9999 (CỐ ĐỊNH)         │           TCP CỔNG 10001 (ĐỘC LẬP)         │
│          "ĐÀI PHÁT THANH NỘI BỘ"          │             "ĐƯỜNG DÂY NÓNG RIÊNG"         │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Nhiệm vụ: Khám phá láng giềng           │ • Nhiệm vụ: Trò chuyện và truyền tệp tin   │
│ • Cơ chế: Broadcast (1 phát tới tất cả)   │ • Cơ chế: Unicast Point-to-Point (1 - 1)   │
│ • Đặc điểm: Nhẹ, nhanh, mất gói không sao │ • Đặc điểm: Tin cậy, đúng thứ tự, bảo toàn │
│ • Chu kỳ: 3 giây phát 1 mẩu tin HELLO     │ • Thời gian: Kéo dài suốt phiên trò chuyện │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

1. **Port UDP 9999 là Cổng Thống Nhất Chung (Well-known Discovery Port):**  
   Mọi thành viên trong mạng LAN đều phải quy ước mở chung cổng UDP `9999`. Nhờ cổng cố định này, một máy mới tham gia mạng chỉ cần phát 1 gói tin `HELLO|Alice|10001` tới địa chỉ `255.255.255.255:9999` là cả làng đều nghe thấy. Trong gói tin này, Alice gửi kèm một thông điệp quan trọng: *"Số điện thoại TCP riêng của tôi là 10001"*.
2. **Port TCP 10001 là Cổng Dịch Vụ Riêng Biệt (Dedicated Conversation Port):**  
   Khi Bob đã thu được thông điệp của Alice từ đài phát thanh UDP 9999, Bob biết ngay Alice đang ở đâu. Khi Bob muốn chat riêng hoặc bắn file sang cho Alice, Bob chủ động nhấc máy gọi thẳng vào cổng TCP `10001` của Alice. Lúc này, một kênh truyền nước trực tiếp, bảo mật, có xác nhận ACK được thiết lập giữa hai người, hoàn toàn không làm phiền đến những người khác trong mạng LAN!

---

## 5. HƯỚNG DẪN BẮT GÓI TIN WIRESHARK LÀM BÁO CÁO ĐỒ ÁN

Để đạt điểm tối đa phần thực nghiệm báo cáo môn học, bạn hãy thực hiện bắt và chụp lại 3 minh chứng sau trên Wireshark:

### 5.1. Minh chứng 1: Gói tin UDP Broadcast Discovery
* **Bộ lọc Wireshark:**
  ```wireshark
  udp.port == 9999
  ```
* **Hiện tượng quan sát được:**
  * Địa chỉ IP đích: `127.255.255.255` hoặc `255.255.255.255`.
  * Địa chỉ MAC đích: `ff:ff:ff:ff:ff:ff` (Broadcast Ethernet Frame).
  * Chu kỳ xuất hiện đều đặn mỗi 3 giây.
  * Click vào phần **Data (Payload)** ở khung chi tiết gói tin, bạn sẽ thấy rõ văn bản thô dạng ASCII: `HELLO|Alice|10001|online`.

---

### 5.2. Minh chứng 2: Quá trình bắt tay 3 bước TCP (3-Way Handshake)
* **Bộ lọc Wireshark:**
  ```wireshark
  tcp.port == 10001 || tcp.port == 10002
  ```
* **Hiện tượng quan sát được khi Alice bắt đầu `/chat Bob`:**
  1. Gói 1: Alice -> Bob với cờ `[SYN]`, kèm số thứ tự khởi tạo `Seq = 0`.
  2. Gói 2: Bob -> Alice với cờ `[SYN, ACK]`, xác nhận `Ack = 1` và đưa ra `Seq = 0` của Bob.
  3. Gói 3: Alice -> Bob với cờ `[ACK]`, xác nhận `Ack = 1`.  
  *Ngay sau 3 gói tin này, trạng thái TCP chuyển sang `ESTABLISHED` và kết nối chính thức thông suốt.*

---

### 5.3. Minh chứng 3: Luồng dữ liệu Message Framing (TCP Stream)
* Click chuột phải vào một gói tin TCP có cờ `[PSH, ACK]` mang dữ liệu chat.
* Chọn menu **Follow** -> **TCP Stream**.
* **Bức ảnh đắt giá cho báo cáo:** Bạn sẽ thấy toàn bộ hội thoại được hiển thị dưới dạng luồng dữ liệu liên tục:
  ```text
  HI|Alice|10001|CHAT|
  HI|Bob|10002|CHAT|
  MSG|35|Chào Bob, bạn có rảnh không?
  MSG|28|Mình rảnh, có chuyện gì thế?
  BYE|
  ```
* Giải thích trong báo cáo: Header `MSG|<length>|` đóng vai trò là "mỏ neo độ dài" giúp bộ phân tích cú pháp ở tầng ứng dụng biết chính xác cần đọc bao nhiêu bytes từ Kernel Buffer để khôi phục lại trọn vẹn câu nói của người dùng.

---

## 6. BỘ CÂU HỎI CHẨN ĐOÁN NGỘ NHẬN (FEYNMAN DIAGNOSTIC PROBES)

#### Câu hỏi 1: Tại sao không dùng cùng số cổng 9999 cho cả UDP và TCP?
> **Tình huống:** Một bạn sinh viên thắc mắc: *"Tại sao không đặt cả TCP server lắng nghe trên cổng 9999 luôn cho đỡ phải nhớ nhiều số cổng?"*
> **Góc nhìn bản chất Feynman:**  
> Hoàn toàn có thể đặt TCP server cổng 9999 trên một máy đơn lẻ mà không xung đột! Tuy nhiên, trong đồ án P2P khi kiểm thử nhiều tiến trình trên cùng 1 máy tính:
> - Cổng UDP 9999 cho phép nhiều tiến trình cùng bind nhờ cơ chế `SO_REUSEPORT` (chia sẻ cổng broadcast).
> - Nhưng cổng TCP 9999 là cổng lắng nghe kết nối độc quyền (Exclusive Binding). Một khi Alice đã bind TCP cổng 9999, thì Bob trên cùng máy đó sẽ bị hệ điều hành báo lỗi ngay: `Address already in use`! Do đó, mỗi node buộc phải có một cổng TCP riêng biệt (10001, 10002, hoặc để hệ điều hành tự cấp phát cổng ngẫu nhiên `port=0`).

#### Câu hỏi 2: Gói tin `HELLO` của UDP có cần mã hóa độ dài như TCP `MSG` không?
> **Tình huống:** Tại sao trong `src/protocol.py`, gói `MSG` của TCP phải có `MSG|<length>|`, trong khi gói `HELLO` của UDP chỉ cần `HELLO|<name>|<port>|<status>` mà không cần ghi độ dài?
> **Góc nhìn bản chất Feynman:**  
> Bởi vì **bản chất cấu trúc vật lý của hai giao thức khác nhau hoàn toàn**:
> - TCP là Byte Stream: Không có ranh giới gói tin. Dữ liệu các lần gửi bị dính chùm vào nhau trong Kernel Buffer, nên bắt buộc tầng ứng dụng phải tự ghi độ dài để biết chỗ nào cần cắt.
> - UDP là Datagram: Mỗi lần gọi `sendto()` sinh ra đúng **một gói tin độc lập** có ranh giới rõ ràng. Ở đầu nhận, mỗi lần gọi `recvfrom()` hệ điều hành trả về trọn vẹn đúng một gói tin đó. Do đó, UDP đã có sẵn ranh giới gói tin tự nhiên từ tầng mạng, không bao giờ bị hiện tượng dính chùm 2 gói `HELLO` vào nhau!

---

*Tài liệu được biên soạn phục vụ công tác nghiên cứu, học tập và bảo vệ đồ án Mạng Máy Tính.*
