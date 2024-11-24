import ffmpeg
import numpy as np
import cv2

# Define the SRT stream URL (replace with actual IP and port)
srt_url = "srt://127.0.0.1:5050?mode=listener&pkt_size=1316&latency=2000"
output_url = "srt://127.0.0.1:5051?pkt_size=1316&mode=caller"

# Set up FFmpeg input to capture the SRT stream
(
    ffmpeg.input(srt_url, f="mpegts", flags="low_delay", fflags="nobuffer")
    .filter("negate")
    .output(output_url, format="mpegts", preset="veryfast", vcodec="libx264")
    .run()
)
