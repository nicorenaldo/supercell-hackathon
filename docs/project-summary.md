# Hackathon Project: Emotion-Driven Browser Game

## Overview

This project is a browser-based interactive game powered by emotional input from the user. The frontend uses Three.js for 3D scene rendering, while the backend uses Python with OpenCV and audio tools to detect the user's emotions via webcam and microphone. The game engine uses these inputs to guide the scenario, dialogue, and gameplay progression.

---

## 🎮 Game Flow

1. **Frontend Scene Load**

   - Three.js loads and renders the scene and characters.

2. **User Interaction Loop**
   - Backend periodically captures a webcam snapshot and microphone audio.
   - Emotion and audio data are analyzed.
   - Backend game engine updates the scenario and dialogue based on emotional state and timing.
   - Frontend displays updated scenario and dialogue.

---

## 🧠 Components

### 1. Frontend (Browser + Three.js)

- Renders scenes and UI
- Receives updates from backend via WebSocket or REST
- Displays dialog and reacts to scenario updates

### 2. Backend (Python)

- **Camera Module:** Captures webcam image using OpenCV
- **Emotion Detection:**
  - Uses pretrained CNN or FER+ to classify facial emotions
  - (Optional) Audio emotion detection based on tone/pitch
- **Game Engine:**
  - Manages current scenario state and dialog history
  - Takes emotion/audio input as input
  - Outputs next dialog/scenario step

---

## 🔁 Data Flow

1. Frontend requests or receives next dialog update
2. Backend captures:
   - Webcam image (OpenCV)
   - Audio clip (optional)
3. Emotion model classifies image
4. Audio is analyzed for mood/sentiment
5. Game engine updates state and sends next dialog to frontend

---
