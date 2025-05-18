import { useEffect, useRef } from 'react';

export const ChatBox = ({ messages, isConnected }) => {
  const chatBoxRef = useRef(null);

  const latestSuspicionPoint =
    messages[messages.length - 1]?.suspicion_level ?? 5;

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
            className='p-2 rounded-md bg-blue-600/60 max-w-[90%] break-words'
          >
            <span className='font-bold text-yellow-300'>{message.npc_id}:</span>{' '}
            {message.text}
          </div>
        );
      case 'game_over':
        const isSuccess = message.ending_type === 'success';
        return (
          <div
            key={index}
            className={`p-3 rounded-md text-center font-bold mx-auto w-4/5 ${
              isSuccess ? 'bg-green-600/60' : 'bg-red-600/60'
            }`}
          >
            <div className='text-lg mb-2'>
              {isSuccess ? 'Mission Complete!' : 'Game Over!'}
            </div>
            <div className='font-normal text-sm leading-tight'>
              {message.analysis}
            </div>
          </div>
        );
      case 'achievement':
        return (
          <div
            key={index}
            className='p-2 rounded-md bg-yellow-500/60 text-black'
          >
            <div className='font-bold mb-2 text-center text-yellow-900'>
              Achievement Unlocked!
            </div>
            {message.achievements.map((achievement, i) => (
              <div key={i} className='mb-1.5 p-1 bg-white/20 rounded'>
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
    <div className='fixed bottom-5 right-5 z-[9999] pointer-events-auto'>
      <div className='w-[400px] h-[400px] bg-black/70 rounded-lg text-white flex flex-col overflow-hidden shadow-lg'>
        <div className='flex justify-between items-center p-2.5 bg-black/80 border-b border-white/10'>
          <h3 className='m-0 text-base'>Game Chat</h3>

          <div className='color-red-500'>
            Suspicion: {latestSuspicionPoint}/10
          </div>

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
    </div>
  );
};
