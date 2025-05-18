import { useEffect } from 'react';

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
    <div className='fixed inset-0 bg-black/80 flex justify-center items-center z-50 animate-fadeIn pointer-events-auto'>
      <div
        className={`bg-zinc-900/90 rounded-2xl p-8 shadow-2xl text-center min-w-[300px] backdrop-blur-xl border border-white/10 animate-scaleIn pointer-events-auto`}
      >
        <h2
          className={`text-3xl mb-6 drop-shadow-md ${
            isSuccess ? 'text-green-500' : 'text-red-400'
          }`}
        >
          {isSuccess ? 'Mission Successful!' : 'Game Over'}
        </h2>

        {analysis && (
          <p className='mb-5 text-gray-100 leading-relaxed text-base bg-white/10 p-4 rounded-lg text-left'>
            {analysis}
          </p>
        )}

        <button
          className='bg-green-500/20 text-green-200 border-none py-3 px-6 text-base font-semibold rounded-full cursor-pointer pointer-events-auto transition-all duration-300 shadow-lg hover:bg-green-500/40 hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0.5 active:shadow-md'
          onClick={onRestart}
        >
          {isSuccess ? 'Play Again' : 'Try Again'}
        </button>
      </div>
    </div>
  );
};
