import { useState } from 'react';
import { useTextToSpeechContext } from '../contexts/TextToSpeechContext';
import { useGameApi } from '../hooks/useGameApi';
import '../styles/GameControls.css';

export const GameControls = ({ wsConnected, gameStarted, onStart }) => {
  const { startRecording, stopRecording } = useGameApi();
  const { isSpeechEnabled, toggleSpeech } = useTextToSpeechContext();
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleStartRecording = async () => {
    try {
      setIsLoading(true);
      await startRecording();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStopRecording = async () => {
    try {
      setIsLoading(true);
      await stopRecording();
      setIsRecording(false);
    } catch (error) {
      console.error('Error stopping recording:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className='game-controls'>
      {!gameStarted && (
        <button onClick={onStart} className='game-button start-button'>
          {isLoading ? 'Starting...' : 'Start Game'}
        </button>
      )}

      <button
        onClick={handleStartRecording}
        disabled={isRecording || isLoading}
        className='game-button start-button'
      >
        {isLoading && !isRecording ? 'Starting...' : 'Start Recording'}
      </button>

      <button
        onClick={handleStopRecording}
        disabled={!isRecording || isLoading}
        className='game-button stop-button'
      >
        {isLoading && isRecording ? 'Stopping...' : 'Stop Recording'}
      </button>

      <button
        onClick={toggleSpeech}
        className={`game-button ${
          isSpeechEnabled ? 'stop-button' : 'start-button'
        }`}
      >
        {isSpeechEnabled ? 'Disable Speech' : 'Enable Speech'}
      </button>
    </div>
  );
};
