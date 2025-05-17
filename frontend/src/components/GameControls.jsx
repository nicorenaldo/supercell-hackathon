import { useEffect, useState } from 'react';
import { useGameApi } from '../hooks/useGameApi';

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

  const startButtonClasses =
    isRecording || isLoading
      ? 'bg-gray-400 text-gray-600 cursor-not-allowed shadow-none'
      : 'bg-green-500 text-white hover:bg-green-600 hover:-translate-y-0.5 transition-transform';

  const stopButtonClasses =
    !isRecording || isLoading
      ? 'bg-gray-400 text-gray-600 cursor-not-allowed shadow-none'
      : 'bg-red-500 text-white hover:bg-red-600 hover:-translate-y-0.5 transition-transform';

  return (
    <div className='flex gap-4 p-4 bg-black/60 rounded-lg z-10'>
      <button
        onClick={handleStartRecording}
        disabled={isRecording || isLoading}
        className={`py-2.5 px-5 border-none rounded font-bold text-sm min-w-[140px] shadow-md ${startButtonClasses}`}
      >
        {isLoading && !isRecording ? 'Starting...' : 'Start Recording'}
      </button>
      <button
        onClick={handleStopRecording}
        disabled={!isRecording || isLoading}
        className={`py-2.5 px-5 border-none rounded font-bold text-sm min-w-[140px] shadow-md ${stopButtonClasses}`}
      >
        {isLoading && isRecording ? 'Stopping...' : 'Stop Recording'}
      </button>
    </div>
  );
};
