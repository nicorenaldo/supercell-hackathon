import { useEffect, useState } from 'react';
import { useGameApi } from '../hooks/useGameApi';
import '../styles/GameControls.css'; 

export const GameControls = () => {
  const { startGame, startRecording, stopRecording } = useGameApi();
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const initGame = async () => {
      try {
        setIsLoading(true);
        await startGame();
      } catch (error) {
        console.error('Error initializing game:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initGame();
  }, [startGame]);

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
    <div className="game-controls">
      <button
        onClick={handleStartRecording}
        disabled={isRecording || isLoading}
        className="game-button start-button"
      >
        {isLoading && !isRecording ? 'Starting...' : 'Start Recording'}
      </button>

      <button
        onClick={handleStopRecording}
        disabled={!isRecording || isLoading}
        className="game-button stop-button"
      >
        {isLoading && isRecording ? 'Stopping...' : 'Stop Recording'}
      </button>
    </div>
  );
};
