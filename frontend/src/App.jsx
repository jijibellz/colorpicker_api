import { useEffect, useRef, useState } from "react";
import styled from "styled-components";

export default function App() {
  const videoRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [facingMode, setFacingMode] = useState("user");

  const backendBaseUrl = import.meta.env.VITE_API_URL;

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

  useEffect(() => {
    let pc;

    const startWebRTC = async () => {
      pc = new RTCPeerConnection({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" }, // mandatory for deployed
        ],
      });

      // capture local webcam
      const localStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode },
        audio: false,
      });

      // add local tracks to peer connection
      localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

      // when backend returns processed track
      pc.ontrack = event => {
        if (videoRef.current) {
          videoRef.current.srcObject = event.streams[0];
          videoRef.current.play().catch(() => {});
          setIsLoaded(true);
        }
      };

      pc.oniceconnectionstatechange = () => {
        console.log("ICE connection state:", pc.iceConnectionState);
      };

      // create offer and send to backend
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const res = await fetch(`${backendBaseUrl}/offer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sdp: offer.sdp, type: offer.type }),
      });

      const answer = await res.json();
      await pc.setRemoteDescription(answer);
    };

    startWebRTC();

    return () => {
      pc?.close();
    };
  }, [facingMode]);

  const handleFlipCamera = () => {
    if (!isMobile) return;
    setFacingMode(prev => (prev === "user" ? "environment" : "user"));
  };

  return (
    <PageContainer>
      <HeaderBar>🎨 Real-Time Color + Object Detector</HeaderBar>
      {!isLoaded && <LoadingText>Connecting to camera...</LoadingText>}
      <VideoBox>
        <VideoFeed ref={videoRef} autoPlay playsInline muted />
      </VideoBox>
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
  background: #0b0b0b;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  font-family: "Poppins", sans-serif;
  overflow: hidden;
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

const VideoBox = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #ff8ac6;
  box-shadow: 0 0 10px rgba(255, 105, 180, 0.5);
`;

const VideoFeed = styled.video`
  width: 640px;
  height: 480px;
  border-radius: 12px;
`;

const Canvas = styled.canvas`
  position: absolute;
  top: 0;
  left: 0;
`;

const LoadingText = styled.div`
  color: #f9a8d4;
  font-size: 1.1rem;
  text-shadow: 0 0 8px rgba(255, 182, 193, 0.6);
`;

const ResultsPanel = styled.div`
  margin-top: 1rem;
  color: white;
  text-align: center;
  max-width: 90%;
  h3 {
    color: #ff8ac6;
    margin-bottom: 0.4rem;
  }
`;

const ColorPalette = styled.div`
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 0.5rem;
`;

const ColorBox = styled.div`
  width: 30px;
  height: 30px;
  border-radius: 6px;
  border: 1px solid #fff3;
  cursor: pointer;
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
  bottom: 0.4rem;
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
