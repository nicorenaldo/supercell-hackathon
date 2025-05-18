import { useCallback } from 'react';

export const useGameApi = () => {
  const BASE_URL = import.meta.env.VITE_BACKEND_URL;

  const startRecording = useCallback(async (gameID) => {
    try {
      console.log('Starting recording');
      const response = await fetch(`${BASE_URL}/recording/start/${gameID}`, {
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

  const stopRecording = useCallback(async (gameID) => {
    try {
      console.log('Stopping recording');
      const response = await fetch(`${BASE_URL}/recording/stop/${gameID}`, {
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

  const uploadRecording = useCallback(async (gameID, videoBlob) => {
    try {
      console.log('Uploading recording');

      // Create a FormData object to send the file to the backend
      const formData = new FormData();
      formData.append('video', videoBlob, 'recording.webm');

      const response = await fetch(`${BASE_URL}/recording/upload/${gameID}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Error uploading recording: ${response.status}`);
      }

      const result = await response.json();

      // Validate that we got a recording_id back
      if (result.status !== 'success') {
        throw new Error('Server validate');
      }

      return result;
    } catch (error) {
      console.error('Failed to upload recording:', error);
      throw error;
    }
  }, []);

  return {
    startRecording,
    stopRecording,
    uploadRecording,
  };
};
