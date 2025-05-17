import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { useTextToSpeechContext } from '../contexts/TextToSpeechContext';
import { useWebsocket } from '../contexts/WebsocketContext';
import { useGameApi } from '../hooks/useGameApi';
import { ChatBox } from './ChatBox';
import { GameControls } from './GameControls';
import { GameOverModal } from './GameOverModal';

export const UIOverlay = () => {
  const [messageProcessed, setMessageProcessed] = useState(0);
  const { isConnected, messages } = useWebsocket();
  const { speakText } = useTextToSpeechContext();
  const { startGame } = useGameApi();
  const [gameStarted, setGameStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [gameOver, setGameOver] = useState(false);

  const handleStart = async () => {
    try {
      setIsLoading(true);
      await startGame();
      setGameStarted(true);
    } catch (error) {
      console.error('Error starting game:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestart = async () => {
    setGameOver(false);
    try {
      setIsLoading(true);
      await startGame();
      setGameStarted(true);
    } catch (error) {
      console.error('Error restarting game:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Process new messages
  useEffect(() => {
    const messageLength = messages.length;
    if (messageLength === messageProcessed) return;

    for (let i = messageProcessed; i < messageLength; i++) {
      const message = messages[i];
      if (message.type === 'dialog') {
        speakText(message.text);
      }
      if (message.type === 'game_over') {
        setGameOver(true);
      }
      if (message.type === 'achievement_unlocked') {
        console.log('AchievementUnlocked', message);
        toast.success(message.achievement.name);
      }
    }

    setMessageProcessed(messageLength);
  }, [messages, messageProcessed, speakText]);

  return (
    <div className='fixed inset-0 p-4 pointer-events-none z-50 flex gap-5'>
      <div className='absolute top-5 right-5 flex gap-4 pointer-events-auto'>
        {isLoading ? (
          <div className='text-white'>Loading...</div>
        ) : (
          <>
            <GameControls
              wsConnected={isConnected}
              gameStarted={gameStarted}
              onStart={handleStart}
            />
          </>
        )}
      </div>
      <div className='absolute bottom-5 left-5 pointer-events-auto'>
        {isLoading ? (
          <div className='text-white'>Loading...</div>
        ) : (
          <ChatBox messages={messages} isConnected={isConnected} />
        )}
      </div>

      <GameOverModal isVisible={gameOver} onRestart={handleRestart} />
    </div>
  );
};
