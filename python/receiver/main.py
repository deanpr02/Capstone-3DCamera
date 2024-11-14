import ffmpeg
import numpy as np
import cv2

# Define the SRT stream URL (replace with actual IP and port)
srt_url = 'srt://127.0.0.1:5050?mode=listener&pkt_size=1316&latency=2000'

# Set up FFmpeg input to capture the SRT stream
stream = ffmpeg.input(srt_url, f='mpegts', flags='low_delay', fflags='nobuffer')

# Output configuration (e.g., store as raw frames or process further)
output = ffmpeg.output(stream, 'pipe:', format='rawvideo', pix_fmt='rgb24', vf='scale')

# Run the command and capture the output frames for further processing
process = ffmpeg.run_async(output, pipe_stdout=True)


# Frame dimensions (replace with actual frame size of your stream)
frame_width = 1280
frame_height = 720

while True:
    # Read raw frame data from FFmpeg process stdout
    in_bytes = process.stdout.read(frame_width * frame_height * 3)  # RGB24 format

    if not in_bytes:
        break

    # Convert raw bytes into a NumPy array and reshape it into an image frame
    frame = np.frombuffer(in_bytes, np.uint8).reshape([frame_height, frame_width, 3])

    # Invert colors
    #frame = cv2.bitwise_not(frame)

    cv2.imshow('SRT Stream', frame)

    # Break on key press (e.g., ESC)
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Release resources after processing is done
cv2.destroyAllWindows()
process.stdout.close()
process.wait()
