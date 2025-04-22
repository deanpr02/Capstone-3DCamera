import asyncio
import socketio
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription, RTCIceCandidate
import numpy as np

class FrameReceiver(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.frame_count = 0

    async def recv(self):
        try:
            frame = await super().recv()
            self.frame_count += 1
            
            # Print basic frame info
            print(f"\n📦 Frame {self.frame_count}")
            print(f"  Resolution: {frame.width}x{frame.height}")
            print(f"  Format: {frame.format.name}")
            print(f"  PTS: {frame.pts}")

            # Convert to bytes and print sample data
            if frame.format.name in ['yuv420p', 'nv12']:
                y_plane = frame.planes[0]
                bytes_data = bytes(y_plane)
                print(f"  Y Plane First 16 bytes: {bytes_data[:16].hex()}")
                
                # Print 8x8 pixel grid from top-left corner
                print("\n  Sample Y Channel 8x8 Grid:")
                y_data = np.frombuffer(bytes_data, dtype=np.uint8)
                y_data = y_data.reshape((frame.height, frame.width))
                for row in y_data[:8, :8]:
                    print("   ", " ".join(f"{pixel:03d}" for pixel in row))

            elif frame.format.name == 'rgb24':
                bytes_data = bytes(frame.planes[0])
                print(f"  First 24 RGB bytes: {bytes_data[:24].hex()}")

            return frame
            
        except Exception as e:
            print(f"Frame reception error: {str(e)}")
            raise

class RemoteStreamProcessor:
    def __init__(self):
        self.frame_count = 0
        self.active_tracks = set()

    async def process_track(self, track):
        """Continuously process frames from an incoming media track"""
        self.active_tracks.add(track)
        print(f"🚨 New track received: {track.kind} (ID: {track.id})")
        
        try:
            while True:
                frame = await track.recv()
                self.frame_count += 1
                self.analyze_frame(frame)
                
        except Exception as e:
            print(f"Track processing failed: {str(e)}")
        finally:
            self.active_tracks.discard(track)

    def analyze_frame(self, frame):
        """Detailed frame analysis matching JavaScript console output"""
        # Basic frame info
        print(f"\n📦 Frame {self.frame_count}")
        print(f"  Resolution: {frame.width}x{frame.height}")
        print(f"  Format: {frame.format.name}")
        print(f"  PTS: {frame.pts}")

        # Convert to bytes and print sample data
        if frame.format.name in ['yuv420p', 'nv12']:
            y_plane = frame.planes[0]
            bytes_data = bytes(y_plane)
            print(f"  Y Plane First 16 bytes: {bytes_data[:16].hex()}")
            
            # Print 8x8 pixel grid from top-left corner
            print("\n  Sample Y Channel 8x8 Grid:")
            y_data = np.frombuffer(bytes_data, dtype=np.uint8)
            y_data = y_data.reshape((frame.height, frame.width))
            for row in y_data[:8, :8]:
                print("   ", " ".join(f"{pixel:03d}" for pixel in row))

        elif frame.format.name == 'rgb24':
            bytes_data = bytes(frame.planes[0])
            print(f"  First 24 RGB bytes: {bytes_data[:24].hex()}")

            
async def main():
    sio = socketio.AsyncClient(ssl_verify=False)
    pc = RTCPeerConnection()
    pc._canOffer = False  # Ensure this client can't create offers
    # receiver = FrameReceiver()
    processor = RemoteStreamProcessor()
    # pc.addTrack(receiver)

    @sio.event
    async def connect():
        print("✅ Connected to signaling server")
        await sio.emit("requestOffers")

    @sio.event
    async def availableOffers(offers):
        print(f"🎯 Found {len(offers)} available offers")
        for offer in offers:
            await handle_offer(offer)

    @sio.event
    async def newOfferAwaiting(offer_list):
        print("📨 New offer received")
        if offer_list:
            await handle_offer(offer_list[0])

    async def handle_offer(offer_data):
        if(offer_data["offererUserName"] != "camera-module"):
            print(f"❌ Ignoring offer from {offer_data['offererUserName']}")
            return
        try:
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=offer_data['offer']['sdp'],
                type=offer_data['offer']['type']
            ))
            
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
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
                        await pc.addIceCandidate(RTCIceCandidate(
                            candidate=candidate["candidate"],
                            sdpMid=candidate["sdpMid"],
                            sdpMLineIndex=candidate["sdpMLineIndex"]
                        ))
                        
            except asyncio.TimeoutError:
                print("⌛ Timeout waiting for server acknowledgment")
                
        except Exception as e:
            print(f"Offer handling error: {str(e)}")

    @sio.event
    async def receivedIceCandidateFromServer(candidate):
        try:
            print("➕ Adding ICE candidate")
            await pc.addIceCandidate(RTCIceCandidate(
                candidate=candidate["candidate"],
                sdpMid=candidate["sdpMid"],
                sdpMLineIndex=candidate["sdpMLineIndex"]
            ))
        except Exception as e:
            print(f"Error adding ICE candidate: {str(e)}")

    @pc.on("icecandidate")
    def on_ice_candidate(candidate):
        if candidate:
            print("❄️ Sending ICE candidate")
            asyncio.create_task(sio.emit("sendIceCandidateToSignalingServer", {
                "didIOffer": False,
                "iceUserName": "recv-client",
                "iceCandidate": {
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex
                }
            }))
    @pc.on("track")
    def on_track(track):
        print("🎉 Got a track from the other peer! How exciting")
        print(f"Track details: {track}")
        asyncio.create_task(processor.process_track(track))

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"Connection state is {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
            print("❌ Connection failed, closing peer connection")

    try:
        await sio.connect(
            'https://192.168.0.151:8181',
            auth={'userName': 'recv-client', 'password': 'x'},
            transports=['websocket']
        )
        await sio.wait()
    except asyncio.CancelledError:
        print("🛑 Asyncio task cancelled")
    except Exception as e:
        print(f"Connection error: {str(e)}")
    finally:
        await pc.close()
        await sio.disconnect()
        print("🔌 Connection cleanly closed")
    
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 User interrupted execution")
