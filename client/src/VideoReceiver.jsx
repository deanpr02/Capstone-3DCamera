import React, { useState, useEffect, useRef } from "react";
import io from "socket.io-client";
import PointCloud from "./PointCloud";
import './VideoReceiver.css'

export default function VideoReceiver() {
    const [userName] = useState(`Rob-${Math.floor(Math.random() * 100000)}`);
    const password = "x";
    const remoteVideoRef = useRef(null);
    const depthVideoRef = useRef(null);
    const socketRef = useRef(null); // Use ref for socket
    const peerConnectionRef = useRef(null); // Use ref for peerConnection
    const remoteStreamRef = useRef(new MediaStream());
    const [remoteStreamKey, setRemoteStreamKey] = useState(0);
    const depthStreamRef = useRef(new MediaStream());
    const [depthStreamKey, setDepthStreamKey] = useState(0);
    const [isStreamReady,setIsStreamReady] = useState(false);
    const [isDepthStreamReady,setIsDepthStreamReady] = useState(false);
    const [didIOffer, setDidIOffer] = useState(false);
    const [isLoaded,setIsLoaded] = useState(false);
    const receivedTracks = useRef([]);
  
    const peerConfiguration = {
      iceServers: [
        {
          urls: ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"],
          iceTransportPolicy: 'all'          
        },
      ],
    };

    const ALLOWED_USERNAME = 'camera-module'
  
    // Initialize socket connection
    useEffect(() => {
      const newSocket = io.connect('https://192.168.0.151:8181', {
        auth: { userName, password },
        rejectUnauthorized: false,
      });
      //console.log(socketRef.current)
      socketRef.current = newSocket; // Store in ref
      console.log(socketRef.current)
      newSocket.on("availableOffers", (offers) => {
        console.log(offers)
        const validOffer = offers.find(offer => {
          // Check for both legacy and current properties
          const offerUserName = offer.offererUserName || offer.userName;
          return offerUserName === ALLOWED_USERNAME;
        });

        if (validOffer) {
          answerOffer(validOffer);
        } else {
          console.warn('No valid offers found for', ALLOWED_USERNAME);
        }
        //if (offers.length > 0) answerOffer(offers[offers.length-1]);
        
      });
  
      newSocket.on("newOfferAwaiting", (offerObj) => {
        if (offerObj.userName === ALLOWED_USERNAME) { // 👈 Add check here
          answerOffer(offerObj[0]);
        }
        //answerOffer(offerObj[0]);
      });
  
      newSocket.on("answerResponse", addAnswer);
      newSocket.on("receivedIceCandidateFromServer", addNewIceCandidate);
      newSocket.on("reconnect", () => {
        console.log("Reconnected to signaling server");
        socketRef.current.emit("requestAvailableOffers");
      });
  
      return () => {
        newSocket.disconnect();
        if(peerConnectionRef.current){
          peerConnectionRef.current.close();
          peerConnectionRef.current = null;
        }
        if(socketRef.current){
          socketRef.current.disconnect();
          socketRef.current = null;
        }
        if(remoteVideoRef.current){
          remoteVideoRef.current.srcObject = null;
          remoteVideoRef.current = null;
        }
        if(depthVideoRef.current){
          depthVideoRef.current.srcObject = null;
          depthVideoRef.current = null;
        }
      };
    }, [userName]);
  
    // Create peer connection
    const createPeerConnection = async (offerObj) => {
      try {
        const pc = new RTCPeerConnection(peerConfiguration);
        
        pc.addEventListener("icecandidate", (e) => {
          if (e.candidate && socketRef.current) { // Check socket exists
            socketRef.current.emit("sendIceCandidateToSignalingServer", {
              iceCandidate: e.candidate,
              iceUserName: userName,
              didIOffer,
            });
          }
        });

        pc.addEventListener('iceconnectionstatechange', () => {
          console.log('ICE connection state:', pc.iceConnectionState);
          if (pc.iceConnectionState === 'disconnected') {
            pc.restartIce();
          }
        });
  
        pc.addEventListener("track", (e) => {
          //const stream = e.streams[0];
          console.log(e.track)

          if (e.track.kind !== 'video') return;

          receivedTracks.current.push(e.track);
          
          
          if (receivedTracks.current.length === 1) {
            const mainStream = new MediaStream([e.track]);
            remoteStreamRef.current = mainStream;
            remoteVideoRef.current.srcObject = mainStream;
            setIsStreamReady(true);
            setRemoteStreamKey(prev => prev + 1);
            console.log("Set main video stream");
          } 
          // Second video track goes to the depth video
          else if (receivedTracks.current.length === 2) {
            const depthStream = new MediaStream([e.track]);
            depthStreamRef.current = depthStream;
            depthVideoRef.current.srcObject = depthStream;
            setIsDepthStreamReady(true);
            setDepthStreamKey(prev => prev + 1);
            console.log("Set depth video stream");
          }
          //remoteStreamRef.current = stream;
          //remoteVideoRef.current.srcObject = stream;
          
          //setIsStreamReady(true);
          //setRemoteStreamKey(prev => prev+1);

          //remoteVideoRef.current.play().catch(err =>
          //  console.error('video play failed',err)
          //)
        });
  
        if (offerObj?.offer) {
          await pc.setRemoteDescription(offerObj.offer);
        }
  
        peerConnectionRef.current = pc; // Store in ref
        return pc;
  
      } catch (err) {
        console.error("Peer connection error:", err);
        throw err;
      }
    };
  
    // Answer offer with proper reference handling
    const answerOffer = async (offerObj) => {
      try {
        //if(peerConnectionRef.current){
        //  console.log('Closing existing peer connection')
        //  peerConnectionRef.current.close();
        //  peerConnectionRef.current = null;
        //}

        const pc = await createPeerConnection(offerObj);
        
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
  
        if (socketRef.current) { // Check socket exists
          socketRef.current.emit("newAnswer", {
            ...offerObj,
            answer: answer
          }, (offerIceCandidates) => {
            offerIceCandidates.forEach(candidate => 
              pc.addIceCandidate(candidate)
            );
          });
        }
      } catch (err) {
        console.error("Answer error:", err);
      }
    };

  // Handle answers
  const addAnswer = async (offerObj) => {
    try {
      if (!peerConnectionRef.current || !offerObj?.answer) {
        throw new Error("Missing peer connection or answer");
      }
      await peerConnectionRef.current.setRemoteDescription(offerObj.answer);
    } catch (err) {
      console.error("Error adding answer:", err);
    }
  };

  // Handle ICE candidates
  const addNewIceCandidate = async (iceCandidate) => {
    try {
      if (!peerConnectionRef.current) {
        console.warn("No peer connection for ICE candidate");
        return;
      }

      await peerConnectionRef.current.addIceCandidate(iceCandidate);
      console.log(peerConnectionRef.current)
    } catch (err) {
      console.error("Error adding ICE candidate:", err);
    }
  };

  return (
    <div className='video-receiver-container'>
    <h1></h1>
    <div className='cloud-container'>
      <video 
        ref={remoteVideoRef} 
        autoPlay 
        playsInline 
        muted
        style={{ width: "50vh", maxWidth: "50vh", height:'50vh'}}
      />
      <video 
        ref={depthVideoRef} 
        autoPlay 
        playsInline 
        muted
        style={{ width: "50vh", maxWidth: "50vh", height:'50vh'}}
      />
      {isStreamReady && remoteStreamRef.current && depthStreamRef.current && 
      <PointCloud videoStream={remoteStreamRef.current} depthStream={depthStreamRef.current}/>
      }
    </div>
  </div>
  );
}
