"""
Cấu hình chung cho bot.

Mọi giá trị nhạy cảm (token) được nạp từ biến môi trường / file .env,
KHÔNG bao giờ hard-code trong source code.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Token & thông tin nhạy cảm — luôn lấy từ biến môi trường
# ---------------------------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

# Guild ID dùng để đồng bộ slash command NGAY LẬP TỨC khi phát triển (tùy chọn).
# Để trống -> đồng bộ global (Discord có thể mất tới 1 giờ để cập nhật toàn bộ).
_dev_guild_raw = os.getenv("DEV_GUILD_ID", "").strip()
DEV_GUILD_ID = int(_dev_guild_raw) if _dev_guild_raw.isdigit() else None

# ---------------------------------------------------------------------------
# Đường dẫn
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "orders.db")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Tự tạo các thư mục cần thiết nếu chưa tồn tại
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Hằng số hiển thị
# ---------------------------------------------------------------------------
BOT_NAME = "Order Management Bot"
EMBED_COLOR = 0x2ECC71
EMBED_COLOR_INFO = 0x3498DB
