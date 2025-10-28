import { useState, useEffect, useRef } from "react";
import styled from "styled-components";

export default function App() {
  const videoRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    async function startCamera() {
      try {
        // Try local webcam first
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
          setIsLoaded(true);
        }
      } catch (err) {
        console.error("Webcam not available, falling back to server stream", err);
        // Fallback to your Render-deployed video URL
        if (videoRef.current) {
          videoRef.current.src = "https://colorpickernijiji.onrender.com/video";
          videoRef.current.onloadeddata = () => setIsLoaded(true);
          videoRef.current.play();
        }
      }
    }

    startCamera();
  }, []);

  return (
    <PageContainer>
      <HeaderBar>🎨 Real-Time Color Detector</HeaderBar>

      {!isLoaded && <LoadingText>Connecting to camera...</LoadingText>}

      <VideoFeed ref={videoRef} autoPlay muted playsInline />

      <Footer>
        made with 💖 by <span>Jiji</span>
      </Footer>
    </PageContainer>
  );
}

//
// 🌈 Styled Components
//
const PageContainer = styled.div`
  position: relative;
  height: 100dvh;
  width: 100vw;
  overflow: hidden;
  background: black;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  font-family: "Poppins", sans-serif;
`;

const HeaderBar = styled.div`
  position: absolute;
  top: 0;
  width: 100%;
  padding: 12px 0;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  color: white;
  font-size: clamp(1.2rem, 4vw, 1.8rem);
  font-weight: 700;
  text-align: center;
  text-shadow: 0 0 8px rgba(255, 105, 180, 0.8);
  z-index: 10;
`;

const VideoFeed = styled.video`
  width: 100%;
  height: 100%;
  object-fit: cover;
  background-color: black;
`;

const LoadingText = styled.div`
  color: #f9a8d4;
  font-size: 1.1rem;
  text-shadow: 0 0 8px rgba(255, 182, 193, 0.6);
`;

const Footer = styled.footer`
  position: absolute;
  bottom: 1rem;
  width: 100%;
  text-align: center;
  color: #f9a8d4;
  text-shadow: 0 0 6px rgba(255, 182, 193, 0.6);
  font-size: 0.9rem;
  z-index: 10;

  span {
    color: #ec4899;
    font-weight: 600;
  }
`;
