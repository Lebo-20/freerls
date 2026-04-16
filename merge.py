import subprocess
import asyncio
import os
import logging
from config import FFMPEG_CRF, FFMPEG_PRESET

logger = logging.getLogger(__name__)

class VideoMerger:
    @staticmethod
    async def merge_episodes(video_paths, output_path, fast_mode=True):
        if not video_paths:
            logger.error("No videos to merge")
            return False

        # Use a unique list file name based on output path to avoid conflict
        dir_name = os.path.dirname(output_path)
        base_name = os.path.basename(output_path).replace(".mp4", "")
        list_file = os.path.join(dir_name, f"list_{base_name}.txt")
        
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for path in video_paths:
                    # Escape single quotes in path for FFmpeg list file
                    abs_path = os.path.abspath(path).replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{abs_path}'\n")

            if fast_mode:
                cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path]
            else:
                cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                    "-c:v", "libx264", "-crf", str(FFMPEG_CRF), "-preset", FFMPEG_PRESET,
                    "-c:a", "aac", "-b:a", "128k", output_path
                ]

            logger.info(f"Running merge command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg Merge Failed (code {process.returncode})")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Merge exception: {e}")
            return False
        finally:
            if os.path.exists(list_file):
                try: os.remove(list_file)
                except: pass

    @staticmethod
    async def burn_subtitle(video_path, sub_path, output_path, crf=None):
        """Hardcode subtitle into video with custom styling."""
        if not os.path.exists(sub_path):
            logger.error(f"Subtitle file not found: {sub_path}")
            return False
        
        target_crf = crf if crf is not None else FFMPEG_CRF
        
        try:
            # Escape path for FFmpeg (Windows specific)
            abs_sub = os.path.abspath(sub_path).replace("\\", "/")
            clean_sub_path = abs_sub.replace(":", "\\:").replace("'", "'\\''")
            
            # Custom Style
            style = (
                "Fontname=Standard Symbols PS,FontSize=10,Bold=1,"
                "PrimaryColour=&HFFFFFF,Outline=1,OutlineColour=&H000000,"
                "Alignment=2,MarginV=90"
            )
            
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"scale=720:-2,subtitles='{clean_sub_path}':force_style='{style}'",
                "-c:v", "libx264", "-crf", str(target_crf), "-preset", FFMPEG_PRESET,
                "-c:a", "copy", output_path
            ]
            
            logger.info(f"Running burn command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg Burn Failed (code {process.returncode})")
                logger.error(f"Stderr: {stderr.decode()}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Burn exception: {e}")
            return False

def sanitize_filename(filename):
    """Remove characters that are invalid in Windows filenames."""
    if not filename: return "video"
    # Keep alphanumeric, space, dot, underscore, hyphen
    valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    filename = "".join(c for c in filename if c in valid_chars)
    return filename.strip()[:100] # Limit length
