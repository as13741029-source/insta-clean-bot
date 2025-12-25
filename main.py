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
import json

TOKEN = os.environ.get("TOKEN")
CLIPDROP_API_KEY = os.environ.get("CLIPDROP_API_KEY")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "لینک پست یا ریل اینستاگرام رو بفرست.\n"
        "تصاویر رو بدون متن و استیکر برات می‌فرستم ✅\n\n"
        "فقط پست‌های عمومی کار می‌کنه"
    )


def extract_shortcode(url: str):
    """استخراج shortcode از لینک"""
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
    """دریافت تصاویر پست از اینستاگرام"""
    
    # روش ۱: استفاده از API غیررسمی عمومی
    url = f"https://www.instagram.com/api/v1/media/{shortcode}/info/"
    
    headers = {
        'User-Agent': 'Instagram 76.0.0.15.395 Android (24/7.0; 640dpi; 1440x2560; samsung; SM-G930F; herolte; samsungexynos8890; en_US; 138226743)',
        'Accept': '*/*',
        'Accept-Language': 'en-US',
    }
    
    try:
        # تلاش اول
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            if items:
                return extract_images_from_item(items[0])
    except:
        pass
    
    # روش ۲: استفاده از embed endpoint
    try:
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = requests.get(embed_url, timeout=15)
        
        if resp.status_code == 200:
            # پیدا کردن URL تصویر از HTML
            import re
            img_pattern = r'"display_url":"(https://[^"]+)"'
            matches = re.findall(img_pattern, resp.text)
            
            if matches:
                # دیکد کردن unicode escapes
                images = [m.encode().decode('unicode_escape') for m in matches]
                return list(set(images))  # حذف تکراری‌ها
    except:
        pass
    
    # روش ۳: استفاده از media endpoint مستقیم
    try:
        media_url = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
        resp = requests.head(media_url, allow_redirects=True, timeout=10)
        
        if resp.status_code == 200:
            final_url = resp.url
            return [final_url]
    except:
        pass
    
    return []


def extract_images_from_item(item):
    """استخراج URLهای تصویر از آیتم اینستاگرام"""
    images = []
    
    # چک carousel
    if 'carousel_media' in item:
        for media in item['carousel_media']:
            if 'image_versions2' in media:
                candidates = media['image_versions2'].get('candidates', [])
                if candidates:
                    images.append(candidates[0]['url'])
    # تک تصویر
    elif 'image_versions2' in item:
        candidates = item['image_versions2'].get('candidates', [])
        if candidates:
            images.append(candidates[0]['url'])
    
    return images


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال دریافت پست...")

    shortcode = extract_shortcode(url)
    if not shortcode:
        await status_msg.edit_text(
            "❌ لینک معتبر نیست\n\n"
            "مثال درست:\n"
            "https://www.instagram.com/p/ABC123/"
        )
        return

    try:
        # دریافت تصاویر
        image_urls = get_instagram_images(shortcode)
        
        if not image_urls:
            await status_msg.edit_text(
                "❌ نتونستم تصاویر پست رو پیدا کنم\n\n"
                "ممکنه:\n"
                "• پست خصوصی باشه\n"
                "• پست حذف شده باشه\n"
                "• پست فقط ویدیو باشه"
            )
            return

        total = len(image_urls)
        await status_msg.edit_text(
            f"✅ {total} تا عکس پیدا شد!\n"
            f"🎨 در حال حذف متن‌ها با AI..."
        )

        success = 0
        for idx, img_url in enumerate(image_urls, start=1):
            try:
                # دانلود تصویر اصلی
                img_resp = requests.get(img_url, timeout=30)
                img_resp.raise_for_status()

                # ارسال به Clipdrop برای حذف متن
                api_resp = requests.post(
                    "https://clipdrop-api.co/remove-text/v1",
                    headers={"x-api-key": CLIPDROP_API_KEY},
                    files={"image_file": ("image.jpg", img_resp.content, "image/jpeg")},
                    timeout=60,
                )

                if api_resp.ok:
                    # ارسال تصویر تمیز شده
                    cleaned = BytesIO(api_resp.content)
                    cleaned.name = "cleaned.jpg"
                    await update.message.reply_photo(
                        photo=cleaned,
                        caption=f"✅ عکس {idx}/{total} - کاملاً تمیز شد",
                    )
                    success += 1
                else:
                    # اگر API خطا داد، عکس خام
                    await update.message.reply_photo(
                        photo=img_url,
                        caption=f"⚠️ عکس {idx}/{total} - خام (Clipdrop error)",
                    )
                    
            except Exception as e:
                await update.message.reply_text(
                    f"❌ خطا در پردازش عکس {idx}: {str(e)[:80]}"
                )

        await status_msg.edit_text(
            f"🎉 کار تمومه!\n"
            f"✅ {success}/{total} عکس با موفقیت تمیز شد"
        )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ خطای غیرمنتظره:\n{str(e)[:200]}"
        )


def main():
    if not TOKEN:
        print("❌ ERROR: TOKEN environment variable not set!")
        return
    
    if not CLIPDROP_API_KEY:
        print("⚠️ WARNING: CLIPDROP_API_KEY not set, text removal won't work!")
    
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link)
    )

    print("✅ Bot is running...")
    print(f"✅ Clipdrop API: {'Enabled' if CLIPDROP_API_KEY else 'Disabled'}")
    application.run_polling()


if __name__ == "__main__":
    main()
