import { useEffect } from 'react';
import '../styles/GameOverModal.css';

export const GameOverModal = ({
  isVisible,
  onRestart,
  endingType,
  analysis,
}) => {
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

  const isSuccess = endingType === 'success';

  return (
    <div className='game-over-overlay'>
      <div className={`game-over-modal ${isSuccess ? 'success' : 'failure'}`}>
        <h2>{isSuccess ? 'Mission Successful!' : 'Game Over'}</h2>
        {analysis && <p className='game-over-analysis'>{analysis}</p>}
        <button className='restart-button' onClick={onRestart}>
          {isSuccess ? 'Play Again' : 'Try Again'}
        </button>
      </div>
    </div>
  );
};
