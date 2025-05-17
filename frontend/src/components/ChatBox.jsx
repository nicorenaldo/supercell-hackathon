import { useEffect, useRef } from 'react';
import { useWebsocket } from '../hooks/useWebsocket';

export const ChatBox = () => {
  const { messages, isConnected, connectWebsocket } = useWebsocket();
  const chatBoxRef = useRef(null);

  useEffect(() => {
    connectWebsocket();
  }, [connectWebsocket]);

  const latestSuspicionPoint =
    messages[messages.length - 1]?.suspicion_level ?? 0;

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  const renderMessage = (message, index) => {
    switch (message.type) {
      case 'dialog':
        return (
          <div
            key={index}
            className='p-2 px-3 rounded-md max-w-[90%] break-words bg-blue-900/60'
          >
            <span className='font-bold text-yellow-300'>{message.npc}:</span>{' '}
            {message.text}
          </div>
        );
      case 'game_over':
        return (
          <div
            key={index}
            className='p-3 rounded-md mx-auto w-4/5 text-center font-bold bg-red-500/60'
          >
            Game Over!
          </div>
        );
      case 'achievement':
        return (
          <div
            key={index}
            className='p-2.5 rounded-md max-w-[90%] bg-amber-400/60 text-black'
          >
            <div className='font-bold mb-2 text-center text-amber-900'>
              Achievement Unlocked!
            </div>
            {message.achievements.map((achievement, i) => (
              <div key={i} className='mb-1.5 p-1 rounded bg-white/20'>
                <div className='font-bold mb-0.5'>{achievement.name}</div>
                <div className='text-xs'>{achievement.description}</div>
              </div>
            ))}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className='w-[300px] h-[350px] bg-black/70 rounded-lg text-white flex flex-col overflow-hidden shadow-lg'>
      <div className='flex justify-between items-center p-2.5 px-4 bg-black/80 border-b border-white/10'>
        <h3 className='m-0 text-base'>Game Chat</h3>
        <div
          className={`text-xs py-1 px-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}
        >
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>
      <div
        className='flex-1 overflow-y-auto p-2.5 flex flex-col gap-2'
        ref={chatBoxRef}
      >
        {messages.length === 0 ? (
          <div className='text-center text-white/60 m-auto'>
            No messages yet...
          </div>
        ) : (
          messages.map((message, index) => renderMessage(message, index))
        )}
      </div>
    </div>
  );
};
