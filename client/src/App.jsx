import { useState } from 'react'
import VideoReceiver from './VideoReceiver'
import PointCloud from './PointCloud'

import vid from './sample.mp4'

import "./App.css"

function App() {
  

  return (
    <>
    <div className='client-container'>
        <VideoReceiver/>
    </div>
    </>
  )
}

export default App
