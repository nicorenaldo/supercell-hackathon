import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useTextToSpeechContext } from '../contexts/TextToSpeechContext';
import { useGameApi } from '../hooks/useGameApi';
import '../styles/GameControls.css';

export const GameControls = ({ wsConnected, gameStarted, onStart }) => {
  const { startRecording, stopRecording } = useGameApi();
  const {
    isSpeechEnabled,
    toggleSpeech,
    stopAudio,
    clearQueue,
    isPlaying,
    error: audioError,
  } = useTextToSpeechContext();
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (audioError) {
      toast.error('Audio error:', audioError);
    }
  }, [audioError]);

  const handleStartRecording = async () => {
    try {
      // Stop all audio before recording starts
      stopAudio();
      clearQueue();

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

  const handleStopAllSpeech = () => {
    stopAudio();
    clearQueue();
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

      {isPlaying && (
        <button
          onClick={handleStopAllSpeech}
          className='game-button stop-button'
        >
          Stop Speech
        </button>
      )}
    </div>
  );
};
