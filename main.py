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

TOKEN = os.environ.get("8408562152:AAHyA8gzuG707N9EfifGe8LAbRtTuIAph1I
")
CLIPDROP_API_KEY = os.environ.get("2edfd7ff6795d44df2469531edf3ca51991ffee1100f228ac5638b5855ca29ce6ea7f5f426cd6ae5808c7398fa032a9b")

L = Instaloader()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "لینک پست یا ریل اینستاگرام رو بفرست.\n"
        "تصاویر رو بدون متن و استیکر برات می‌فرستم ✅"
    )


def extract_shortcode(url: str) -> str | None:
    url = url.split("?")[0]
    parts = url.strip("/").split("/")
    if "p" in parts:
        i = parts.index("p")
        return parts[i + 1] if i + 1 < len(parts) else None
    if "reel" in parts:
        i = parts.index("reel")
        return parts[i + 1] if i + 1 < len(parts) else None
    if "tv" in parts:
        i = parts.index("tv")
        return parts[i + 1] if i + 1 < len(parts) else None
    return None


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ در حال پردازش لینک...")

    shortcode = extract_shortcode(url)
    if not shortcode:
        await status_msg.edit_text("❌ لینک اینستاگرام معتبر نیست.")
        return

    try:
        post = Post.from_shortcode(L.context, shortcode)

        # تشخیص اسلایدها (کاروسل) یا یک تصویر
        slides = []
        if post.typename == "GraphSidecar":
            for node in post.get_sidecar_nodes():
                slides.append(node.display_url)
        else:
            slides.append(post.url)

        total = len(slides)
        await status_msg.edit_text(
            f"✅ پست پیدا شد. تعداد تصاویر: {total}\n"
            f"در حال حذف متن از روی عکس‌ها با Clipdrop..."
        )

        for idx, img_url in enumerate(slides, start=1):
            # گرفتن تصویر اصلی
            img_resp = requests.get(img_url, timeout=30)
            img_resp.raise_for_status()

            # فرستادن به API کلیپ‌دراپ
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
                    caption=f"🖼 عکس {idx}/{total} - متن‌ها حذف شد ✅",
                )
            else:
                # اگر API خطا داد تصویر خام را می‌فرستیم
                await update.message.reply_photo(
                    photo=img_url,
                    caption=(
                        f"⚠️ عکس {idx}/{total} - خطا در Clipdrop "
                        f"(کد: {api_resp.status_code})\n"
                        "تصویر خام ارسال شد."
                    ),
                )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش پست یا لینک.\n{e}")


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
