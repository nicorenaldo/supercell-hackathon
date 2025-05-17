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
  const [pendingAudio, setPendingAudio] = useState([]);
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

  // Process pending audio once user has interacted
  useEffect(() => {
    if (userInteracted && pendingAudio.length > 0) {
      const playNext = async () => {
        const audioElement = pendingAudio[0];
        try {
          await audioElement.play();
        } catch (error) {
          console.error('Failed to play audio:', error);
        }
        setPendingAudio((prev) => prev.slice(1));
      };

      playNext();
    }
  }, [userInteracted, pendingAudio]);

  const speakText = useCallback(
    async (text) => {
      if (!isSpeechEnabled || !text) return;

      const audio = await tts.synthesizeSpeech(text);
      if (audio) {
        try {
          if (userInteracted) {
            await audio.play();
          } else {
            setPendingAudio((prev) => [...prev, audio]);
          }
        } catch (error) {
          console.error('Audio play error:', error);
          setPendingAudio((prev) => [...prev, audio]);
        }
      }
    },
    [isSpeechEnabled, tts, userInteracted]
  );

  const toggleSpeech = useCallback(() => {
    setIsSpeechEnabled((prev) => !prev);
    setUserInteracted(true); // Mark as interacted when user toggles speech
  }, []);

  return (
    <TextToSpeechContext.Provider
      value={{
        isSpeechEnabled,
        toggleSpeech,
        speakText,
        isLoading: tts.isLoading,
        error: tts.error,
        userInteracted,
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
