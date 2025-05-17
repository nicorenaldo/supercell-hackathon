import { useEffect } from 'react';
import '../styles/GameOverModal.css';

export const GameOverModal = ({ isVisible, onRestart }) => {
  useEffect(() => {
    if (isVisible) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }

    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div className='game-over-overlay'>
      <div className='game-over-modal'>
        <h2>Game Over</h2>
        <button className='restart-button' onClick={onRestart}>
          Restart Game
        </button>
      </div>
    </div>
  );
};
