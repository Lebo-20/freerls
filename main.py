import asyncio
import logging
import os
import shutil
import time
from datetime import datetime
import urllib.parse
from telethon import events, Button

from api import FreeReelsAPI
from downloader import Downloader
from merge import VideoMerger, sanitize_filename
from uploader import TelegramUploader
from gsheets_db import GoogleSheetsDB
from postgres_db import PostgresDB
from task_manager import DramaTask, TaskQueue
from ui_utils import generate_progress_bar, calculate_eta
from config import (
    BOT_TOKEN, DOWNLOAD_DIR, AUTO_SCAN_INTERVAL, 
    MAX_WORKERS, SEMAPHORE_LIMIT, PRIORITY_HIGH, PRIORITY_LOW,
    CHANNEL_ID, ADMIN_ID, MAX_UPLOAD_SIZE
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FreeReelsBot:
    def __init__(self):
        self.api = FreeReelsAPI()
        self.downloader = Downloader()
        self.merger = VideoMerger()
        self.uploader = TelegramUploader()
        self.db = GoogleSheetsDB()
        self.pg_db = PostgresDB()
        self.task_queue = TaskQueue()
        self.semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
        self.workers = []

    async def cleanup_on_startup(self):
        """Hapus file internal dan clear work state saat restart."""
        logger.info("Cleaning up temporary files and leftover videos...")
        if os.path.exists(DOWNLOAD_DIR):
            shutil.rmtree(DOWNLOAD_DIR)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        for file in os.listdir("."):
            if file.endswith(".mp4") or file.endswith(".ts"):
                try: os.remove(file)
                except: pass

    async def start(self):
        await self.cleanup_on_startup()
        await self.uploader.start()
        logger.info(f"Bot started with {MAX_WORKERS} workers...")
        
        # --- COMMAND HANDLERS ---
        
        @self.uploader.client.on(events.NewMessage(pattern='/start'))
        async def start_cmd(event):
            logger.info(f"Received /start from {event.sender_id}")
            await event.respond("🎬 **FreeReels Drama Automation Bot**\nDatabase: Google Sheets (FreeReels Tracker)")

        @self.uploader.client.on(events.NewMessage(pattern='/search (.+)'))
        async def search_cmd(event):
            query = event.pattern_match.group(1).strip()
            await self.execute_search(event, query)

        @self.uploader.client.on(events.NewMessage(pattern='/id (.+)'))
        async def id_cmd(event):
            drama_id = event.pattern_match.group(1).strip()
            logger.info(f"Received /id (download): {drama_id} from {event.sender_id}")
            if self.task_queue.is_processing(drama_id):
                await event.respond(f"❌ ID `{drama_id}` sedang diproses.")
                return
            await self.task_queue.put(DramaTask(PRIORITY_HIGH, drama_id, event=event))
            await event.respond(f"📥 ID `{drama_id}` masuk antrian (High Priority).")

        @self.uploader.client.on(events.NewMessage(pattern='/queue'))
        async def queue_status(event):
            logger.info(f"Received /queue from {event.sender_id}")
            status = f"📊 Queue: {self.task_queue.qsize()} | Running: {self.task_queue.processing_count()}"
            await event.respond(status)

        # --- CALLBACK HANDLERS ---

        @self.uploader.client.on(events.CallbackQuery(data=lambda d: d.startswith(b'details|')))
        async def callback_details(event):
            try:
                data_parts = event.data.decode().split('|')
                if len(data_parts) < 3:
                    await event.answer("❌ Data callback tidak valid.", alert=True)
                    return
                
                _, d_id, query = data_parts[:3]
                await event.answer("Mengambil detail...")
                
                detail = await self.api.get_drama_detail(d_id)
                if detail:
                    item = detail
                    title = item.get("title") or item.get("name", "Drama")
                    synopsis = item.get("description") or item.get("synopsis") or item.get("desc", "...")
                    thumb_url = item.get("cover")
                    
                    temp_thumb = os.path.join(DOWNLOAD_DIR, f"thumb_{d_id}.jpg")
                    success = await self.downloader.download_file(thumb_url, temp_thumb)
                    
                    buttons = [
                        [Button.inline("🚀 Download Full Movie", data=f"dl|{d_id}")],
                        [Button.inline("⬅️ Kembali ke Hasil", data=f"back|{query}")]
                    ]
                    
                    # Delete the search list message to keep chat clean
                    await event.delete()
                    
                    if success and os.path.exists(temp_thumb):
                        await event.client.send_file(
                            event.chat_id, temp_thumb, 
                            caption=(f"🎬 **{title}**\n🆔 ID: `{d_id}`\n\n📝 **SINOPSIS:**\n{synopsis}"), 
                            buttons=buttons
                        )
                        try: os.remove(temp_thumb)
                        except: pass
                    else:
                        await event.client.send_message(
                            event.chat_id,
                            f"🎬 **{title}** (ID: `{d_id}`)\n\n📝 **SINOPSIS:**\n{synopsis}",
                            buttons=buttons
                        )
                else:
                    await event.respond(f"❌ Detail tidak ditemukan untuk ID: `{d_id}`")
            except Exception as e:
                logger.error(f"Callback Details Error: {e}")

        @self.uploader.client.on(events.CallbackQuery(data=lambda d: d.startswith(b'back|')))
        async def callback_back(event):
            _, query = event.data.decode().split('|')
            await event.answer("Kembali...")
            # Delete the details message before showing search again
            await event.delete()
            await self.execute_search(event, query)

        @self.uploader.client.on(events.CallbackQuery(data=lambda d: d.startswith(b'dl|')))
        async def callback_dl(event):
            _, d_id = event.data.decode().split('|')
            
            # Check if processing or already in queue
            if self.task_queue.is_processing(d_id) or self.task_queue.is_queued(d_id):
                await event.answer("⚠️ Drama ini sudah ada di antrian atau sedang diproses!", alert=True)
                return
            
            await event.answer("✅ Drama ditambahkan ke antrian!")
            
            # Lock the button to prevent further clicks
            await event.edit(buttons=[[Button.inline("⏳ Sudah Masuk Antrian", data="noop")]])
            
            await self.task_queue.put(DramaTask(PRIORITY_HIGH, d_id, event=event))

        # --- WORKERS & AUTO MODE ---
        for i in range(MAX_WORKERS):
            self.workers.append(asyncio.create_task(self.worker(f"Worker-{i+1}")))
        asyncio.create_task(self.auto_mode_producer())
        
        await self.uploader.client.run_until_disconnected()

    async def execute_search(self, event, query):
        logger.info(f"Executing search for: {query}")
        msg = await event.respond(f"🔍 Mencari: `{query}`...")
        
        results = await self.api.search(query)
        if not results or not results.get("data"):
            results = await self.api.search_suggest(query)

        drama_list = results.get("data") or results.get("items")
        if results and drama_list:
            buttons = []
            for item in drama_list[:8]:
                title = item.get('title') or item.get('keyword')
                d_id = item.get('id')
                if d_id == 0 and item.get('deep_link'):
                    parsed = urllib.parse.urlparse(item.get('deep_link'))
                    qs = urllib.parse.parse_qs(parsed.query)
                    if 'id' in qs: d_id = qs['id'][0]
                buttons.append([Button.inline(f"🎬 {title}", data=f"details|{d_id}|{query}")])
            await msg.edit(f"🔍 **Hasil Pencarian: {query}**\nSilakan pilih drama:", buttons=buttons)
        else:
            await msg.edit(f"❌ Tidak ada hasil untuk: `{query}`")

    async def update_progress_ui(self, event, title, status, current, total, start_time):
        if not event or isinstance(event, events.CallbackQuery): return
        now = time.time()
        if hasattr(event, '_last_ui_update') and now - event._last_ui_update < 3: return
        event._last_ui_update = now
        bar = generate_progress_bar(current, total)
        eta = calculate_eta(start_time, current, total)
        text = (f"🎬 **[FreeReels] Full Episode: {title}**\n🔥 Status: {status}...\n🎞 Progress: {bar}\n⏳ Estimasi: {eta}")
        try:
            if not hasattr(event, '_progress_msg'): event._progress_msg = await event.respond(text)
            else: await event._progress_msg.edit(text)
        except: pass

    async def notify_admin(self, message):
        if ADMIN_ID != 0:
            try: await self.uploader.client.send_message(ADMIN_ID, f"🔔 **[FreeReels NOTIF]**\n{message}")
            except: pass

    async def worker(self, name):
        while True:
            try:
                task = await self.task_queue.get()
                if self.task_queue.is_processing(task.drama_id):
                    self.task_queue.task_done()
                    continue

                self.task_queue.add_processing(task.drama_id)
                
                # Send start notification only ONCE
                detail = await self.api.get_drama_detail(task.drama_id)
                title = detail.get("title") or detail.get("name") if detail else f"ID_{task.drama_id}"
                await self.notify_admin(f"🚀 Memproses: **{title}**")

                async with self.semaphore:
                    success = False
                    for attempt in range(3):
                        result = await self.process_drama(task, name, attempt + 1)
                        if result:
                            if result is True: # Actual upload success, not a skip
                                logger.info(f"✅ {name} selesai upload drama baru. Bot istirahat 10 menit...")
                                await asyncio.sleep(600)
                            
                            success = True
                            break
                        
                        if attempt == 0: # Gagal 1x -> Tunggu 2 Jam
                            wait_time = 2 * 3600 
                            wait_str = "2 JAM"
                        elif attempt == 1: # Gagal 2x -> Tunggu 4 Jam
                            wait_time = 4 * 3600
                            wait_str = "4 JAM"
                        else:
                            break

                        logger.warning(f"⚠️ {name} Gagal pada percobaan {attempt+1}. Cooldown selama {wait_str} untuk ID {task.drama_id}...")
                        await asyncio.sleep(wait_time)
                    
                    if not success: 
                        await self.notify_admin(f"❌ Gagal memproses: **{title}** setelah 3x percobaan.")
                
                self.task_queue.remove_processing(task.drama_id)
                self.task_queue.task_done()
            except Exception as e:
                logger.error(f"{name} error: {e}")
                await asyncio.sleep(5)

    async def process_drama(self, task, worker_name, attempt):
        drama_id = task.drama_id
        # Handle feedback message target correctly
        event = getattr(task, 'event', None)
        feedback_target = event
        if isinstance(event, events.CallbackQuery):
            # For callback queries, we should send new messages to the chat
            feedback_target = event
        
        start_time = time.time()
        try:
            detail = await self.api.get_drama_detail(drama_id)
            if not detail: return False
            drama_info = detail # Root object
            title = drama_info.get("title") or drama_info.get("name", f"Drama_{drama_id}")
            safe_title = sanitize_filename(title)
            if self.db.is_processed(title) or self.pg_db.is_processed(title): 
                logger.info(f"⏩ {title} sudah pernah diproses. Skipping...")
                return "SKIP"
            
            ep_data = await self.api.get_episodes(drama_id)
            # API returns results in 'episode_list' 
            episodes = ep_data.get("episode_list") if ep_data else None
            if not episodes:
                logger.error(f"No episodes found for ID: {drama_id}")
                return False
            
            total_eps = len(episodes)
            
            # Dynamic CRF Selection based on episode count
            if total_eps > 25:
                dynamic_crf = 26
            elif total_eps > 10:
                dynamic_crf = 24
            else:
                dynamic_crf = 22
            
            logger.info(f"Using Dynamic CRF: {dynamic_crf} for {total_eps} episodes (ID: {drama_id})")
            
            temp_dir = os.path.join(DOWNLOAD_DIR, f"{worker_name}_{drama_id}")
            os.makedirs(temp_dir, exist_ok=True)

            current_part_videos = []
            current_part_size = 0
            part_count = 1
            
            thumb = os.path.join(temp_dir, "poster.jpg")
            await self.downloader.download_file(drama_info.get("cover"), thumb)
            synopsis = drama_info.get("description") or drama_info.get("synopsis") or "..."
            
            # Intro notification
            await self.uploader.client.send_file(CHANNEL_ID, thumb, caption=f"🎬 **{title}**\n\n📝 **Sinopsis:**\n{synopsis}")

            for i, ep in enumerate(episodes):
                ep_n = ep.get("index") or ep.get("episode_num") or ep.get("ep")
                if ep_n is None: continue
                
                stream = await self.api.get_stream(drama_id, ep_n)
                if not stream: continue
                
                # 1. Video URL
                video_url = stream.get("video_url") or stream.get("m3u8_url")
                if not video_url: continue
                
                # 2. Subtitle id-ID
                sub_url = None
                sub_list = stream.get("subtitle_list", [])
                for sub in sub_list:
                    if sub.get("language") == "id-ID":
                        sub_url = sub.get("subtitle") or sub.get("vtt")
                        break
                
                # 3. Download
                raw_video = os.path.join(temp_dir, f"raw_ep_{ep_n}.mp4")
                burned_video = os.path.join(temp_dir, f"ep_{ep_n}.mp4")
                
                async def dl_prog(c, t):
                    await self.update_progress_ui(feedback_target, title, f"Downloading Eps {i+1}/{total_eps}", i + (c/t), total_eps, start_time)
                
                if await self.downloader.download_file(video_url, raw_video, progress_callback=dl_prog):
                    if sub_url:
                        sub_ext = "srt" if ".srt" in sub_url.lower() else "ass" if ".ass" in sub_url.lower() else "vtt"
                        sub_path = os.path.join(temp_dir, f"sub_{ep_n}.{sub_ext}")
                        await self.downloader.download_file(sub_url, sub_path)
                        
                        await self.update_progress_ui(feedback_target, title, f"Burning Sub Eps {i+1}", i + 0.5, total_eps, start_time)
                        if await self.merger.burn_subtitle(raw_video, sub_path, burned_video, crf=dynamic_crf):
                            try: os.remove(raw_video); os.remove(sub_path)
                            except: pass
                        else:
                            os.rename(raw_video, burned_video)
                    else:
                        os.rename(raw_video, burned_video)
                    
                    # Size Check for Splitting
                    ep_size = os.path.getsize(burned_video)
                    if current_part_size + ep_size > MAX_UPLOAD_SIZE and current_part_videos:
                        # Merge and Upload current part
                        merged_part = os.path.join(temp_dir, f"{safe_title}_Part_{part_count}.mp4")
                        await self.update_progress_ui(feedback_target, title, f"Merging Part {part_count}...", 0.95, 1, start_time)
                        if await self.merger.merge_episodes(current_part_videos, merged_part):
                            ul_start_time = time.time()
                            async def ul_prog(c, t):
                                await self.update_progress_ui(feedback_target, title, f"Uploading Part {part_count}", c, t, ul_start_time)
                            
                            if not await self.uploader.upload_video(merged_part, f"🎞 **{title} (Part {part_count})** #FreeReels", thumb, progress_callback=ul_prog):
                                return False # Upload failed
                            
                            # Cleanup this part's videos
                            for f in current_part_videos:
                                try: os.remove(f)
                                except: pass
                            try: os.remove(merged_part)
                            except: pass
                            
                            part_count += 1
                            current_part_videos = []
                            current_part_size = 0
                        else:
                            return False # Merge failure
                    
                    current_part_videos.append(burned_video)
                    current_part_size += ep_size
                else:
                    return False

            # Final Part
            if current_part_videos:
                suffix = "Full" if part_count == 1 else f"Part_{part_count}"
                merged = os.path.join(temp_dir, f"{safe_title}_{suffix}.mp4")
                await self.update_progress_ui(feedback_target, title, f"Final Merging ({suffix})...", 0.95, 1, start_time)
                
                if not await self.merger.merge_episodes(current_part_videos, merged):
                    if not await self.merger.merge_episodes(current_part_videos, merged, False): return False

                ul_start_time = time.time()
                async def last_ul_prog(c, t):
                    await self.update_progress_ui(feedback_target, title, f"Uploading {suffix}", c, t, ul_start_time)
                
                caption = f"🎞 **{title}** #FreeReels" if part_count == 1 else f"🎞 **{title} ({suffix.replace('_', ' ')})** #FreeReels"
                if await self.uploader.upload_video(merged, caption, thumb, progress_callback=last_ul_prog):
                    self.db.mark_success(title)
                    self.pg_db.mark_success(title)
                    await self.notify_admin(f"✅ Selesai: **{title}**")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return True
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    async def auto_mode_producer(self):
        """Scans for new dramas and adds them to queue."""
        logger.info("Auto Mode Producer started (monitoring 'New' and 'Last' arrivals)...")
        # Priority on 'New' as requested by user
        srcs = [("New Arrivals", self.api.get_new), ("Trending", self.api.get_popular), ("Discover", self.api.get_foryou)]
        
        while True:
            try:
                for name, func in srcs:
                    logger.info(f"🔍 Auto-scanning source: {name}")
                    res = await func()
                    if res and res.get("data"):
                        count_added = 0
                        for item in res["data"]:
                            d_id = item.get("id")
                            if d_id == 0 and item.get("deep_link"):
                                try:
                                    parsed = urllib.parse.urlparse(item.get('deep_link'))
                                    qs = urllib.parse.parse_qs(parsed.query)
                                    if 'id' in qs: d_id = qs['id'][0]
                                except: pass
                            
                            title = item.get("title") or item.get("name")
                            if d_id and not (self.db.is_processed(title) or self.pg_db.is_processed(title)):
                                if not self.task_queue.is_queued(str(d_id)) and not self.task_queue.is_processing(str(d_id)):
                                    await self.task_queue.put(DramaTask(PRIORITY_LOW, str(d_id)))
                                    count_added += 1
                        
                        if count_added > 0:
                            logger.info(f"➕ Auto Mode found {count_added} new items from {name}")
                
                # Check New/Last more frequently, but others less
                await asyncio.sleep(AUTO_SCAN_INTERVAL)
            except Exception as e:
                logger.error(f"Auto Mode Error: {e}")
                await asyncio.sleep(60) # Wait a bit on error before retry

if __name__ == "__main__":
    bot = FreeReelsBot()
    asyncio.run(bot.start())
