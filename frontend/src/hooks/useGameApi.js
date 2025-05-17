import { useCallback } from 'react';

export const useGameApi = () => {
  const BASE_URL = 'http://localhost:8000';

  const startGame = useCallback(async () => {
    try {
      console.log('Starting game');
      const response = await fetch(`${BASE_URL}/start-game`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Error starting game: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to start game:', error);
      throw error;
    }
  }, []);

  const startRecording = useCallback(async () => {
    try {
      console.log('Starting recording');
      const response = await fetch(`${BASE_URL}/recording/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Error starting recording: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  }, []);

  const stopRecording = useCallback(async () => {
    try {
      console.log('Stopping recording');
      const response = await fetch(`${BASE_URL}/recording/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Error stopping recording: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to stop recording:', error);
      throw error;
    }
  }, []);

  return {
    startGame,
    startRecording,
    stopRecording,
  };
};
