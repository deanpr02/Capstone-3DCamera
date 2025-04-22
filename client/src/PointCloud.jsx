import { useRef, useEffect, useState, useMemo } from 'react'
import { Points, OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'

import './PointCloud.css'

export default function PointCloud({ videoStream, depthStream }) {
  const videoRef = useRef(null);
  const depthVideoRef = useRef(null);
  const canvasRef = useRef(null);
  const depthCanvasRef = useRef(null);
  const [width, setWidth] = useState(0);
  const [height, setHeight] = useState(0);
  const [depthSize, setDepthSize] = useState({ width: 0, height: 0 });
  const [isPlaying, setIsPlaying] = useState(false);
  
  // Raw data refs to avoid unnecessary state updates
  const pixelDataRef = useRef(null);
  const depthDataRef = useRef(null);
  const frameCountRef = useRef(0);
  
  // Set up video element with the stream
  useEffect(() => {
    console.log('depth')
    console.log(depthStream)
    console.log(videoStream)
    if (!videoStream || !videoRef.current) return;
    
    videoRef.current.srcObject = videoStream;
    depthVideoRef.current.srcObject = depthStream;
    //if(depthStream && depthVideoRef.current){
    //  depthVideoRef.current.srcObject = depthStream;
    //}
    
    // Attempt to play the video
    const playVideo = async () => {
      try {
        const playPromises = [];
        if(videoRef.current){
          playPromises.push(videoRef.current.play());
        }

        if(depthStream && depthVideoRef.current){
          playPromises.push(depthVideoRef.current.play());
        }

        await Promise.all(playPromises);
        setIsPlaying(true);
      } catch (err) {
        console.error("Error playing video in PointCloud:", err);
      }
    };
    
    playVideo();
    
    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.srcObject = null;
      }

      if(depthVideoRef.current){
        depthVideoRef.current.pause();
        depthVideoRef.current.srcObject = null;
      }
    };
  }, [videoStream, depthStream]);
  
  // Process video frames
  useEffect(() => {
    if (!isPlaying || !videoRef.current || !canvasRef.current) return;
    
    const video = videoRef.current;
    const depthVideo = depthVideoRef.current;
    const canvas = canvasRef.current;
    const depthCanvas = depthCanvasRef.current;
    const ctx = canvas.getContext('2d');
    const depthCtx = depthCanvas.getContext('2d');
    
    // Set initial dimensions
    if (video.videoWidth && video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      setWidth(video.videoWidth);
      setHeight(video.videoHeight);
    }
    
    if (depthVideo && depthVideo.videoWidth && depthVideo.videoHeight) {
      depthCanvas.width = depthVideo.videoWidth;
      depthCanvas.height = depthVideo.videoHeight;
      setDepthSize({
        width: depthVideo.videoWidth,
        height: depthVideo.videoHeight
      });
    }
    
    let animationId;
    
    const processFrame = () => {
      if (video.readyState < 2) {
        animationId = requestAnimationFrame(processFrame);
        return;
      }
      
      // Only process every 2nd frame to improve performance
      frameCountRef.current++;
      if (frameCountRef.current % 2 === 0) {
        // Update canvas dimensions if they change
        if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          setWidth(video.videoWidth);
          setHeight(video.videoHeight);
        }
        
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        pixelDataRef.current = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        
        if (depthVideo && depthVideo.readyState >= 2) {
          depthCtx.drawImage(depthVideo, 0, 0, depthCanvas.width, depthCanvas.height);
          depthDataRef.current = depthCtx.getImageData(0, 0, depthCanvas.width, depthCanvas.height).data;
        }
      }
      
      animationId = requestAnimationFrame(processFrame);
    };
    
    processFrame();
    
    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isPlaying]);
  
  return (
    <div className='point-cloud-container'>
      <video 
        ref={videoRef} 
        autoPlay 
        playsInline 
        muted
        style={{ display: 'none' }}
      />
      <video 
        ref={depthVideoRef} 
        autoPlay 
        playsInline 
        muted
        style={{ display: 'none' }}
      />
      <Canvas style={{ height: '80vh', width: '80vh' }} 
             camera={{ position: [0, 0, -1], near: 0.1, far: 1000, zoom: 1 }}>
        {width > 0 && height > 0 && (
          <CloudCanvas 
            pixelDataRef={pixelDataRef} 
            depthDataRef={depthDataRef} 
            width={width} 
            height={height} 
            depthWidth={depthSize.width} 
            depthHeight={depthSize.height}
          />
        )}
        <OrbitControls />
      </Canvas>
      <canvas ref={canvasRef} hidden />
      <canvas ref={depthCanvasRef} hidden/>
    </div>
  );
}

function CloudCanvas({ pixelDataRef, depthDataRef, width, height, depthWidth, depthHeight }) {
  const pointsRef = useRef();
  const frameCountRef = useRef(0);
  const updateCounterRef = useRef(0);

  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(width * height * 3);
    const colors = new Float32Array(width * height * 3);
    
    // Pre-calculate positions to avoid doing this in the animation loop
    const aspect = width / height;
    const xScale = aspect > 1 ? 1 : aspect;
    const yScale = aspect < 1 ? 1 : 1/aspect;
    
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = y * width + x;
        const i3 = idx * 3;
        
        positions[i3] = (x / width - 0.5) * xScale;
        positions[i3+1] = (0.5 - y / height) * yScale;
        positions[i3+2] = 0; // Will be updated in the frame loop
      }
    }
    
    return { positions, colors };
  }, [width, height]);

  // Use a more efficient update strategy
  useFrame(() => {
    if (!pointsRef.current || !pixelDataRef.current || !depthDataRef.current) return;
    
    frameCountRef.current++;
    
    // Only update every 3rd frame to improve performance
    //if (frameCountRef.current % 3 !== 0) return;
    
    updateCounterRef.current++;
    const updateFullGeometry = updateCounterRef.current % 30 === 0; // Full update every 30 updates
    
    const geometry = pointsRef.current.geometry;
    const colorArray = geometry.attributes.color.array;
    const positionArray = geometry.attributes.position.array;
    
    const pixelData = pixelDataRef.current;
    const depthData = depthDataRef.current;
    
    const zScale = 1.0;
    
    // Use a sampling approach to update only a subset of points each frame
    const samplingRate = updateFullGeometry ? 1 : 1; // Update every 10th pixel normally
    
    for (let y = 0; y < height; y += samplingRate) {
      for (let x = 0; x < width; x += samplingRate) {
        const idx = y * width + x;
        const i3 = idx * 3;
        const i4 = idx * 4;
        
        // Update Z position from depth data
        if (depthData && depthWidth > 0 && depthHeight > 0) {
          const depthX = Math.floor((x / width) * depthWidth);
          const depthY = Math.floor((y / height) * depthHeight);
          const depthIdx = (depthY * depthWidth + depthX) * 4;
          
          if (depthIdx < depthData.length) {
            positionArray[i3+2] = 1 - (depthData[depthIdx] / 255) * zScale;
          }
        }
        
        // Update color
        if (i4 + 2 < pixelData.length) {
          const r = Math.pow(pixelData[i4] / 255, 2.2);
              const g = Math.pow(pixelData[i4+1] / 255, 2.2);
              const b = Math.pow(pixelData[i4+2] / 255, 2.2);
          
          colorArray[i3] = r;
          colorArray[i3+1] = g;
          colorArray[i3+2] = b;
        }
      }
    }
    
    // Only mark attributes as needing update when we've actually changed them
    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.color.needsUpdate = true;
    
    // Only compute bounding sphere occasionally
    if (updateFullGeometry) {
      geometry.computeBoundingSphere();
    }
  });

  return (
    <Points ref={pointsRef} positions={positions} colors={colors}>
      <pointsMaterial
        vertexColors
        size={0.2}
        sizeAttenuation={false}
        transparent
        opacity={1.0}
      />
    </Points>
  );
}
