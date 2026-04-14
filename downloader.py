import httpx
import asyncio
import os
import logging
from tqdm.asyncio import tqdm
from config import MAX_CONCURRENT_DOWNLOADS

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, semaphore_limit=MAX_CONCURRENT_DOWNLOADS):
        self.semaphore = asyncio.Semaphore(semaphore_limit)

    async def download_file(self, url, dest_path, description=None, progress_callback=None):
        if not url:
            logger.error(f"Invalid URL for {dest_path}")
            return False

        # Support for M3U8 streams using FFmpeg
        if ".m3u8" in url.lower():
            logger.info(f"Downloading M3U8 stream via FFmpeg: {url}")
            try:
                os.makedirs(os.path.dirname(dest_path) if os.path.dirname(dest_path) else ".", exist_ok=True)
                cmd = ["ffmpeg", "-y", "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", dest_path]
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                return process.returncode == 0
            except Exception as e:
                logger.error(f"FFmpeg stream download failed: {e}")
                return False

        async with self.semaphore:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                try:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        total = int(response.headers.get("Content-Length", 0))
                        
                        dirname = os.path.dirname(dest_path)
                        if dirname:
                            os.makedirs(dirname, exist_ok=True)
                        
                        with open(dest_path, "wb") as f:
                            with tqdm(total=total, unit="B", unit_scale=True, desc=description or os.path.basename(dest_path), leave=False) as pbar:
                                downloaded = 0
                                async for chunk in response.aiter_bytes():
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    pbar.update(len(chunk))
                                    if progress_callback:
                                        await progress_callback(downloaded, total)
                        return True
                except Exception as e:
                    logger.error(f"Download failed for {url}: {str(e)}")
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    return False

    async def download_batch(self, tasks):
        # tasks is a list of tuples (url, dest_path, description)
        coros = [self.download_file(url, path, desc) for url, path, desc in tasks]
        return await asyncio.gather(*coros)
