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
  const [showPointer, setShowPointer] = useState(true);

  // Show the pointer for first-time users
  useEffect(() => {
    // Check if this is the first visit
    const hasVisitedBefore = localStorage.getItem('hasVisitedBefore');
    if (hasVisitedBefore) {
      setShowPointer(false);
    } else {
      setShowPointer(true);
      // Hide pointer after 10 seconds
      const timer = setTimeout(() => {
        setShowPointer(false);
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, []);

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
      // Mark that user has played before
      localStorage.setItem('hasVisitedBefore', 'true');
      // Hide pointer once game starts
      setShowPointer(false);
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
    // Mark that user has played before
    localStorage.setItem('hasVisitedBefore', 'true');
    // Hide pointer once user starts recording
    setShowPointer(false);
  };

  // Common button classes
  const buttonBase =
    'flex-1 min-w-[120px] py-2 px-4 rounded-full font-semibold text-sm cursor-pointer transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-white/5 disabled:text-gray-500';
  const startButtonClass = `${buttonBase} bg-green-500/15 text-green-100/70 hover:bg-green-500/30 hover:text-green-100 hover:-translate-y-0.5 shadow-md hover:shadow-lg`;
  const stopButtonClass = `${buttonBase} bg-red-500/15 text-red-100/70 hover:bg-red-500/30 hover:text-red-100 hover:-translate-y-0.5 shadow-md hover:shadow-lg`;

  // Pointer styles
  const pointerClass =
    'absolute animate-bounce text-yellow-300 text-3xl -mb-10 bottom-0';

  return (
    <>
      <div className='flex gap-3 p-3 bg-black/45 rounded-xl shadow-lg z-10 backdrop-blur-sm max-w-sm mx-auto whitespace-nowrap relative'>
        {!gameStarted && (
          <div className='relative'>
            {showPointer && (
              <div
                className={pointerClass}
                style={{
                  left: '50%',
                  transform: 'translateX(-50%) translateY(100%)',
                }}
              >
                ↑ <span className='text-sm'>Click here to start!</span>
                <span className='text-sm'>
                  Use big expressions to have the best experience!
                </span>
              </div>
            )}
            <button
              onClick={handleStartGame}
              className={startButtonClass}
              disabled={isLoading}
            >
              {isLoading ? 'Starting...' : 'Start Game'}
            </button>
          </div>
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
        <div className='relative'>
          {showPointer && gameStarted && !isRecording && (
            <div
              className={pointerClass}
              style={{
                left: '50%',
                transform: 'translateX(-50%) translateY(100%)',
              }}
            >
              ↑ <span className='text-sm'>Click to record!</span>
            </div>
          )}
          <button
            onClick={handleToggleRecording}
            disabled={
              isLoading || (!gameStarted && !isRecording) || isUploading
            }
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
      </div>
    </>
  );
};
