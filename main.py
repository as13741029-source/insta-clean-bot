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
from instaloader import Instaloader, Post
import re

TOKEN = os.environ.get("TOKEN")
CLIPDROP_API_KEY = os.environ.get("CLIPDROP_API_KEY")

L = Instaloader()
# لاگین نکردیم ولی session خالی داریم برای پست‌های عمومی
L.context._session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "لینک پست یا ریل اینستاگرام رو بفرست.\n"
        "تصاویر رو بدون متن و استیکر برات می‌فرستم ✅\n\n"
        "⚠️ فقط پست‌های عمومی (Public) کار می‌کنه"
    )


def extract_shortcode(url: str) -> str | None:
    """استخراج shortcode از انواع لینک‌های اینستاگرام"""
    # حذف query parameters
    url = url.split("?")[0].strip("/")
    
    # الگوهای مختلف لینک
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


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال پردازش...")

    shortcode = extract_shortcode(url)
    if not shortcode:
        await status_msg.edit_text(
            "❌ لینک معتبر نیست.\n\n"
            "لینک باید به این شکل باشه:\n"
            "https://www.instagram.com/p/ABC123/"
        )
        return

    try:
        # دانلود اطلاعات پست
        post = Post.from_shortcode(L.context, shortcode)

        # استخراج URLهای تصاویر
        image_urls = []
        
        if post.typename == "GraphSidecar":
            # کاروسل (چند تصویر)
            for node in post.get_sidecar_nodes():
                if node.is_video:
                    continue  # فقط عکس می‌خوایم
                image_urls.append(node.display_url)
        elif post.typename == "GraphImage":
            # یک تصویر
            image_urls.append(post.url)
        elif post.typename == "GraphVideo":
            await status_msg.edit_text("❌ این یه ویدیوئه! فقط عکس پشتیبانی میشه")
            return
        else:
            await status_msg.edit_text(f"❌ نوع پست پشتیبانی نمیشه: {post.typename}")
            return

        if not image_urls:
            await status_msg.edit_text("❌ هیچ تصویری پیدا نشد")
            return

        total = len(image_urls)
        await status_msg.edit_text(
            f"✅ {total} تا عکس پیدا شد\n"
            f"در حال حذف متن‌ها با Clipdrop AI..."
        )

        success_count = 0
        for idx, img_url in enumerate(image_urls, start=1):
            try:
                # دانلود تصویر
                img_resp = requests.get(img_url, timeout=30)
                img_resp.raise_for_status()

                # ارسال به Clipdrop
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
                        caption=f"✅ عکس {idx}/{total} - کاملاً تمیز شد",
                    )
                    success_count += 1
                else:
                    # اگر API خطا داد، عکس خام
                    await update.message.reply_photo(
                        photo=img_url,
                        caption=f"⚠️ عکس {idx}/{total} - خام (API error {api_resp.status_code})",
                    )
                    
            except Exception as img_error:
                await update.message.reply_text(
                    f"❌ خطا در عکس {idx}/{total}: {str(img_error)[:100]}"
                )

        await status_msg.edit_text(
            f"🎉 تمام شد!\n"
            f"✅ {success_count}/{total} تصویر با موفقیت تمیز شد"
        )

    except Exception as e:
        error_msg = str(e)
        
        if "Login required" in error_msg or "private" in error_msg.lower():
            await status_msg.edit_text(
                "❌ این پست خصوصی (Private) هست\n"
                "فقط پست‌های عمومی کار می‌کنه 😔"
            )
        elif "not found" in error_msg.lower():
            await status_msg.edit_text(
                "❌ پست پیدا نشد - ممکنه حذف شده باشه"
            )
        else:
            await status_msg.edit_text(
                f"❌ خطا در دریافت پست:\n{error_msg[:200]}"
            )


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_link)
    )

    print("✅ Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
