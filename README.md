Currently Only Support Vietnamese | Hiện tại chỉ hỗ trợ Tiếng Việt

ĐỂ KHỞI ĐỘNG SERVER:
- Chạy server.py
- Chạy lệnh "ngrok http 5000" qua Terminal

--------------------------------------------------

TỔNG QUAN VỀ GAME MONOPOLY

1. Khởi tạo & Phòng chờ (Lobby)
- Hỗ trợ tối đa 6 người chơi cùng tham gia qua mạng LAN nội bộ.
- Màn hình Lobby cho phép người chơi tự điền tên cá nhân và chọn màu sắc đại diện duy nhất.
- Quyền Chủ phòng (Host) tự động cấp cho người truy cập đầu tiên để thiết lập thời gian ván đấu và kích hoạt bắt đầu.

2. Hệ thống Tiền tệ & Ngân hàng
- Vốn khởi điểm cấp cho mỗi người chơi là 15.000.000 VNĐ.
- Lối chơi hoàn toàn không dùng tiền mặt với mọi giao dịch cộng/trừ được hệ thống tự động hóa.
- Tính năng Public Ledger công khai số dư và tài sản bất động sản (hiển thị dạng ô màu thu gọn) của tất cả người chơi trên màn hình.

3. Hệ thống Bất Động Sản & Xây dựng
- Luật Bộ Màu bắt buộc người chơi sở hữu đủ các mảnh đất cùng màu mới được phép tiến hành xây nhà.
- Luật Xây Đồng Đều (Even Build) ép buộc người chơi xây dàn trải trên các ô cùng màu với độ chênh lệch không quá 1.
- Giới hạn tài nguyên toàn bàn cờ được thiết lập ở mức 32 Nhà và 12 Khách sạn.
- Cơ chế Cầm cố (Mortgage) cho phép thu về 50% giá mua gốc, nhưng bắt buộc bán hết nhà trên mảnh đất đó trước.
- Việc chuộc lại đất đã cầm cố sẽ tốn phí bằng số tiền đã nhận cộng thêm 10% lãi suất.
- Phí của 4 trạm di chuyển dao động từ 250.000 VNĐ đến 2.000.000 VNĐ tùy thuộc vào số lượng trạm chủ đất sở hữu.
- Phí của 2 khu tiện ích được tính bằng tổng 2 xúc xắc nhân với 40.000 VNĐ (nếu có 1 tiện ích) hoặc 100.000 VNĐ (nếu có 2 tiện ích).

4. Tương tác & Giao dịch
- Sàn Đấu giá bắt buộc kích hoạt cho toàn bộ người chơi khi có một người từ chối mua mảnh đất vô chủ.
- Cửa sổ Vote cho phép chọn hình thức đấu giá: Trả giá tự do liên tục (Live Bidding) hoặc Trả giá mù giấu kín (Blind Bidding).
- Tính năng Trao đổi (Trade) sẽ tạm dừng ván game để hai người chơi đàm phán đổi đất hoặc tiền cho đến khi chốt giao dịch.

5. Di chuyển & Hình phạt
- Tính năng Xúc xắc Tốc độ được tùy chọn Bật/Tắt lúc tạo phòng để thêm 1 viên xúc xắc đỏ quyết định các bước đi đặc biệt (Cộng dồn, Xe buýt, Mr. Monopoly).
- Người chơi phải vào tù khi đổ ra số đôi 3 lần liên tiếp hoặc giẫm trúng ô Go to Jail.
- Cách thoát khỏi nhà tù bao gồm: Nộp 500.000 VNĐ ngay đầu lượt, dùng thẻ "Ra tù miễn phí", hoặc tung xúc xắc thử vận may tìm số đôi (tối đa 3 lần).

6. Thời gian & Phân định Thắng Thua
- Đồng hồ đếm ngược được Chủ phòng thiết lập tính bằng phút và hiển thị liên tục trên màn hình của tất cả người chơi.
- Bảng xếp hạng (Leaderboard) tự động kích hoạt khi hết giờ hoặc khi chỉ còn một người chưa phá sản.
- Hệ thống tính Tổng Tài Sản (Net Worth) cộng dồn tiền mặt, 100% giá đất gốc, 50% giá đất cầm cố và 100% chi phí xây nhà để tìm ra người chiến thắng.
