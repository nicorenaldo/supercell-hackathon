import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useTextToSpeechContext } from '../contexts/TextToSpeechContext';
import { useWebsocket } from '../contexts/WebsocketContext';

export const GameControls = ({ isUploading, isRecording, setIsRecording }) => {
  const {
    stopAudio,
    clearQueue,
    isPlaying,
    error: audioError,
  } = useTextToSpeechContext();
  const { gameID, startGame } = useWebsocket();
  const [isLoading, setIsLoading] = useState(false);
  const [gameStarted, setGameStarted] = useState(false);

  // Handle any audio errors
  useEffect(() => {
    if (audioError) {
      toast.error(`Audio error: ${audioError}`);
    }
  }, [audioError]);

  const handleStartGame = async () => {
    try {
      setIsLoading(true);
      await startGame();
      setGameStarted(true);
    } catch (error) {
      console.error('Error starting game:', error);
      toast.error('Failed to start game');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleRecording = () => {
    if (!gameID) {
      toast.error('No game ID found');
      return;
    }

    // Stop all audio before recording starts/stops
    stopAudio();
    clearQueue();

    setIsRecording(!isRecording);
  };

  // Common button classes
  const buttonBase =
    'flex-1 min-w-[120px] py-2 px-4 rounded-full font-semibold text-sm cursor-pointer transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-white/5 disabled:text-gray-500';
  const startButtonClass = `${buttonBase} bg-green-500/15 text-green-100/70 hover:bg-green-500/30 hover:text-green-100 hover:-translate-y-0.5 shadow-md hover:shadow-lg`;
  const stopButtonClass = `${buttonBase} bg-red-500/15 text-red-100/70 hover:bg-red-500/30 hover:text-red-100 hover:-translate-y-0.5 shadow-md hover:shadow-lg`;

  return (
    <>
      <div className='flex gap-3 p-3 bg-black/45 rounded-xl shadow-lg z-10 backdrop-blur-sm max-w-sm mx-auto whitespace-nowrap'>
        {!gameStarted && (
          <button
            onClick={handleStartGame}
            className={startButtonClass}
            disabled={isLoading}
          >
            {isLoading ? 'Starting...' : 'Start Game'}
          </button>
        )}
        {isPlaying && (
          <button
            onClick={() => {
              stopAudio();
              clearQueue();
            }}
            className={stopButtonClass}
          >
            Stop Speech
          </button>
        )}
        <button
          onClick={handleToggleRecording}
          disabled={isLoading || (!gameStarted && !isRecording) || isUploading}
          className={isRecording ? stopButtonClass : startButtonClass}
        >
          {isLoading
            ? 'Loading...'
            : isUploading
            ? 'Uploading...'
            : isRecording
            ? 'Stop Recording'
            : 'Start Recording'}
        </button>
      </div>
    </>
  );
};
