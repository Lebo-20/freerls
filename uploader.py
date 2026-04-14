import os
import logging
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
import asyncio
from config import API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID

logger = logging.getLogger(__name__)

class TelegramUploader:
    def __init__(self):
        self.client = TelegramClient('bot_session', API_ID, API_HASH)

    async def start(self):
        await self.client.start(bot_token=BOT_TOKEN)

    async def upload_video(self, file_path, caption, thumb_path=None, progress_callback=None):
        if not os.path.exists(file_path):
            logger.error(f"File not found for upload: {file_path}")
            return None

        try:
            # Metadata parsing (simple duration/width/height could be added with enzyme or similar, 
            # but let's keep it simple or use ffmpeg to get info if needed)
            
            # Use telethon's upload_file with progress
            async def upload_progress(current, total):
                if progress_callback:
                    await progress_callback(current, total)

            sent_msg = await self.client.send_file(
                CHANNEL_ID,
                file_path,
                caption=caption,
                thumb=thumb_path,
                supports_streaming=True,
                progress_callback=upload_progress
            )
            return sent_msg
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return None

    async def disconnect(self):
        await self.client.disconnect()
