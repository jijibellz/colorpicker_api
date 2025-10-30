import { useState, useEffect, useRef } from "react";
import styled from "styled-components";

export default function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [facingMode, setFacingMode] = useState("user");
  const [useBackendStream, setUseBackendStream] = useState(false);
  const [analysis, setAnalysis] = useState(null);

  // ✅ Automatically choose backend
  const backendBaseUrl =
    window.location.hostname.includes("localhost")
      ? "http://127.0.0.1:8000"
      : "https://colorpickernijiji.onrender.com";

  // ✅ Detect if device is mobile
  useEffect(() => {
    const detectMobile = () => {
      const isTouchDevice =
        "ontouchstart" in window || navigator.maxTouchPoints > 0;
      const isSmallScreen = window.innerWidth < 900;
      setIsMobile(isTouchDevice && isSmallScreen);
    };
    detectMobile();
    window.addEventListener("resize", detectMobile);
    return () => window.removeEventListener("resize", detectMobile);
  }, []);

  // ✅ Try to access local camera
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
          setUseBackendStream(false);
        }
      } catch (err) {
        console.warn("⚠️ Local camera not available, fallback:", err);
        setUseBackendStream(true);
        setIsLoaded(true);
      }
    }

    startCamera();

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach((track) => track.stop());
      }
    };
  }, [facingMode]);

  // ✅ Capture a frame and send to backend every second
  useEffect(() => {
    if (useBackendStream) return; // no local camera, skip

    const interval = setInterval(async () => {
      if (!videoRef.current || !canvasRef.current) return;

      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      const video = videoRef.current;

      // Draw current frame to canvas
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Convert to blob and send to backend
      canvas.toBlob(async (blob) => {
        if (!blob) return;

        const formData = new FormData();
        formData.append("file", blob, "frame.jpg");

        try {
          const res = await fetch(`${backendBaseUrl}/analyze`, {
            method: "POST",
            body: formData,
          });

          const data = await res.json();
          setAnalysis(data);
        } catch (error) {
          console.error("❌ Error sending frame:", error);
        }
      }, "image/jpeg");
    }, 1500); // every 1.5 seconds

    return () => clearInterval(interval);
  }, [useBackendStream, backendBaseUrl]);

  // ✅ Flip camera (mobile only)
  const handleFlipCamera = () => {
    if (!isMobile) return;
    setFacingMode((prev) => (prev === "user" ? "environment" : "user"));
  };

  return (
    <PageContainer>
      <HeaderBar>🎨 Real-Time Color + Object Detector</HeaderBar>

      {!isLoaded && <LoadingText>Connecting to camera...</LoadingText>}

      {useBackendStream ? (
        <FallbackBox>
          <p>🚫 Local camera unavailable</p>
          <p>Try using your device camera instead!</p>
        </FallbackBox>
      ) : (
        <>
          <VideoFeed ref={videoRef} autoPlay muted playsInline />
          <HiddenCanvas ref={canvasRef} />
        </>
      )}

      <FlipButton
        onClick={handleFlipCamera}
        disabled={!isMobile}
        title={isMobile ? "Flip Camera" : "Flip unavailable on desktop"}
      >
        🔄
      </FlipButton>

      {/* 🎨 Results display */}
      {analysis && (
        <ResultsPanel>
          <h3>🎨 Scene Colors</h3>
          <ColorRow>
            {analysis.scene_colors?.map((c, idx) => (
              <ColorBox key={idx} color={c.hex}>
                <span>{c.name}</span>
                <small>{c.hex}</small>
              </ColorBox>
            ))}
          </ColorRow>

          <h3>🧠 Detected Objects</h3>
          <ObjectList>
            {analysis.objects?.length > 0 ? (
              analysis.objects.map((obj, idx) => (
                <ObjectItem key={idx}>
                  <ColorDot color={obj.main_color.hex} />
                  <span>
                    {obj.object} ({obj.main_color.name}){" "}
                    <small>{obj.confidence}</small>
                  </span>
                </ObjectItem>
              ))
            ) : (
              <p>No objects detected 🫠</p>
            )}
          </ObjectList>
        </ResultsPanel>
      )}

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
  background: black;
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

const VideoFeed = styled.video`
  width: 100%;
  height: 100%;
  object-fit: cover;
`;

const HiddenCanvas = styled.canvas`
  display: none;
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

const ResultsPanel = styled.div`
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  right: 1rem;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  border-radius: 1rem;
  padding: 1rem;
  color: white;
  text-align: center;
  z-index: 15;
  h3 {
    color: #ffb6c1;
    margin: 0.3rem 0;
  }
`;

const ColorRow = styled.div`
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
`;

const ColorBox = styled.div`
  background-color: ${(props) => props.color};
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  color: black;
  font-weight: 600;
  text-shadow: 0 0 3px white;
  small {
    display: block;
    font-size: 0.75rem;
  }
`;

const ObjectList = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const ObjectItem = styled.div`
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin: 0.2rem 0;
`;

const ColorDot = styled.div`
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: ${(props) => props.color};
  border: 1px solid #fff;
`;

const FallbackBox = styled.div`
  color: #fca5a5;
  text-align: center;
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
