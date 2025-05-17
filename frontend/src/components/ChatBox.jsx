import { useEffect, useRef } from 'react';
import '../styles/ChatBox.css';

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
          <div key={index} className='chat-message dialog'>
            <span className='npc-name'>{message.npc_id}:</span> {message.text}
          </div>
        );
      case 'game_over':
        return (
          <div key={index} className='chat-message game-over'>
            Game Over!
          </div>
        );
      case 'achievement':
        return (
          <div key={index} className='chat-message achievement'>
            <div className='achievement-header'>Achievement Unlocked!</div>
            {message.achievements.map((achievement, i) => (
              <div key={i} className='achievement-item'>
                <div className='achievement-name'>{achievement.name}</div>
                <div className='achievement-description'>
                  {achievement.description}
                </div>
              </div>
            ))}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: 9999,
        pointerEvents: 'auto',
      }}
    >
      <div className='chat-box-container'>
        <div className='chat-box-header'>
          <h3>Game Chat</h3>

          <div>Suspicion: {latestSuspicionPoint}/10</div>

          <div
            className={`connection-status ${
              isConnected ? 'connected' : 'disconnected'
            }`}
          >
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <div className='chat-box-messages' ref={chatBoxRef}>
          {messages.length === 0 ? (
            <div className='empty-chat'>No messages yet...</div>
          ) : (
            messages.map((message, index) => renderMessage(message, index))
          )}
        </div>
      </div>
    </div>
  );
};
