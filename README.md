# Emotion-Driven Interactive Game

A browser-based game where your emotional state and verbal responses determine the outcome of a tense confrontation.

## Overview

In this game, you encounter a thug who wants to steal your purse. Your goal is to convince them not to do so by maintaining confidence and using appropriate verbal responses. The game uses:

- Your webcam to detect emotions
- Your microphone to capture speech
- An AI to determine how the scenario unfolds

## Project Structure

```
.
├── backend/               # Python backend services
│   ├── app.py             # Main FastAPI application
│   ├── emotion_detector/  # Emotion detection module
│   ├── game_engine/       # Game state and logic
│   ├── llm_integration/   # LLM API integration
│   └── requirements.txt   # Python dependencies
├── frontend/              # Web frontend
├── docs/                  # Documentation
└── README.md              # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+ (for development server)
- Web browser with camera and microphone access

### Backend Setup

1. Create a virtual environment:

   ```
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:

   ```
   # Create a .env file with:
   LLM_API_KEY=your_api_key_here
   ```

4. Start the backend server:
   ```
   uvicorn app:app --reload
   ```

### Frontend Setup

1. Open a new terminal window
2. Navigate to the frontend directory:

   ```
   cd frontend
   ```

3. Start a development server:

   ```
   # Using Python:
   python -m http.server
   # Or using Node.js:
   npx serve
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Usage

1. Grant camera and microphone permissions when prompted
2. The game will start automatically
3. Try to remain calm and confident while responding to the thug's demands
4. Your emotional state and verbal responses will influence the outcome

## Development

See the technical documentation in `docs/` for implementation details.

## License

MIT
