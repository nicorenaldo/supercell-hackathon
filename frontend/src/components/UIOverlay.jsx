import { ChatBox } from './ChatBox';
import { GameControls } from './GameControls';

export const UIOverlay = () => {
  return (
    <div className='fixed inset-0 p-4 pointer-events-none z-50 flex gap-5'>
      <div className='absolute top-5 right-5 flex gap-4 pointer-events-auto'>
        <GameControls />
      </div>
      <div className='absolute bottom-5 left-5 pointer-events-auto'>
        <ChatBox />
      </div>
    </div>
  );
};
