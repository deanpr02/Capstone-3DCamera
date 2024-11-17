import ffmpeg
import platform

os_name = platform.system()

if os_name == 'Darwin':
    # macOS
    input_device = '0'

elif os_name == 'Linux':
    # Linux
    input_device = '/dev/video0'

elif os_name == 'Windows':
    # Windows
    input_device = 'video=Integrated Camera'


output_url = "srt://127.0.0.1:5050?pkt_size=1316&mode=caller"

(ffmpeg
 .input(input_device, format='avfoundation', framerate=30)
 .output(output_url, format='mpegts', preset='veryfast', vcodec='libx264')
 .run()
)