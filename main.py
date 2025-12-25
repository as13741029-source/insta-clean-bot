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
        self.wfile.write(b"Bot is running!")
    
    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"✅ Health server on port {port}")
    server.serve_forever()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "لینک پست یا ریل اینستاگرام رو بفرست.\n"
        "تصاویر رو بدون متن و استیکر برات می‌فرستم ✅\n\n"
        "فقط پست‌های عمومی کار می‌کنه"
    )


def extract_shortcode(url: str):
    url = url.split("?")[0].strip("/")
    
    patterns = [
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/tv/([A-Za-z0-9_-]+)',
        r'instagr\.am/p/([A-Za-z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def get_instagram_images(shortcode: str):
    try:
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = requests.get(embed_url, timeout=15)
        
        if resp.status_code == 200:
            img_pattern = r'"display_url":"(https://[^"]+)"'
            matches = re.findall(img_pattern, resp.text)
            
            if matches:
                images = [m.encode().decode('unicode_escape') for m in matches]
                return list(set(images))
    except:
        pass
    
    try:
        media_url = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
        resp = requests.head(media_url, allow_redirects=True, timeout=10)
        
        if resp.status_code == 200:
            return [resp.url]
    except:
        pass
    
    return []


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال دریافت پست...")

    shortcode = extract_shortcode(url)
    if not shortcode:
        await status_msg.edit_text(
            "❌ لینک معتبر نیست\n\n"
            "مثال:\nhttps://www.instagram.com/p/ABC123/"
        )
        return

    try:
        image_urls = get_instagram_images(shortcode)
        
        if not image_urls:
            await status_msg.edit_text(
                "❌ نتونستم تصاویر رو پیدا کنم\n\n"
                "ممکنه پست خصوصی یا حذف شده باشه"
            )
            return

        total = len(image_urls)
        await status_msg.edit_text(
            f"✅ {total} تا عکس پیدا شد!\n"
            f"🎨 در حال حذف متن‌ها..."
        )

        success = 0
        for idx, img_url in enumerate(image_urls, start=1):
            try:
                img_resp = requests.get(img_url, timeout=30)
                img_resp.raise_for_status()

                api_resp = requests.post(
                    "https://clipdrop-api.co/remove-text/v1",
                    headers={"x-api-key": CLIPDROP_API_KEY},
                    files={"image_file": ("image.jpg", img_resp.content, "image/jpeg")},
                    timeout=60,
                )

                if api_resp.ok:
                    cleaned = BytesIO(api_resp.content)
                    cleaned.name = "cleaned.jpg"
                    await update.message.reply_photo(
                        photo=cleaned,
                        caption=f"✅ {idx}/{total} - تمیز شد",
                    )
                    success += 1
                else:
                    await update.message.reply_photo(
                        photo=img_url,
                        caption=f"⚠️ {idx}/{total} - خام",
                    )
                    
            except Exception as e:
                await update.message.reply_text(f"❌ خطا در عکس {idx}")

        await status_msg.edit_text(f"🎉 تموم شد! {success}/{total} موفق")

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)[:150]}")


def main():
    # اجرای health server در background
    threading.Thread(target=run_health_server, daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link)
    )

    print("✅ Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
