import { useState, useEffect, useRef } from "react";
import styled from "styled-components";

export default function App() {
  const videoRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [facingMode, setFacingMode] = useState("user");

  // Dynamically choose backend URL based on environment
  const backendUrl =
    window.location.hostname === "localhost"
      ? "http://127.0.0.1:8000/video"
      : "https://colorpickernijiji.onrender.com/video";

  // Detect mobile device
  useEffect(() => {
    const detectMobile = () => {
      const isTouchDevice = "ontouchstart" in window || navigator.maxTouchPoints > 0;
      const isSmallScreen = window.innerWidth < 900;
      setIsMobile(isTouchDevice && isSmallScreen);
    };
    detectMobile();
    window.addEventListener("resize", detectMobile);
    return () => window.removeEventListener("resize", detectMobile);
  }, []);

  // Start camera or fallback to backend stream
  useEffect(() => {
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode },
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setIsLoaded(true);
        }
      } catch (err) {
        console.warn("⚠️ Local camera not available. Falling back to backend stream:", backendUrl);
        if (videoRef.current) {
          videoRef.current.srcObject = null; // Ensure no old streams remain
          videoRef.current.src = backendUrl;
          videoRef.current.onloadeddata = () => setIsLoaded(true);
          videoRef.current.play().catch(() => {});
        }
      }
    }

    startCamera();

    // Stop camera tracks when component unmounts
    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach((track) => track.stop());
      }
    };
  }, [facingMode, backendUrl]);

  const handleFlipCamera = () => {
    if (!isMobile) return;
    setFacingMode((prev) => (prev === "user" ? "environment" : "user"));
  };

  return (
    <PageContainer>
      <HeaderBar>🎨 Real-Time Color Detector</HeaderBar>

      {!isLoaded && <LoadingText>Connecting to camera...</LoadingText>}

      <VideoFeed ref={videoRef} autoPlay muted playsInline />

      <FlipButton
        onClick={handleFlipCamera}
        disabled={!isMobile}
        title={isMobile ? "Flip Camera" : "Flip unavailable on desktop"}
      >
        🔄
      </FlipButton>

      <Footer>
        made with 💖 by <span>Jiji</span>
      </Footer>
    </PageContainer>
  );
}

//
// 🌸 Styled Components
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

const FlipButton = styled.button`
  position: absolute;
  bottom: 4.5rem;
  right: 1.5rem;
  background: ${(props) => (props.disabled ? "#555" : "#ec4899")};
  color: white;
  border: none;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  font-size: 1.4rem;
  box-shadow: 0 0 15px rgba(236, 72, 153, 0.6);
  cursor: ${(props) => (props.disabled ? "not-allowed" : "pointer")};
  transition: 0.3s ease;
  z-index: 20;

  &:hover {
    transform: ${(props) => (props.disabled ? "none" : "scale(1.1)")};
  }
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
