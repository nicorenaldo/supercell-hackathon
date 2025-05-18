import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useTextToSpeechContext } from '../contexts/TextToSpeechContext';
import { useWebsocket } from '../contexts/WebsocketContext';
import { useGameApi } from '../hooks/useGameApi';
import { ChatBox } from './ChatBox';
import { GameControls } from './GameControls';
import { GameOverModal } from './GameOverModal';
import WebcamVideo from './WebcamVideo';

export const UIOverlay = () => {
  const { uploadRecording } = useGameApi();
  const [messageProcessed, setMessageProcessed] = useState(0);
  const { isConnected, messages, gameID, startGame, clearMessages } =
    useWebsocket();
  const { speakText, clearQueue } = useTextToSpeechContext();
  const [gameOver, setGameOver] = useState(false);
  const [endingType, setEndingType] = useState(null);
  const [analysis, setAnalysis] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  // Process new messages
  useEffect(() => {
    const messageLength = messages.length;
    if (messageLength === messageProcessed) return;

    for (let i = messageProcessed; i < messageLength; i++) {
      const message = messages[i];
      if (message.type === 'dialog') {
        speakText(message.text, message.npc_id);
      }
      if (message.type === 'game_over') {
        clearQueue();
        setGameOver(true);
        setEndingType(message.ending_type || 'failure');
        setAnalysis(message.analysis || '');
      }
      if (message.type === 'achievement_unlocked') {
        toast.success(message.achievement.name);
      }
    }

    setMessageProcessed(messageLength);
  }, [messages, messageProcessed, speakText, clearQueue]);

  const handleRestart = () => {
    try {
      setGameOver(false);
      setEndingType(null);
      setAnalysis('');
      setMessageProcessed(0);
      clearMessages();
      startGame();

      // Show feedback to the user
      toast.info('Starting new game...', {
        position: 'top-center',
        autoClose: 2000,
      });
    } catch (error) {
      console.error('Error restarting game:', error);
      toast.error('Failed to restart game. Please refresh the page.');
    }
  };

  const handleRecordingComplete = async (blob) => {
    if (!gameID) {
      toast.error('No game ID found');
      return;
    }

    try {
      setIsUploading(true);
      console.log('Uploading video');
      const url = URL.createObjectURL(blob);
      await uploadRecording(gameID, blob);
      console.log('Video successfully uploaded');
    } catch (error) {
      console.error('Error uploading video:', error);
      toast.error('Failed to upload video');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <>
      <div className='fixed inset-0 p-4 pointer-events-none z-40 flex gap-5'>
        <div className='absolute top-5 right-5 pointer-events-auto'>
          <GameControls
            wsConnected={isConnected}
            isUploading={isUploading}
            isRecording={isRecording}
            setIsRecording={setIsRecording}
          />
        </div>

        <div className='absolute bottom-5 left-5 pointer-events-auto'>
          <ChatBox messages={messages} isConnected={isConnected} />
        </div>

        <WebcamVideo
          width={320}
          height={240}
          onRecordingStop={handleRecordingComplete}
          isRecording={isRecording}
        />
      </div>

      {/* Game over modal outside the pointer-events-none container */}
      <GameOverModal
        isVisible={gameOver}
        onRestart={handleRestart}
        endingType={endingType}
        analysis={analysis}
      />
    </>
  );
};
