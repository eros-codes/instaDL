import os
import re
import glob
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from keep_alive import keep_alive

TOKEN = "8650033727:AAGIbkqr5gbQCeoViZwEVsoKyLGsyUDdYjA"

INSTAGRAM_PATTERN = re.compile(
    r'https?://(?:www\.)?instagram\.com/(?:p|reel|reels|stories|tv)/[\w-]+(?:/[\w-]*)?/?(?:\?[^\s]*)?'
)

DOWNLOAD_DIR = "downloads"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! لینک پست یا ریل اینستاگرام رو برام بفرست تا دانلودش کنم."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = INSTAGRAM_PATTERN.search(text)

    if not match:
        await update.message.reply_text(
            "لینک اینستاگرام معتبر نیست! لطفاً یک لینک پست یا ریل اینستاگرام بفرست."
        )
        return

    url = match.group(0)
    await update.message.reply_text("در حال دانلود... لطفاً صبر کن.")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    unique_id = str(update.message.message_id)
    output_template = f"{DOWNLOAD_DIR}/{unique_id}.%(ext)s"

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "username": "post.downloader.bot",
        "password": "mypythonproject",
    }

    downloaded_file = None
    try:
        loop = asyncio.get_running_loop()

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info

        info = await loop.run_in_executor(None, download)

        # Find the downloaded file by unique_id prefix
        matched_files = glob.glob(f"{DOWNLOAD_DIR}/{unique_id}.*")
        if matched_files:
            downloaded_file = max(matched_files, key=os.path.getmtime)

        if not downloaded_file or not os.path.exists(downloaded_file):
            await update.message.reply_text(
                "دانلود ناموفق بود! ممکنه پست خصوصی باشه یا لینک نادرست."
            )
            return

        file_size = os.path.getsize(downloaded_file)
        if file_size > 50 * 1024 * 1024:
            await update.message.reply_text(
                "فایل خیلی بزرگه! حداکثر ۵۰ مگابایت قابل ارسال است."
            )
            return

        ext = os.path.splitext(downloaded_file)[1].lower()
        is_video = ext in (".mp4", ".mkv", ".mov", ".avi", ".webm")

        with open(downloaded_file, "rb") as f:
            if is_video:
                await update.message.reply_video(video=f)
            else:
                await update.message.reply_photo(photo=f)

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if "private" in error_msg or "login" in error_msg or "cookie" in error_msg:
            await update.message.reply_text(
                "این پست خصوصی است و قابل دانلود نیست."
            )
        elif "not found" in error_msg or "404" in error_msg or "does not exist" in error_msg:
            await update.message.reply_text(
                "پست پیدا نشد! احتمالاً حذف شده یا لینک اشتباه است."
            )
        elif "rate" in error_msg or "too many" in error_msg:
            await update.message.reply_text(
                "اینستاگرام موقتاً درخواست‌ها را محدود کرده. کمی صبر کن و دوباره امتحان کن."
            )
        else:
            await update.message.reply_text(
                "دانلود با خطا مواجه شد. لطفاً مطمئن شو لینک درست و پست عمومی است."
            )
    except Exception:
        await update.message.reply_text(
            "خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره امتحان کن."
        )
    finally:
        for leftover in glob.glob(f"{DOWNLOAD_DIR}/{unique_id}.*"):
            try:
                os.remove(leftover)
            except OSError:
                pass


def main():
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("ربات شروع به کار کرد!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
