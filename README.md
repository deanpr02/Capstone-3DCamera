3D Camera Capstone

Dean Prach
Nathan Anderson
Arvin Edouard


===About the Project=== </br>
The project consists of three core components. The first component of the project is the sender portion, otherwise known as the camera module. This section of the project controls the input to the system, ultimately determining what will be displayed for the client. The module uses a USB camera; it also works using other camera devices such as webcams, and sends the video stream over the WebRTC protocol using a custom implementation and signalling server. This video stream is then sent to the next portion of the project, which is the server. The server is in control of estimating the depth of each frame in the video stream and then sending both the original video stream containing the RGB values and the depth stream, which encapsulates the depth information for each pixel within another video stream. The server calculates the depth of the video stream using a monocular depth estimation neural network, MiDas. The neural network is essentially trained from a large amount of images to learn depth within images based on the sizes, shapes, and other characteristics of objects in the image. With both of these streams, the server then simultaneously sends the video and depth streams to the client over the WebRTC protocol. The last section of the project is the client, which is in control of receiving both of these streams, combining their information, and rendering a 3D point cloud that contains the valid geometry of the video stream combined with the depth from the depth estimation for each pixel, giving the video stream its three-dimensional look. The client is a web application built using the JavaScript library React JS, and uses the library Three.js for its three-dimensional rendering of the scene onto the browser.




https://github.com/user-attachments/assets/f16d4287-ca80-42f8-bc9f-54fa7ba9d639

