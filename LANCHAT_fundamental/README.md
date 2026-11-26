# SỔ TAY KỸ THUẬT & CẨM NANG NỀN TẢNG: LANCHAT_FUNDAMENTAL
## *Giải mã bản chất Socket Programming qua lăng kính tư duy Richard Feynman*

> *"Biết tên một loài chim trong tất cả các thứ tiếng trên thế giới không có nghĩa là bạn hiểu bất kỳ điều gì về con chim đó."*  
> — **Richard Feynman**

---

## 1. TỔNG QUAN KIẾN TRÚC & MỤC TIÊU SƯ PHẠM

`LANCHAT_fundamental` là bộ dự án học tập được thiết kế tinh giản (minimalist) nhằm mục đích **tổng hợp vừa đủ và chuẩn xác toàn bộ nội dung lý thuyết lẫn thực hành** trong bài giảng môn Mạng Máy Tính (*Seminar Socket Programming with Python* và *Hướng dẫn lập trình Socket - HDLT_Socket*).

Dự án được xây dựng với các nguyên tắc giáo trình nghiêm ngặt:
* **Thuần 100% Python Standard Library:** Không cài thêm bất kỳ thư viện ngoài nào (không dùng `pip`, chỉ sử dụng các module tích hợp sẵn `socket`, `threading`, `time`, `sys`). Bất kỳ máy tính nào cài Python đều có thể chạy ngay lập tức.
* **Mã nguồn trong sáng, chú thích tiếng Việt từng bước:** Phân tích trực diện lý do tại sao phải gọi từng hàm hệ thống, giải quyết triệt để rào cản học vẹt câu lệnh.
* **Cung cấp đủ 2 mô hình kinh điển để đối chiếu:**
  1. **Mô hình Tập trung (Client - Server):** Nằm trong thư mục `client_server_demo/` (Minh họa trực quan nội dung Slide 20–25).
  2. **Mô hình Ngang hàng (Peer - to - Peer):** Nằm trong tệp `p2p_chat.py` (Minh họa bản chất đồ án P2P rút gọn trong một tệp duy nhất ~200 dòng).

```
                            SỰ CHUYỂN DỊCH TƯ DUY KIẾN TRÚC MẠNG
                            
    MÔ HÌNH CLIENT - SERVER (TẬP TRUNG)                 MÔ HÌNH PEER - TO - PEER (PHÂN TÁN)
             client_server_demo/                                     p2p_chat.py

               ┌──────────────┐                               ┌──────────┐      TCP      ┌──────────┐
               │    SERVER    │                               │  ALICE   │ ◄═══════════► │   BOB    │
               │ (Port 50000) │                               │(TCP/UDP) │               │(TCP/UDP) │
               └──────┬───────┘                               └────▲─────┘               └────▲─────┘
         ┌────────────┼────────────┐                               │                          │
   TCP   │      TCP   │      TCP   │                               └──────────────┬───────────┘
         ▼            ▼            ▼                                              │ UDP Broadcast 50005
    ┌─────────┐  ┌─────────┐  ┌─────────┐                                         ▼
    │ Client1 │  │ Client2 │  │ Client3 │                           ┌───────────────────────────┐
    │ (Alice) │  │  (Bob)  │  │(Charlie)│                           │ ĐÀI PHÁT THANH TOÀN MẠNG  │
    └─────────┘  └─────────┘  └─────────┘                           └───────────────────────────┘
```

---

## 2. HƯỚNG DẪN CÀI ĐẶT & CHẠY THỬ NGHIỆM TỪNG BƯỚC

Toàn bộ dự án không có file `requirements.txt` vì không phụ thuộc vào bất kỳ bên thứ ba nào. Bạn chỉ cần mở Terminal và thực thi trực tiếp bằng Python 3.

### 2.1. Kịch bản 1: Thử nghiệm phòng chat Client - Server (`client_server_demo/`)
*Mô hình kinh điển: 1 Server trung tâm phục vụ nhiều Client đồng thời theo đúng bài giảng slide.*

Mở **3 cửa sổ Terminal** độc lập:

* **Terminal 1 (Bật Server trung tâm):**
  ```bash
  cd /home/vite/Documents/Mon_hoc/MMT/Socket_Programming/LANCHAT_fundamental/client_server_demo
  python3 server.py
  ```
  *Server sẽ lắng nghe tại cổng TCP 50000.*

* **Terminal 2 (Client Alice tham gia):**
  ```bash
  cd /home/vite/Documents/Mon_hoc/MMT/Socket_Programming/LANCHAT_fundamental/client_server_demo
  python3 client.py
  # Nhấn Enter để dùng IP mặc định (127.0.0.1)
  # Nhấn Enter để dùng Port mặc định (50000)
  # Nhập Nickname: Alice
  ```

* **Terminal 3 (Client Bob tham gia):**
  ```bash
  cd /home/vite/Documents/Mon_hoc/MMT/Socket_Programming/LANCHAT_fundamental/client_server_demo
  python3 client.py
  # Nhấn Enter cho IP và Port mặc định
  # Nhập Nickname: Bob
  ```

* **Trải nghiệm:** Gõ một câu bất kỳ từ Alice (`"Chào cả phòng!"`), Server sẽ nhận dữ liệu và broadcast ngay lập tức sang màn hình của Bob.

---

### 2.2. Kịch bản 2: Thử nghiệm mạng ngang hàng P2P LAN Chat (`p2p_chat.py`)
*Mô hình phân tán: Mỗi node tự tìm thấy nhau qua UDP và chat trực tiếp qua TCP mà không cần máy chủ.*

Mở **2 cửa sổ Terminal**:

* **Terminal 1 (Node Alice):**
  ```bash
  cd /home/vite/Documents/Mon_hoc/MMT/Socket_Programming/LANCHAT_fundamental
  python3 p2p_chat.py
  # Nhập tên hiển thị: Alice
  ```

* **Terminal 2 (Node Bob):**
  ```bash
  cd /home/vite/Documents/Mon_hoc/MMT/Socket_Programming/LANCHAT_fundamental
  python3 p2p_chat.py
  # Nhập tên hiển thị: Bob
  ```

* **Trải nghiệm giao tiếp P2P:**
  1. Tại màn hình Alice, gõ lệnh:
     ```text
     /list
     ```
     *Hệ thống quét bảng danh bạ và hiển thị Bob kèm địa chỉ IP và Port TCP của Bob (nhờ gói UDP Broadcast phát hiện tự động).*
  2. Alice chủ động mở kết nối TCP để trò chuyện riêng với Bob:
     ```text
     /chat Bob
     ```
  3. Gõ tin nhắn văn bản và nhấn `Enter`:
     ```text
     Xin chào Bob, đây là kết nối TCP trực tiếp giữa 2 máy!
     ```
  4. Quan sát màn hình Bob: Dòng tin nhắn xuất hiện tức thì kèm tên người gửi. Bob có thể gõ phản hồi lại ngay lập tức.
  5. Gõ `/help` để xem danh sách lệnh hoặc `/quit` để thoát an toàn.

---

### 2.3. Kịch bản 3: Chạy bộ kiểm thử tích hợp tự động (`test_fundamental.py`)
Kiểm tra tính đúng đắn toàn diện của mã nguồn chỉ bằng 1 câu lệnh:
```bash
cd /home/vite/Documents/Mon_hoc/MMT/Socket_Programming/LANCHAT_fundamental
python3 test_fundamental.py
```
*Script sẽ tự động khởi động 2 tiến trình ngầm Alice và Bob, kích hoạt luồng phát sóng UDP, xác nhận danh bạ tìm thấy nhau, mở socket TCP chat 2 chiều và báo cáo kết quả `PASS 100%`.*

---

## 3. GIẢI PHÃU KỸ THUẬT THEO PHƯƠNG PHÁP FEYNMAN

### 3.1. Socket thực sự là gì dưới góc độ Hệ điều hành (Kernel)?
* **Ảo tưởng học vẹt:** Nghĩ rằng socket là một "sợi cáp vật lý ảo" hoặc "một biến số lưu trữ văn bản trong RAM chương trình".
* **Bản chất vật lý sơ cấp:**  
  Một Socket là một **Con Trỏ Điều Khiển (File Descriptor / Handle)** do Kernel cấp phát. Khi bạn gọi `s = socket(AF_INET, SOCK_STREAM)`, hệ điều hành sẽ cấp phát ngay **2 hàng đợi bộ nhớ trong RAM (Kernel Buffers)**:
  1. **Kernel Send Buffer (Bộ đệm gửi):** Khi bạn gọi `sendall(b"Hello")`, lệnh này **chưa hề phát sóng điện ra dây cáp ngay!** Nó chỉ copy chuỗi byte `"Hello"` từ bộ nhớ của chương trình bạn (User Space) vào Kernel Send Buffer. Nhân hệ điều hành sẽ tự quyết định thời điểm đẩy các byte này ra card mạng (NIC).
  2. **Kernel Receive Buffer (Bộ đệm nhận):** Khi card mạng nhận được xung điện/sóng radio từ đối phương, nó kiểm tra mã băm CRC và ném các byte vào Kernel Receive Buffer. Khi bạn gọi `recv(1024)`, bạn chỉ đang thò tay vào hàng đợi này để vớt dữ liệu lên.

---

### 3.2. Tại sao bắt buộc phải `encode('utf-8')` và `decode('utf-8')`?
* **Bản chất vật lý:** Dây cáp mạng đồng chỉ dẫn dòng electron; cáp quang chỉ dẫn hạt photon ánh sáng; sóng Wi-Fi chỉ là điện từ trường dao động.  
  Tầng vật lý và tầng giao vận của máy tính **hoàn toàn không có khái niệm về "chữ cái", "tiếng Việt" hay "chuỗi String"**. Chúng chỉ vận chuyển các **dãy bit nhị phân (0 và 1) được gom thành các byte (8 bits)**.
* **Nguyên lý:**
  * `.encode('utf-8')`: Chuyển đổi các ký tự Unicode của bạn thành dãy byte nhị phân để có thể nhét vào Socket.
  * `.decode('utf-8')`: Phía nhận nhặt các byte thô từ Socket lên và tra bảng mã để dịch ngược lại thành chữ cái hiển thị lên màn hình.

---

### 3.3. Hiện tượng Blocking I/O và Thí nghiệm chiếc điện thoại bàn (Tại sao cần Multithreading?)
* **Vấn đề bản chất:**  
  Các hàm socket như `accept()`, `recv()`, `recvfrom()` và hàm bàn phím `input()` đều là **Hàm Chặn (Blocking Calls)**.  
  Khi chương trình gọi một hàm blocking, luồng thực thi của CPU sẽ **ngủ đông ngay tại dòng lệnh đó**, nhường CPU cho ứng dụng khác và kiên nhẫn chờ đến khi có sự kiện I/O xảy ra (có dữ liệu từ mạng hoặc có người nhấn Enter).
* **Nghịch lý nếu chỉ dùng 1 luồng duy nhất:**  
  Hãy tưởng tượng một người sống một mình trong nhà có 1 chiếc điện thoại bàn (`recv`) và 1 cuốn sách cần viết (`input`):
  * Nếu người đó ngồi cắm cúi viết sách (`input`), họ sẽ không thể nhấc máy nghe điện thoại.
  * Nếu người đó ngồi canh bên chiếc điện thoại (`recv`), họ không thể viết tiếp cuốn sách!
  * Kết quả: Khi chương trình đang đứng chờ bạn gõ phím `input()`, nếu bạn bè từ xa gửi tin nhắn chat đến, hàm `recv()` không được gọi -> tin nhắn bị giam giữ trong Kernel Buffer, màn hình không thể hiện tin nhắn mới!
* **Giải pháp Đa luồng (Multithreading):**  
  Tạo thêm một người phụ việc (`threading.Thread`):
  * **Luồng phụ (Receiver Thread):** Chuyên túc trực bên chiếc điện thoại socket gọi `recv()`. Khi có tin nhắn đến, lập tức in ra màn hình.
  * **Luồng chính (Main Thread):** Chuyên ngồi đọc bàn phím `input()`. Người dùng gõ xong câu nào thì lập tức dùng `sendall()` gửi đi câu đó.
  Hai luồng vận hành song song độc lập, loại bỏ hoàn toàn hiện tượng đóng băng ứng dụng!

---

### 3.4. Dấu hiệu nhận biết đối phương ngắt kết nối trong TCP (Bản chất gói FIN)
* Trong mã nguồn của cả `server.py` và `p2p_chat.py`, bạn sẽ luôn thấy đoạn code kinh điển:
  ```python
  data = sock.recv(1024)
  if not data:
      print("Đối phương đã ngắt kết nối!")
      break
  ```
* **Tại sao `not data` (dữ liệu rỗng `b''`) lại tương đương với ngắt kết nối?**
  * Trong giao thức TCP, khi đối phương gọi lệnh `sock.close()`, card mạng của họ sẽ phát ra một gói tin điều khiển đặc biệt mang cờ **FIN (Finish)** để thực hiện bắt tay 4 bước kết thúc kết nối.
  * Khi hệ điều hành bên nhận nhận được cờ FIN, nó hiểu rằng: *"Luồng dữ liệu này đã kết thúc, sẽ không còn byte nào được gửi thêm nữa"*.
  * Hệ điều hành đánh dấu ký hiệu kết thúc tệp (**EOF - End of File**) vào Receive Buffer. Lúc này, hàm `recv()` lập tức được đánh thức và trả về **chuỗi 0 bytes (`b''`)**. Đây là quy ước chuẩn mực quốc tế của kiến trúc POSIX Socket để báo hiệu kết nối đã đóng an toàn.

---

## 4. DIỄN GIẢI CHUYÊN SÂU: BẢN CHẤT CỦA PORT & TẠI SAO PHẢI DÙNG CẢ 2 PORT (TCP VÀ UDP)?

Trong ứng dụng `p2p_chat.py`, khi khởi chạy bạn sẽ thấy 2 dòng cấu hình:
```text
[*] TCP Port: 45541 (hoặc do bạn chỉ định)
[*] UDP Discovery Port: 50005
```

Rất nhiều sinh viên thắc mắc:  
> *"Tại sao cùng là chat mà ứng dụng lại phải dùng tới 2 Port? Tại sao không dùng 1 Port duy nhất cho tiện?"*

Hãy cùng bóc tách bản chất của câu hỏi này qua 3 tầng phân tích:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CARD MẠNG VẬT LÝ (NIC)                                            │
│                         Tiếp nhận mọi tín hiệu sóng / xung điện từ mạng LAN                             │
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
│ Port 50005 ──► P2PChatNode (Luồng UDP Discovery)    │ │ Port 45541 ──► P2PChatNode (Luồng TCP Server)   │
└─────────────────────────────────────────────────────┘ └─────────────────────────────────────────────────┘
```

### 4.1. Bản chất của "Port" trong nhân Hệ điều hành
1. **Địa chỉ IP đại diện cho Ngôi nhà (Máy tính):** Giúp bưu tá mạng đưa gói tin đến đúng thiết bị.
2. **Số hiệu Cổng (Port) đại diện cho Căn phòng trong nhà (Tiến trình phần mềm):**  
   Một chiếc máy tính cùng lúc chạy web, game, nghe nhạc, chat. Khi một gói tin đến nơi, làm sao hệ điều hành biết gói tin này là của chương trình chat hay của trình duyệt web?  
   **Port chính là số hòm thư phân loại (Demultiplexing Key) 16-bit** nằm trong Header tầng Giao vận.
3. **Cổng TCP và Cổng UDP là 2 bảng hoàn toàn độc lập:**  
   Hệ điều hành quản lý 2 bảng danh bạ băm độc lập: bảng cho TCP và bảng cho UDP. Do đó, port UDP `50005` và port TCP `45541` (hoặc kể cả nếu bạn đặt trùng số `50005`) không bao giờ xung đột hay đè lên nhau, vì số nhận diện giao thức ở tầng IP (TCP là 6, UDP là 17) đã phân luồng chúng từ trước.

---

### 4.2. Nghịch lý nếu "Chỉ dùng một giao thức duy nhất"

Hãy cùng thực hiện 2 thí nghiệm tư duy để thấy tại sao hệ thống sẽ bế tắc nếu bạn chỉ dùng 1 giao thức:

#### Kịch bản A: Nếu cố tình CHỈ DÙNG TCP cho cả việc tìm kiếm lẫn chat
* TCP là giao thức **hướng kết nối điểm - điểm (Point-to-Point, 1-1)**. Muốn nói chuyện bằng TCP, bạn bắt buộc phải gọi `connect(IP_đích, Port_đích)`.
* **TCP KHÔNG BAO GIỜ hỗ trợ Broadcast (phát thanh quảng bá toàn mạng).** Bạn không thể gửi một gói tin TCP SYN tới địa chỉ toàn mạng `255.255.255.255`.
* **Nghịch lý "Con gà và quả trứng":** Bạn vừa mang laptop đến phòng lab. Bạn muốn chat với Alice. Nhưng bạn chưa hề biết IP của Alice là gì, Alice đang mở cổng TCP nào. Để tìm Alice bằng TCP, chương trình của bạn buộc phải quét (Scan) toàn bộ 254 địa chỉ IP trong phòng lab, mỗi IP thử gõ cửa hàng trăm cổng! Việc này vừa làm tê liệt mạng Wi-Fi, vừa mất 5–10 phút chỉ để tìm xem ai đang online.

#### Kịch bản B: Nếu cố tình CHỈ DÙNG UDP cho cả việc tìm kiếm lẫn chat
* UDP là giao thức **bưu thiếp không tin cậy (Unreliable Datagram)**: Cứ ném gói tin đi mà không cần biết đối phương có nhận được hay không, không có giấy báo nhận (ACK), không có cơ chế truyền lại khi rơi rớt gói.
* Nếu bạn chat bằng UDP broadcast trên cổng 50005:
  1. **Mất tính riêng tư:** Mọi tin nhắn tâm sự riêng tư của bạn với Alice đều bị loa phóng thanh phát cho cả lớp cùng nghe.
  2. **Rơi rớt chữ:** Mạng Wi-Fi chập chờn sẽ làm rơi gói tin. Một câu nói quan trọng có thể bị mất chữ mà hai bên không hề hay biết!

---

### 4.3. Sự kết hợp hoàn hảo: "Đài phát thanh UDP + Đường dây nóng TCP"

Chính vì vậy, kiến trúc mạng chuẩn mực phân định ranh giới rạch ròi:

```
┌───────────────────────────────────────────┬────────────────────────────────────────────┐
│         UDP CỔNG 50005 (CỐ ĐỊNH CHUNG)    │         TCP CỔNG RIÊNG (VD: 45541)         │
│          "ĐÀI PHÁT THANH TOÀN LÀNG"       │            "ĐƯỜNG DÂY NÓNG RIÊNG TƯ"       │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Nhiệm vụ: Khám phá bạn bè trong mạng LAN│ • Nhiệm vụ: Trò chuyện trực tiếp 1 - 1     │
│ • Cơ chế: Broadcast (1 phát tới tất cả)   │ • Cơ chế: Unicast Point-to-Point (1 - 1)   │
│ • Tính chất: Nhẹ, không cần bắt tay       │ • Tính chất: Tin cậy, bảo đảm đúng thứ tự  │
│ • Nội dung: "Tôi là Alice, số TCP là 45541"│ • Nội dung: Tin nhắn trò chuyện thực tế    │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

1. **Port UDP 50005 (Tần số radio chung của cả phòng):**  
   Mọi máy đều mở chung cổng UDP `50005`. Cứ 3 giây, máy của Alice lại phát 1 mẩu tin ngắn: `HELLO|Alice|45541`. Bob đang bật radio cổng 50005 lập tức nhặt được mẩu tin này và ghi vào danh bạ: *"Alice đang online, số điện thoại TCP riêng của Alice là 45541"*.
2. **Port TCP 45541 (Đường dây điện thoại riêng kéo vào phòng Alice):**  
   Khi Bob muốn chat với Alice, Bob không phát loa nữa. Bob nhấc máy gọi thẳng vào cổng TCP `45541` của Alice. Một đường ống dẫn nước tin cậy, bảo mật 1-1 được thiết lập, dữ liệu truyền đi có xác nhận ACK, bảo đảm không bao giờ mất một ký tự nào!

---

## 5. SO SÁNH TOÀN DIỆN: CLIENT-SERVER VS PEER-TO-PEER (P2P)

| Tiêu chí | Mô hình Client - Server (`client_server_demo/`) | Mô hình Peer-to-Peer (`p2p_chat.py`) |
| :--- | :--- | :--- |
| **Kiến trúc mạng (Topology)** | **Tập trung hình sao (Star):** Máy chủ ở trung tâm, mọi client đều hướng về server. | **Phi tập trung dạng lưới (Mesh):** Các node kết nối trực tiếp với nhau theo nhu cầu. |
| **Điểm sụp đổ đơn lẻ (SPOF)** | **Có rủi ro cao.** Nếu Server mất điện hoặc bị tấn công sập, toàn bộ phòng chat tê liệt. | **Không có.** Nếu một node tắt máy, toàn bộ các node còn lại vẫn tìm kiếm và trò chuyện bình thường. |
| **Gánh nặng băng thông** | **Dồn toàn bộ vào Server.** Nếu có 100 client chat, server phải nhân bản và gửi 100 lần lưu lượng. | **Phân tán đều.** Băng thông được chia sẻ trực tiếp giữa các cặp peer nói chuyện với nhau. |
| **Cơ chế phát hiện nhau** | Tĩnh. Client bắt buộc phải được cấu hình sẵn địa chỉ IP và Port cố định của Server. | Động. Tự động tìm thấy nhau qua gói tin **UDP Broadcast** mà không cần cấu hình trước. |
| **Độ trễ truyền tin (Latency)** | Trễ gấp đôi: Client A gửi lên Server -> Server xử lý rồi gửi xuống Client B (2 chặng). | Trễ tối thiểu: Đi trực tiếp một chặng từ Peer A sang Peer B (1 chặng TCP). |
| **Độ phức tạp lập trình** | Đơn giản hơn: Client chỉ việc mở 1 socket kết nối tới Server. | Cao hơn: Mỗi máy vừa phải chạy Server đón khách, vừa phải chạy Client đi gọi bạn bè. |

---

## 6. BẢNG TRA CỨU CÁC HÀM SOCKET CỐT LÕI (CORE SOCKET API)

| Tên hàm Socket | Giao thức | Ý nghĩa & Hành vi bản chất tầng Giao vận |
| :--- | :--- | :--- |
| `socket(family, type)` | Cả TCP và UDP | Tạo điểm cuối truyền thông (endpoint). `AF_INET` chỉ định IPv4; `SOCK_STREAM` chọn TCP; `SOCK_DGRAM` chọn UDP. |
| `bind((ip, port))` | Cả TCP và UDP | Gắn socket với một cổng cụ thể trên máy. Đặt IP là `''` hoặc `'0.0.0.0'` để lắng nghe trên mọi card mạng. |
| `listen(backlog)` | Chỉ TCP Server | Chuyển socket sang trạng thái thụ động sẵn sàng đón khách. `backlog` là độ dài hàng đợi kết nối đang chờ duyệt. |
| `accept()` | Chỉ TCP Server | **Blocking Call.** Tạm dừng luồng chờ client kết nối tới, hoàn tất bắt tay 3 bước và trả về socket mới `(conn, addr)`. |
| `connect((ip, port))` | Chỉ TCP Client | Khởi tạo bắt tay 3 bước TCP (SYN -> SYN-ACK -> ACK) để mở kênh truyền tới máy chủ/peer khác. |
| `sendall(bytes)` | Chỉ TCP | Đẩy toàn bộ chuỗi byte vào Kernel Send Buffer. Đảm bảo toàn vẹn hơn hàm `send()` thô khi dữ liệu dài. |
| `recv(bufsize)` | Chỉ TCP | **Blocking Call.** Múc tối đa `bufsize` byte từ Kernel Receive Buffer. **Trả về `b''` khi đối phương ngắt kết nối.** |
| `sendto(data, addr)` | Chỉ UDP | Bắn một gói datagram độc lập tới địa chỉ đích mà không cần thiết lập kết nối trước. Hỗ trợ địa chỉ Broadcast. |
| `recvfrom(bufsize)` | Chỉ UDP | **Blocking Call.** Chờ và nhặt 1 gói datagram kèm địa chỉ IP/port của bên gửi `(data, (ip, port))`. |
| `close()` | Cả TCP và UDP | Thu hồi tài nguyên socket. Đối với TCP, kích hoạt quá trình bắt tay 4 bước kết thúc kết nối (FIN-ACK). |
| `setsockopt(...)` | Cả TCP và UDP | Bật cờ cấu hình socket: `SO_REUSEADDR` (tái dùng cổng lập tức), `SO_BROADCAST` (cho phép bắn gói quảng bá). |

---

## 7. HƯỚNG DẪN BẮT GÓI TIN WIRESHARK LÀM BÁO CÁO MÔN HỌC

Để bài báo cáo môn học đạt điểm xuất sắc, bạn hãy mở Wireshark và thực hiện chụp 3 minh chứng cốt lõi sau:

### 7.1. Bắt gói tin UDP Broadcast Discovery
* **Bộ lọc Wireshark (Display Filter):**
  ```wireshark
  udp.port == 50005
  ```
* **Hiện tượng cần ghi lại:**
  * Địa chỉ IP đích là địa chỉ quảng bá: `255.255.255.255` (hoặc `127.255.255.255` khi test loopback).
  * Chu kỳ phát sóng đều đặn mỗi 3 giây.
  * Phần Data hiển thị chuỗi ASCII: `HELLO|Alice|45541`.

### 7.2. Bắt gói tin Bắt tay 3 bước TCP (3-Way Handshake)
* **Bộ lọc Wireshark:**
  ```wireshark
  tcp.flags.syn == 1
  ```
* **Hiện tượng cần ghi lại:**
  * Gói 1: Alice gửi tới Bob mang cờ `[SYN]`.
  * Gói 2: Bob gửi lại Alice mang cờ `[SYN, ACK]`.
  * Gói 3: Alice xác nhận mang cờ `[ACK]`.
  * Giải thích trong báo cáo: Quá trình bắt tay 3 bước giúp hai bên thỏa thuận số thứ tự gói tin khởi tạo (Initial Sequence Number - ISN) và cấp phát bộ đệm truyền nhận an toàn trước khi truyền dữ liệu.

### 7.3. Theo dõi luồng TCP Stream
* Nhấp chuột phải vào gói tin TCP PSH/ACK mang nội dung chat -> Chọn **Follow** -> **TCP Stream**.
* Bạn sẽ thấy toàn bộ hội thoại:
  ```text
  CONNECT|Alice
  Xin chào Bob! Tôi là Alice.
  Chào Alice! Bob đã nhận được tin của bạn.
  ```

---

## 8. BỘ CÂU HỎI CHẨN ĐOÁN NGỘ NHẬN (FEYNMAN DIAGNOSTIC PROBES)

#### Câu hỏi 1: Tại sao trong `p2p_chat.py` khi tạo TCP Server ta lại bind vào `tcp_port = 0`?
> **Góc nhìn bản chất Feynman:**  
> Trong Socket API của hệ điều hành, số cổng `0` là một **Mã Đặc Biệt (Wildcard Port)**!  
> Khi bạn gọi `bind(('0.0.0.0', 0))`, bạn đang ra lệnh cho nhân hệ điều hành: *"Hãy tự động tìm một cổng TCP còn rảnh rỗi trong dải Ephemeral Ports (thường từ 32768 đến 60999) và cấp phát cho tôi!"*.  
> Điều này cực kỳ thông minh: Khi bạn mở 5 cửa sổ terminal trên cùng 1 máy tính để test P2P, không có cửa sổ nào bị trùng cổng TCP, không bao giờ bị lỗi `Address already in use`! Sau đó, hàm `getsockname()[1]` sẽ lấy ra số cổng thực tế mà hệ điều hành vừa cấp để đóng gói vào bản tin UDP `HELLO` cho bạn bè biết.

#### Câu hỏi 2: Nếu một gói tin UDP HELLO bị rơi trên đường truyền Wi-Fi thì sao?
> **Góc nhìn bản chất Feynman:**  
> **Hoàn toàn không sao cả!**  
> Bản chất của UDP là nhẹ và không có bảo đảm. Nhưng kiến trúc của chúng ta đã tính trước điều đó: Cứ 3 giây một gói HELLO mới lại được phát đi. Đồng thời, thời gian timeout để coi một node offline là tận **10 giây**.  
> Điều này có nghĩa là một người chỉ bị coi là offline nếu mạng làm rơi liên tiếp **3 gói tin HELLO**! Việc chấp nhận mất gói tin ngẫu nhiên giúp hệ thống vận hành cực nhẹ mà không tốn công sức thiết lập các cơ chế ACK phức tạp.

---

*Tài liệu tóm lược toàn diện được biên soạn theo chuẩn sư phạm tư duy bản chất Richard Feynman.*
