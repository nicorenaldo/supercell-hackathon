# Technical Implementation Plan: Emotion-Driven Interactive Game

## Game Scenario: Night Encounter

- **Setting**: Dark street at night
- **Characters**: Player (user) and a Thug
- **Goal**: Convince the thug not to steal your purse through emotional regulation and verbal responses
- **Key Mechanics**: Displaying confidence reduces threat level; showing nervousness escalates the situation

## System Architecture

### Frontend Components

1. **Static Scene**

   - Simple night-time street background image
   - No complex 3D rendering required

2. **Avatar Visualization**

   - Thug character avatar with basic expressions
   - Position fixed on screen

3. **Dialog Display**

   - Text box for showing thug's dialogue
   - Optionally player's recognized speech as text

4. **Text-to-Speech**

   - Web Speech API for converting dialog text to speech
   - Voice modulation based on character emotion

5. **UI/UX Elements**
   - Status indicators (threat level, etc.)
   - Game state visualization

### Backend Components

1. **Emotion Detection Service**

   - Process webcam frames to detect user emotions
   - Returns emotion classification with timestamp
   - Categories: calm, nervous, confident, scared, angry

2. **Speech Recognition**

   - Converts audio input to text
   - Returns text with timestamp

3. **Game Engine**

   - State machine tracking current scenario stage
   - Input processor for emotion and speech data
   - Dialog generator based on game state

4. **LLM Integration**
   - API interface to chosen LLM (e.g., GPT-4)
   - Context manager for maintaining conversation history
   - Function calling for game state management

## Data Flow

1. Frontend sends webcam frames to backend at regular intervals (1-2fps)
2. Backend processes frames for emotion detection
3. Frontend sends audio to backend for speech recognition
4. Backend packages emotion and speech data with timestamps
5. Backend sends data to LLM with current game state
6. LLM processes inputs and returns:
   - Next dialog text
   - Game state update (continue, end-success, end-failure)
7. Backend sends dialog and state to frontend
8. Frontend renders dialog, plays speech, updates UI

## LLM Integration Details

### LLM Context Formatting

```json
{
  "scenario": "night_encounter",
  "current_state": {
    "stage": "initial_confrontation",
    "threat_level": 7,
    "dialog_history": [...]
  },
  "user_input": {
    "emotion": {"type": "nervous", "confidence": 0.85, "timestamp": 1623482},
    "speech": {"text": "Please don't hurt me", "timestamp": 1623485}
  }
}
```

### LLM Function Calling Definition

```json
{
  "name": "generate_response",
  "parameters": {
    "dialog": "string",
    "internal_state": {
      "threat_level": "number",
      "stage": "string"
    },
    "game_status": {
      "continue": "boolean",
      "ending_type": "string" // "success" or "failure" or null
    }
  }
}
```

## Emotion Detection Implementation

- Use a pre-trained model (FER+ or similar)
- Process frames at 1-2fps to reduce computational load
- Track emotion trends over time (sudden changes vs. consistent state)
- Map detected emotions to game-relevant categories:
  - Confidence (promotes positive outcome)
  - Nervousness (promotes negative outcome)
  - Other emotions mapped accordingly

## Speech Processing

- Convert audio to text using Web Speech API or similar
- Extract key phrases and sentiment
- Timestamp alignment with emotion data
- Provide both raw text and extracted intent to LLM

## Game State Management

- Track threat level (0-10)
- Track conversation stage
- Define key decision points
- Maintain history of user emotions and responses
- Two possible endings:
  1. **Success**: Thug backs down, player keeps purse
  2. **Failure**: Thug takes purse or escalates to violence

## Implementation Roadmap

1. Setup basic frontend with static background and avatar
2. Implement webcam and audio capture
3. Create emotion detection service
4. Implement speech-to-text conversion
5. Setup LLM API integration
6. Design game state machine
7. Connect all components
8. Testing and refinement

## Technical Stack Details

- **Frontend**: HTML5, CSS, JavaScript, Web Speech API
- **Backend**: Python, FastAPI
- **Emotion Detection**: OpenCV + pre-trained CNN model
- **Speech Processing**: Web Speech API (frontend) or Python speech recognition
- **LLM Integration**: OpenAI API or equivalent
- **Deployment**: Local development server for hackathon
