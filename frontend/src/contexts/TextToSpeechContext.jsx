import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { useTextToSpeech } from '../hooks/useTextToSpeech';

const TextToSpeechContext = createContext();

export const TextToSpeechProvider = ({ children }) => {
  const [userInteracted, setUserInteracted] = useState(false);
  const tts = useTextToSpeech();

  // Listen for user interaction to enable audio
  useEffect(() => {
    const handleUserInteraction = () => {
      setUserInteracted(true);
    };

    // Add event listeners for common user interactions
    window.addEventListener('click', handleUserInteraction);
    window.addEventListener('keydown', handleUserInteraction);
    window.addEventListener('touchstart', handleUserInteraction);

    return () => {
      window.removeEventListener('click', handleUserInteraction);
      window.removeEventListener('keydown', handleUserInteraction);
      window.removeEventListener('touchstart', handleUserInteraction);
    };
  }, []);

  const speakText = useCallback(
    (text, npcId = 'default') => {
      if (userInteracted) {
        tts.queueAudio(text, npcId);
      } else {
        // Set up a one-time event handler that will speak the text once user interacts
        const handleFirstInteraction = () => {
          tts.queueAudio(text, npcId);
          // Remove this handler after first interaction
          window.removeEventListener('click', handleFirstInteraction);
          window.removeEventListener('keydown', handleFirstInteraction);
          window.removeEventListener('touchstart', handleFirstInteraction);
        };

        window.addEventListener('click', handleFirstInteraction);
        window.addEventListener('keydown', handleFirstInteraction);
        window.addEventListener('touchstart', handleFirstInteraction);
      }
    },
    [tts, userInteracted]
  );

  return (
    <TextToSpeechContext.Provider
      value={{
        speakText,
        isLoading: tts.isLoading,
        error: tts.error,
        isPlaying: tts.isPlaying,
        userInteracted,
        stopAudio: tts.stopAudio,
        clearQueue: tts.clearQueue,
      }}
    >
      {children}
    </TextToSpeechContext.Provider>
  );
};

export const useTextToSpeechContext = () => {
  const context = useContext(TextToSpeechContext);
  if (context === undefined) {
    throw new Error(
      'useTextToSpeechContext must be used within a TextToSpeechProvider'
    );
  }
  return context;
};
