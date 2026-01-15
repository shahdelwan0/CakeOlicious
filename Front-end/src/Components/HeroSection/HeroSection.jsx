import React, { useRef, useEffect } from "react";
import styles from "./HeroSection.module.css";

const HeroSection = () => {
  const videoRef = useRef(null);

  useEffect(() => {
    if (videoRef.current) {
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch((error) => {
          console.log("Video autoplay failed:", error);
        });
      }
    }
  }, []);

  return (
    <div className={`container-fluid p-0 ${styles.heroSection}`}>
      <div className={styles.videoContainer}>
        <video
          ref={videoRef}
          autoPlay
          loop
          muted
          playsInline
          preload="auto"
          className={styles.backgroundVideo}
          poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1920 1080'%3E%3Crect fill='%23000' width='1920' height='1080'/%3E%3C/svg%3E"
        >
          <source src="/promo.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>
        <div className={styles.overlay}></div>
      </div>
      <div className={styles.content}>
        <h1 className={styles.title}>Sweetness Awaits at CakeOlicious</h1>
        <p className={styles.subtitle}>Freshly baked daily</p>
        <button className={styles.ctaButton}>Taste the magic!</button>
      </div>
    </div>
  );
};

export default HeroSection;
