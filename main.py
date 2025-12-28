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
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")


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
    print(f"Health server on port {port}")
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
    if RAPIDAPI_KEY:
        try:
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info"
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
            }
            params = {"code_or_id_or_url": shortcode}
            
            response = requests.get(url, headers=headers, params=params, timeout=20)
            print(f"RapidAPI status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                images = []
                
                if 'data' in data and 'items' in data['data']:
                    items = data['data']['items']
                    if items:
                        item = items[0]
                        
                        if 'carousel_media' in item:
                            for media in item['carousel_media']:
                                if 'image_versions2' in media:
                                    candidates = media['image_versions2']['candidates']
                                    if candidates:
                                        images.append(candidates[0]['url'])
                        elif 'image_versions2' in item:
                            candidates = item['image_versions2']['candidates']
                            if candidates:
                                images.append(candidates[0]['url'])
                
                if images:
                    print(f"Found {len(images)} images")
                    return images
        except Exception as e:
            print(f"RapidAPI error: {e}")
    
    print("Trying fallback...")
    try:
        url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        
        if resp.status_code == 200:
            pattern = r'https://[^"\'>\s]*(?:cdninstagram|fbcdn)[^"\'>\s]*\.jpg'
            matches = re.findall(pattern, resp.text)
            if matches:
                return list(set(matches))[:10]
    except Exception as e:
        print(f"Fallback error: {e}")
    
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
            await msg.edit_text("❌ تصویری پیدا نشد")
            return

        total = len(images)
        await msg.edit_text(f"✅ {total} عکس پیدا شد، در حال پردازش...")

        ok = 0
        for i, img_url in enumerate(images, 1):
            try:
                img_data = requests.get(img_url, timeout=30).content
                
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
                    await update.message.reply_photo(img_url, caption=f"⚠️ {i}/{total}")
            except Exception as e:
                print(f"Error image {i}: {e}")

        await msg.edit_text(f"🎉 تمام! {ok}/{total} موفق")

    except Exception as e:
        await msg.edit_text(f"❌ خطا: {str(e)[:100]}")


def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    print("✅ Bot started!")
    print(f"RapidAPI: {'Yes' if RAPIDAPI_KEY else 'No'}")
    print(f"Clipdrop: {'Yes' if CLIPDROP_API_KEY else 'No'}")
    
    app.run_polling()


if __name__ == "__main__":
    main()
