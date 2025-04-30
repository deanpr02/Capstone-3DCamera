import asyncio
import aiortc.sdp
import socketio
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCConfiguration, RTCIceServer, RTCRtpCodecParameters, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole
import aiortc
import numpy as np
import numpy
import cv2
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
import matplotlib.pyplot as plt
import time
from av import VideoFrame
import queue

class QueuedVideoStreamTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.fdata_queue = asyncio.Queue(maxsize=60)

    def put_frame(self, frame_data):
        try:
            self.fdata_queue.put_nowait(frame_data)
        except Exception as e:
            pass
            #print(f"Error queuing frame: {e}")

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame_data = await self.fdata_queue.get()
        frame = VideoFrame.from_ndarray(frame_data, format="bgr24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

original_video_track = QueuedVideoStreamTrack()
depth_video_track = QueuedVideoStreamTrack()

# Depth estimation model functions from webcam_simple.py
def load_model():
    # Use MiDaS small model which is more reliable
    model = torch.hub.load("intel-isl/MiDaS", "DPT_Hybrid")

    # Switch to eval mode
    model.eval()

    # Move to GPU if available
    if torch.cuda.is_available():
        model = model.cuda()

    return model

def process_image(img, size=(256, 256)):
    # OpenCV uses BGR color ordering, need to convert to RGB for the model
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Resize to model input size
    img_resized = cv2.resize(img_rgb, size, interpolation=cv2.INTER_LINEAR)

    # Convert to tensor and normalize
    transform = transforms.Compose([
        transforms.ToTensor(),

        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    img_tensor = transform(Image.fromarray(img_resized)).unsqueeze(0)
    return img_tensor, img  # Return original BGR image for display

def get_depth_map(model, image_tensor):
    with torch.no_grad():
        if torch.cuda.is_available():
            image_tensor = image_tensor.cuda()

        # Forward pass
        prediction = model(image_tensor)

        # Normalize output
        output = prediction.cpu().numpy().squeeze()

        return output

def colorize_depth(depth, cmap=plt.cm.viridis):
    # Normalize depth to 0-1 range
    normalized_depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)

    # Apply colormap
    colored_depth = (cmap(normalized_depth) * 255).astype(np.uint8)[:, :, :3]
    return colored_depth

class RemoteStreamProcessor:
    def __init__(self):
        self.frame_count = 0
        self.active_tracks = set()

        # Load the depth estimation model
        print("Loading MiDaS model...")
        try:
            self.model = load_model()
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None

    async def process_track(self, track):
        global original_video_track
        self.active_tracks.add(track)
        print(f"🚨 New track received: {track.kind} (ID: {track.id})")

        frame_count = 0
        try:
            while True:
                frame = await track.recv()
                frame_count += 1
                self.frame_count += 1

                if frame_count % 30 == 0:  # Log every 30 frames
                    print(f"🔄 Processed {frame_count} frames from track {track.id}")

                self.analyze_frame(frame)

        except asyncio.CancelledError:
            print(f"⚠️ Track processing was cancelled for {track.id}")
        except Exception as e:
            print(f"❌ Track processing failed: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.active_tracks.discard(track)
            print(f"🔚 Track processing ended for {track.id}")

    def analyze_frame(self, frame):
        """Apply depth estimation to the received frame and display results"""
        if self.model is None:
            # If model failed to load, just display the original frame
            img = frame.to_ndarray(format='bgr24')
            cv2.imshow('Remote Video Stream', img)
            cv2.waitKey(1)
            return

        # Convert frame to ndarray format that OpenCV can work with
        img = frame.to_ndarray(format='bgr24')

        # Put frame in the original track's queue
        original_video_track.put_frame(img)

        try:
            # Process frame for depth estimation
            start_time = time.time()
            image_tensor, original_frame = process_image(img)

            # Get depth prediction
            depth_map = get_depth_map(self.model, image_tensor)

            # Normalize depth map to 0-255 for display
            normalized_depth = ((depth_map - depth_map.min()) / (depth_map.max() - depth_map.min()) * 255).astype(np.uint8)

            # Create a 3-channel grayscale image (BGR format)
            depth_bgr = cv2.cvtColor(normalized_depth, cv2.COLOR_GRAY2BGR)

            # Resize depth map to match original frame
            h, w = original_frame.shape[:2]
            depth_bgr_resized = cv2.resize(depth_bgr, (w, h))

            # Send the depth map to the video track
            depth_video_track.put_frame(depth_bgr_resized)

            # Show fps
            # fps = 1.0 / (time.time() - start_time)
            # cv2.putText(original_frame, f"FPS: {fps:.2f}", (10, 30),
            #            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Display original and depth side by side
            display_img = np.hstack((original_frame, depth_bgr_resized))
            cv2.imshow('Remote Depth Estimation (Original | Depth)', display_img)
        except Exception as e:
            print(f"Error processing frame for depth: {e}")
            # Display original frame if error occurs
            cv2.imshow('Remote Video Stream', img)

        cv2.waitKey(1)  # Wait 1ms to allow GUI to update

async def main():
    sio = socketio.AsyncClient(ssl_verify=False)

    # In your main() function:
    preferred_codecs = [
        # Configure VP8 for low bandwidth with temporal scaling
        RTCRtpCodecParameters(
            mimeType='video/VP8',
            clockRate=90000,
            parameters={"x-google-start-bitrate": "250", "x-google-min-bitrate": "100", "x-google-max-bitrate": "500"},
            rtcpFeedback=[
                {"type": "nack"},
                {"type": "nack", "parameter": "pli"},
                {"type": "ccm", "parameter": "fir"},
                {"type": "goog-remb"}  # Receiver estimated maximum bitrate
            ]
        ),
        # Add H.264 with constrained baseline profile for low bandwidth
        RTCRtpCodecParameters(
            mimeType='video/H264',
            clockRate=90000,
            parameters={"profile-level-id": "42e01f", "packetization-mode": "1", "level-asymmetry-allowed": "1"},
            rtcpFeedback=[
                {"type": "nack"},
                {"type": "nack", "parameter": "pli"}
            ]
        )
    ]

    # Create the peer connection with low bandwidth configuration
    ice_servers = [RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
    config = RTCConfiguration(iceServers=ice_servers)
    incoming_pc = RTCPeerConnection(configuration=config)
    for transceiver in incoming_pc.getTransceivers():
        transceiver.setCodecPreferences(preferred_codecs)

    outgoing_pc = RTCPeerConnection()
    processor = RemoteStreamProcessor()

    @sio.event
    async def availableOffers(offers):
        print(f"🎯 Found {len(offers)} available offers")
        for offer in offers:
            await handle_offer(offer)


    async def handle_offer(offer_data):
        try:
            # Only process offers from 'camera-module'
            if offer_data["offererUserName"] != 'camera-module':
                print(f"❌ Ignoring offer from unauthorized user: {offer_data['offererUserName']}")
                return

            await incoming_pc.setRemoteDescription(RTCSessionDescription(
                sdp=offer_data['offer']['sdp'],
                type=offer_data['offer']['type']
            ))

            answer = await incoming_pc.createAnswer()
            await incoming_pc.setLocalDescription(answer)

            # Use call() instead of emit() for proper timeout handling
            try:
                offer_ice_candidates = await sio.call(
                    "newAnswer",
                    {
                        "offererUserName": offer_data["offererUserName"],
                        "answer": {
                            "type": answer.type,
                            "sdp": answer.sdp
                        }
                    },
                    timeout=10  # Timeout in seconds
                )

                if offer_ice_candidates:
                    print(f"Received {len(offer_ice_candidates)} ICE candidates")
                    for candidate in offer_ice_candidates:
                        ice_candidate = aiortc.sdp.candidate_from_sdp(candidate["candidate"])
                        ice_candidate.sdpMid = candidate["sdpMid"]
                        ice_candidate.sdpMLineIndex = candidate["sdpMLineIndex"]
                        await incoming_pc.addIceCandidate(ice_candidate)

            except asyncio.TimeoutError:
                print("⌛ Timeout waiting for server acknowledgment")

        except Exception as e:
            print(f"Offer handling error: {str(e)}")

    @sio.event
    async def receivedIceCandidateFromServer(candidate):
        try:
            print("➕ Adding ICE candidate")
            # Use the from_sdp utility function
            ice_candidate = aiortc.sdp.candidate_from_sdp(candidate["candidate"])
            ice_candidate.sdpMid = candidate["sdpMid"]
            ice_candidate.sdpMLineIndex = candidate["sdpMLineIndex"]
            await incoming_pc.addIceCandidate(ice_candidate)
            await outgoing_pc.addIceCandidate(ice_candidate)
        except Exception as e:
            print(f"Error adding ICE candidate: {str(e)}")

    @incoming_pc.on("icecandidate")
    def on_ice_candidate(candidate):
        if candidate:
            print("❄️ Sending ICE candidate")
            asyncio.create_task(sio.emit("sendIceCandidateToSignalingServer", {
                "didIOffer": False,
                "iceUserName": "server-in",
                "iceCandidate": {
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex
                }
            }))

    @outgoing_pc.on("icecandidate")
    def on_ice_candidate_outgoing(candidate):
        if candidate:
            print("❄️ Sending ICE candidate")
            asyncio.create_task(sio.emit("sendIceCandidateToSignalingServer", {
                "didIOffer": False,
                "iceUserName": "server",
                "iceCandidate": {
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex
                }
            }))

    async def setup_forwarding():
        # Wait for the track to be ready
        #await original_video_track.wait_until_ready()
        print("🔄 Original video track has frames, creating offer...")
        await create_offer()

    @incoming_pc.on("track")
    def on_track(track):
        print("🎉 Got a track from the other peer! How exciting")
        print(f"Track details: {track}")

        # Only process video tracks
        if track.kind == "video":
            print("🎥 Processing video track...")
            asyncio.create_task(processor.process_track(track))

            # Make setup_forwarding more robust by handling errors
            async def safe_setup_forwarding():
                try:
                    print("⏳ Waiting for video track to be ready...")
                    #await original_video_track.wait_until_ready()
                    print("🔄 Original video track has frames, creating offer...")
                    await create_offer()
                except Exception as e:
                    print(f"❌ Error in setup_forwarding: {e}")

            # Use create_task with explicit variable to avoid garbage collection
            setup_task = asyncio.create_task(safe_setup_forwarding())
        else:
            print(f"📢 Ignoring non-video track: {track.kind}")


    @incoming_pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state is {incoming_pc.connectionState}")
        if incoming_pc.connectionState == "failed":
            await incoming_pc.close()
            print("❌ Connection failed, closing peer connection")

    @outgoing_pc.on("connectionstatechange")
    async def on_outgoing_connectionstatechange():
        print(f"🔌 Outgoing connection state is {outgoing_pc.connectionState}")
        if outgoing_pc.connectionState == "connected":
            print("✅ Successfully forwarding video")
        elif outgoing_pc.connectionState == "failed":
            print("❌ Outgoing connection failed")

    async def create_peer_connection():

        @incoming_pc.on("icecandidate")
        def on_icecandidate(candidate):
            if candidate:
                asyncio.create_task(send_ice_candidate(candidate))

        @incoming_pc.on("track")
        def on_track(track):
            print(f"Received {track.kind} track")

    async def send_ice_candidate(candidate):
        await sio.emit('sendIceCandidateToSignalingServer', {
            'didIOffer': True,  # Change this based on your role (offerer/answerer)
            'iceUserName': 'server',
            'iceCandidate': {
                'candidate': candidate.candidate,
                'sdpMid': candidate.sdpMid,
                'sdpMLineIndex': candidate.sdpMLineIndex
            }
        })

    async def create_offer():
        global original_video_track
        print("📤 Adding track to outgoing peer connection...")
        outgoing_pc.addTrack(original_video_track)
        outgoing_pc.addTrack(depth_video_track)

        # Create and set local description
        print("📝 Creating outgoing offer...")
        offer = await outgoing_pc.createOffer()
        await outgoing_pc.setLocalDescription(offer)

        # Send offer to signaling server
        print("📡 Sending offer to signaling server...")
        await sio.emit('newOffer', {
            'sdp': outgoing_pc.localDescription.sdp,
            'type': outgoing_pc.localDescription.type
        })
        print("💬 Offer sent, waiting for answer...")

    @sio.event
    async def answerResponse(data):
        print(f"📨 Received answer to my offer from {data.get('answererUserName', 'unknown')}")
        try:
            await outgoing_pc.setRemoteDescription(RTCSessionDescription(
                sdp=data['answer']['sdp'],
                type=data['answer']['type']
            ))
            print("📥 Set remote description for outgoing PC")
        except Exception as e:
            print(f"❌ Error setting remote description: {e}")

    @sio.event
    async def connect():
        print("✅ Connected to signaling server")
        await sio.emit("requestOffers")
        await create_peer_connection()

    try:
        await sio.connect(
            'https://192.168.0.151:8181/',
            auth={'userName': 'server', 'password': 'x'},
            transports=['websocket']
        )
        await sio.wait()
    except asyncio.CancelledError:
        print("🛑 Asyncio task cancelled")
        await outgoing_pc.close()
        await incoming_pc.close()
        await sio.disconnect()
    except Exception as e:
        print(f"Connection error: {str(e)}")

        await outgoing_pc.close()
        await incoming_pc.close()
        await sio.disconnect()
        cv2.destroyAllWindows()  # Clean up OpenCV windows

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 User interrupted execution")
    finally:
        # Final cleanup
        cv2.destroyAllWindows()
        cv2.waitKey(1)  # Process any OpenCV events

        # Force exit if needed
        import os, sys
        os._exit(0)  # Force exit in case OpenCV threads are still running
