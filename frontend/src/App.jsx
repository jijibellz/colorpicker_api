import { useState } from "react";
import styled from "styled-components";

export default function App() {
  const [videoUrl] = useState("http://127.0.0.1:8000/video");

  return (
    <PageContainer>
      <HeaderBar>🎨 Real-Time Color Detector</HeaderBar>

      <VideoFeed src={videoUrl} alt="Live Stream" />

      <Footer>made with 💖 by <span>Jiji</span></Footer>
    </PageContainer>
  );
}

//
// 🌈 Styled Components
//

const PageContainer = styled.div`
  position: relative;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: black;
  font-family: "Poppins", sans-serif;
`;

const HeaderBar = styled.div`
  position: absolute;
  top: 0;
  width: 100%;
  padding: 15px 0;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  color: white;
  font-size: 1.6rem;
  font-weight: 700;
  text-align: center;
  text-shadow: 0 0 8px rgba(255, 105, 180, 0.7);
  z-index: 10;
`;

const VideoFeed = styled.img`
  width: 100%;
  height: 100%;
  object-fit: contain; /* 👈 ensures full camera view fits perfectly */
  background-color: black;
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
