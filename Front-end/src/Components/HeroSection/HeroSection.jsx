import React from "react";
import styles from "./HeroSection.module.css";
import bgImage from "../../assets/takuya-nagaoka-fENvSZUzbzU-unsplash.jpg";

const HeroSection = () => {
  return (
    <div className={`container-fluid p-0 ${styles.heroSection}`}>
      <div className={styles.videoContainer}>
        <img
          className={styles.backgroundVideo}
          src={bgImage}
          alt="Hero Background"
        />
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
