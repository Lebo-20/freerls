import subprocess
import os
import logging
from config import FFMPEG_CRF, FFMPEG_PRESET

logger = logging.getLogger(__name__)

class VideoMerger:
    @staticmethod
    def merge_episodes(video_paths, output_path, fast_mode=True):
        if not video_paths:
            logger.error("No videos to merge")
            return False

        list_file = "file_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for path in video_paths:
                abs_path = os.path.abspath(path).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        try:
            if fast_mode:
                cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path]
            else:
                cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                    "-c:v", "libx264", "-crf", str(FFMPEG_CRF), "-preset", FFMPEG_PRESET,
                    "-c:a", "aac", "-b:a", "128k", output_path
                ]

            process = subprocess.run(cmd, capture_output=True, text=True)
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Merge error: {e}")
            return False
        finally:
            if os.path.exists(list_file): os.remove(list_file)

    @staticmethod
    def burn_subtitle(video_path, sub_path, output_path):
        """Hardcode subtitle into video with custom styling."""
        if not os.path.exists(sub_path): return False
        try:
            # Escape path for FFmpeg (Windows specific)
            clean_sub_path = os.path.abspath(sub_path).replace("\\", "/").replace(":", "\\:")
            
            # Custom Style: Font Standard Symbols PS, Size 10, Bold, Outline 1 Black, MarginV 90
            style = (
                "Fontname=Standard Symbols PS,FontSize=10,Bold=1,"
                "PrimaryColour=&HFFFFFF,Outline=1,OutlineColour=&H000000,"
                "Alignment=2,MarginV=90"
            )
            
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles='{clean_sub_path}':force_style='{style}'",
                "-c:v", "libx264", "-crf", str(FFMPEG_CRF), "-preset", FFMPEG_PRESET,
                "-c:a", "copy", output_path
            ]
            process = subprocess.run(cmd, capture_output=True, text=True)
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Burn error: {e}")
            return False
