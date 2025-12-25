import os
import requests
from io import BytesIO
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

TOKEN = os.environ.get("TOKEN")
CLIPDROP_API_KEY = os.environ.get("CLIPDROP_API_KEY")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    
    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"✅ Health server running on :{port}")
    server.serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "لینک پست یا ریل اینستاگرام رو بفرست\n"
        "تصاویر رو بدون متن برات می‌فرستم ✅"
    )


def extract_shortcode(url: str):
    url = url.split("?")[0].strip("/")
    patterns = [
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_instagram_images(shortcode: str):
    """دریافت تصاویر با embed API"""
    try:
        url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code == 200:
            pattern = r'"display_url":"(https://[^"]+)"'
            matches = re.findall(pattern, resp.text)
            if matches:
                images = [m.encode().decode('unicode_escape') for m in matches]
                return list(set(images))
    except:
        pass
    
    return []


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    msg = await update.message.reply_text("⏳ در حال پردازش...")

    shortcode = extract_shortcode(url)
    if not shortcode:
        await msg.edit_text("❌ لینک معتبر نیست")
        return

    try:
        images = get_instagram_images(shortcode)
        
        if not images:
            await msg.edit_text("❌ تصویری پیدا نشد (ممکنه خصوصی باشه)")
            return

        total = len(images)
        await msg.edit_text(f"✅ {total} عکس پیدا شد، در حال پردازش...")

        ok = 0
        for i, img_url in enumerate(images, 1):
            try:
                img_data = requests.get(img_url, timeout=30).content
                
                # ارسال به Clipdrop
                api_resp = requests.post(
                    "https://clipdrop-api.co/remove-text/v1",
                    headers={"x-api-key": CLIPDROP_API_KEY},
                    files={"image_file": ("img.jpg", img_data, "image/jpeg")},
                    timeout=60,
                )

                if api_resp.ok:
                    cleaned = BytesIO(api_resp.content)
                    await update.message.reply_photo(cleaned, caption=f"✅ {i}/{total}")
                    ok += 1
                else:
                    await update.message.reply_photo(img_url, caption=f"⚠️ {i}/{total} خام")
            except:
                pass

        await msg.edit_text(f"🎉 تمام! {ok}/{total} موفق")

    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)[:100]}")


def main():
    # شروع Health Server
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    print("✅ Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
