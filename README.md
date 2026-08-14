# Discord Order Management Bot

Bot Discord quản lý đơn hàng đầy đủ vòng đời: Bảng giá → Khách chọn sản phẩm →
Tạo đơn → Staff nhận đơn → Đang xử lý → Hoàn thành → Bot DM khách hàng.

## Cấu trúc dự án

```
discord_order_bot/
├── main.py                  # Điểm khởi động bot
├── requirements.txt
├── .env.example
├── config/settings.py       # Nạp biến môi trường & đường dẫn
├── commands/
│   ├── setup.py             # /setup
│   ├── price.py             # /price, /price-admin add|edit|remove|list
│   └── order.py             # Logic đơn hàng, nút bấm, modal, /order-lookup
├── events/
│   ├── on_ready.py
│   └── on_interaction.py    # Router xử lý mọi nút bấm / menu chọn
├── database/
│   ├── database.py          # Lớp Database (aiosqlite)
│   └── models.py            # Hằng số, dataclass, schema SQL
├── products/prices.py       # Toàn bộ bảng giá khởi tạo
├── utils/
│   ├── embeds.py
│   ├── dm.py
│   └── logger.py
└── data/orders.db           # Tự tạo khi chạy bot lần đầu
```

## 1. Cài đặt dependency

```bash
cd discord_order_bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Cấu hình token

```bash
cp .env.example .env
```

Mở `.env` và điền:

```
DISCORD_TOKEN=token_bot_cua_ban
DEV_GUILD_ID=                  # tùy chọn — xem ghi chú bên dưới
```

Lấy token tại **Discord Developer Portal → Application → Bot → Reset/Copy
Token**. Trong tab **Bot**, bật **Server Members Intent** nếu bạn dự định mở
rộng bot sau này (bản hiện tại không bắt buộc).

> `DEV_GUILD_ID`: nếu điền ID server test, slash command sẽ đồng bộ **ngay
> lập tức** trong server đó. Để trống thì bot đồng bộ global — Discord có thể
> mất tới ~1 giờ để command hiện ra ở mọi server.

## 3. Chạy bot

```bash
python main.py
```

Lần chạy đầu tiên, bot sẽ tự tạo `data/orders.db`, tạo toàn bộ bảng, và nạp
sẵn bảng giá từ `products/prices.py`.

## 4. Dùng lệnh `/setup`

Chạy `/setup` trong server (cần quyền **Administrator**) và điền:

| Tham số | Ý nghĩa |
|---|---|
| `order_channel` | Nơi đơn hàng được đăng để Staff xử lý |
| `log_channel` | Nơi bot ghi log mọi hoạt động |
| `price_channel` | Kênh dành cho bảng giá |
| `staff_role` | Role được phép Nhận đơn / Hoàn thành / Hủy đơn |
| `admin_role` | Role được phép quản lý bảng giá (`/price-admin`) |
| `ticket_channel` | Kênh khách tạo ticket (dùng cho báo giá "búc lẻ") |

Cấu hình lưu vào database — chạy lại `/setup` bất cứ lúc nào để cập nhật,
không cần sửa code hay khởi động lại bot.

## 5. Dùng lệnh `/price`

- Chạy `/price` trong kênh bảng giá (hoặc bất kỳ kênh nào) để đăng bảng giá
  với 5 nút: **Deca0 Login**, **Deca0R/NPL/Frames**, **Búc Sivi**, **Lưu ý**,
  **Thanh toán**.
- Quản lý sản phẩm (chỉ Admin, không cần sửa source code):
  - `/price-admin add` — thêm sản phẩm
  - `/price-admin edit` — sửa tên/giá/ghi chú/ẩn-hiện
  - `/price-admin remove` — xóa sản phẩm
  - `/price-admin list` — xem toàn bộ sản phẩm (kể cả đã ẩn)

> **Ghi chú kỹ thuật:** Discord không cho một slash command vừa gọi trực
> tiếp (`/price`) vừa là group chứa subcommand (`/price add`) cùng lúc, nên
> phần quản lý được tách sang `/price-admin` thay vì `/price add`.

## 6. Tạo & xử lý đơn hàng

**Khách hàng:**
1. Bấm một trong 3 nút danh mục trên bảng giá → chọn sản phẩm từ menu.
2. Với **Deca0 Login**: menu có sẵn 2 lựa chọn mỗi sản phẩm (có/không
   `sw_naichobs`, +9.000đ) — chọn xong, đơn được tạo ngay.
3. Với **Búc Sivi** (gói cố định): một form hiện ra để nhập Link server.
   Chọn "Búc lẻ" để được hướng dẫn tạo ticket báo giá riêng.
4. Với **Deca0R/NPL/Frames**: đơn được tạo ngay, không cần thêm thông tin.
5. Bot tạo mã đơn dạng `ORDER-0001`, đăng Embed trạng thái vào kênh đơn hàng,
   và gửi xác nhận riêng cho khách.

**Staff (cần role Staff/Admin, cấu hình qua `/setup`):**
1. **🔄 Nhận đơn** — chuyển trạng thái sang *Đang xử lý*, gán Staff xử lý.
2. **✅ Hoàn thành** — với sản phẩm dạng Link, bot hiện form yêu cầu nhập
   Link trước khi hoàn tất; các loại khác hoàn tất ngay. Bot tự động DM
   khách hàng kèm thông tin đơn (và Link nếu có), đồng thời đánh dấu
   `dm_notified` để **không bao giờ gửi DM trùng lặp**, kể cả khi bot khởi
   động lại.
3. **❌ Hủy đơn** — hiện màn hình xác nhận, sau đó yêu cầu nhập lý do hủy.
   Bot ghi lý do, log lại, và DM thông báo cho khách.

Mọi thao tác (tạo đơn, nhận đơn, hoàn thành, hủy, gửi/lỗi DM, đổi giá, đổi
cấu hình) đều được ghi vào kênh Log đã cấu hình.

## Bảo mật

- Token chỉ đọc từ biến môi trường (`.env`), không hard-code, không in ra
  console, không lưu vào database.
- Bot **không** thu thập hay lưu tài khoản/mật khẩu/2FA/backup code của
  khách — với đơn Deca0 Login, khách được hướng dẫn gửi thông tin đó trực
  tiếp cho Staff qua DM sau khi đơn được nhận, ngoài phạm vi xử lý của bot.
- Dữ liệu đơn hàng lưu SQLite (`data/orders.db`), tồn tại qua các lần khởi
  động lại bot.
