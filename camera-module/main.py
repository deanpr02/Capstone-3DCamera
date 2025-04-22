import asyncio
import os
import sys
import socketio
import ssl
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, RTCConfiguration, RTCIceServer, MediaStreamTrack
from aiortc.contrib.media import MediaPlayer
import platform
import cv2


# Create an SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Socket.IO client setup
sio = socketio.AsyncClient(ssl_verify=False)
pc = None
local_tracks = None

config = RTCConfiguration(iceServers=[
    RTCIceServer(urls=["stun:stun.l.google.com:19302"])
])

async def create_peer_connection():
    global pc
    pc = RTCPeerConnection(configuration=config)
    
    @pc.on("icecandidate")
    def on_icecandidate(candidate):
        if candidate:
            asyncio.create_task(send_ice_candidate(candidate))

    @pc.on("track")
    def on_track(track):
        print(f"Received {track.kind} track")

async def send_ice_candidate(candidate):
    await sio.emit('sendIceCandidateToSignalingServer', {
        'didIOffer': True,  # Change this based on your role (offerer/answerer)
        'iceUserName': 'python_client',
        'iceCandidate': {
            'candidate': candidate.candidate,
            'sdpMid': candidate.sdpMid,
            'sdpMLineIndex': candidate.sdpMLineIndex
        }
    })
  
def find_available_cameras(max_cameras=3):
    """Discover available video devices"""
    cameras = []
    for i in range(max_cameras*2 + 1):  # Check up to double the requested
        dev_path = f"/dev/video{i}"
        if os.path.exists(dev_path):
            try:
                # Basic validation attempt
                cap = cv2.VideoCapture(dev_path)
                if cap.isOpened():
                    cameras.append(dev_path)
                    cap.release()
            except:
                continue
    return cameras[:max_cameras]  # Return up to requested amount

def create_local_tracks(camera_amount):
    tracks = []
    options = {"framerate": "30", "video_size": "640x480"}

    if platform.system() == "Darwin":  # macOS
        tracks.append(MediaPlayer("default:none", format="avfoundation", options=options))
        return tracks
    elif platform.system() == "Windows":
        tracks.append(MediaPlayer("video=Integrated Camera", format="dshow", options=options))
        return tracks
    else:  # Linux
        available_cams = find_available_cameras(camera_amount)
        print(f"Discovered cameras: {available_cams}")
        
        if not available_cams:
            raise RuntimeError("No valid cameras found!")
        
        for cam_dev in available_cams:
            try:
                player = MediaPlayer(cam_dev, format="v4l2", options=options)
                tracks.append(player)
            except Exception as e:
                print(f"⚠️ Failed to open {cam_dev}: {str(e)}")
                continue
                
        return tracks

async def create_offer():
    global local_tracks
    camera_amount = int(sys.argv[1])
    
    tracks = create_local_tracks(camera_amount)
    if not tracks:
        await shutdown()
        raise RuntimeError("No valid camera tracks available")
    
    local_tracks = [t.video for t in tracks]
    for track in local_tracks:
        pc.addTrack(track)

    # Create and set local description
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    # Send offer to signaling server
    await sio.emit('newOffer', {
        'sdp': pc.localDescription.sdp,
        'type': pc.localDescription.type
    })

@sio.event
async def connect():
    print("Connected to signaling server")
    await create_peer_connection()
    await create_offer()

@sio.event
async def availableOffers(offers):
    print("Received available offers")
    # Here you would typically choose an offer to answer
    # For simplicity, we'll just print the offers
    print(offers)
@sio.event
async def newOfferAwaiting(offer):
    print("📨 Received offer, creating answer...")

@sio.event
async def answerResponse(answer_data):
    print("Received answer")
    answer = RTCSessionDescription(sdp=answer_data['answer']['sdp'], type=answer_data['answer']['type'])
    await pc.setRemoteDescription(answer)

@sio.event
async def receivedIceCandidateFromServer(candidate):
    print("Received ICE candidate from server")
    candidate_obj = RTCIceCandidate(
        candidate['candidate'],
        candidate['sdpMid'],
        candidate['sdpMLineIndex']
    )
    await pc.addIceCandidate(candidate_obj)

async def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <camera_amount>")
        sys.exit(1)

    try:
        await sio.connect('https://192.168.0.151:8181/',
            auth={'userName': 'camera-module', 'password': 'x'}
        )
        await sio.wait()
    except KeyboardInterrupt:
        pass  # Handled by finally block
    finally:
        await shutdown()

# Add this shutdown handler
async def shutdown():
    print("\nShutting down gracefully...")
    
    # Close WebRTC connection
    if pc:
        await pc.close()
        print("Closed peer connection")
    
    # Release camera resources
    for track in local_tracks:
        track.stop()
    # Disconnect from signaling server
    if sio.connected:
        await sio.disconnect()
        print("Disconnected from signaling server")

if __name__ == '__main__':
    asyncio.run(main())
