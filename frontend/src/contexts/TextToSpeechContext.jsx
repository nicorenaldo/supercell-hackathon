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
  const [isSpeechEnabled, setIsSpeechEnabled] = useState(true);
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
      if (!isSpeechEnabled || !text) return;

      if (userInteracted) {
        // Use the queue system directly
        tts.queueAudio(text, npcId);
      } else {
        // Store callback to execute once user interacts
        const handler = () => {
          tts.queueAudio(text, npcId);
          window.removeEventListener('click', handler);
          window.removeEventListener('keydown', handler);
          window.removeEventListener('touchstart', handler);
        };

        window.addEventListener('click', handler);
        window.addEventListener('keydown', handler);
        window.addEventListener('touchstart', handler);
      }
    },
    [isSpeechEnabled, tts, userInteracted]
  );

  const toggleSpeech = useCallback(() => {
    setIsSpeechEnabled((prev) => {
      const newValue = !prev;
      if (!newValue) {
        // If disabling speech, stop any current audio
        tts.stopAudio();
      }
      return newValue;
    });
    setUserInteracted(true); // Mark as interacted when user toggles speech
  }, [tts]);

  return (
    <TextToSpeechContext.Provider
      value={{
        isSpeechEnabled,
        toggleSpeech,
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
