import { useCallback, useState } from 'react';

export const useTextToSpeech = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [audio, setAudio] = useState(null);

  const synthesizeSpeech = useCallback(async (text, options = {}) => {
    const projectId = import.meta.env.VITE_GOOGLE_PROJECT_ID;
    const apiKey = import.meta.env.VITE_GOOGLE_API_KEY;

    if (!projectId || !apiKey) {
      console.error('Missing Google Cloud credentials');
      setError('Missing Google Cloud credentials');
      return null;
    }

    const defaultOptions = {
      languageCode: 'en-US',
      name: 'en-US-Chirp3-HD-Sadachbia',
      audioConfig: {
        effectsProfileId: ['small-bluetooth-speaker-class-device'],
        audioEncoding: 'LINEAR16',
        speakingRate: 0.5,
        pitch: -15,
      },
      ...options,
    };

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(
        `https://texttospeech.googleapis.com/v1/text:synthesize`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Goog-User-Project': projectId,
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({
            input: { markup: text },
            voice: {
              languageCode: defaultOptions.languageCode,
              ssmlGender: defaultOptions.ssmlGender,
              name: defaultOptions.name,
            },
            audioConfig: { audioEncoding: 'MP3' },
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.error?.message || 'Failed to synthesize speech'
        );
      }

      const data = await response.json();
      const audioContent = data.audioContent;

      // Create audio element with the received base64 audio data
      const audioSource = `data:audio/mp3;base64,${audioContent}`;
      const audioElement = new Audio(audioSource);

      setAudio(audioElement);
      return audioElement;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const playAudio = useCallback(() => {
    if (audio) {
      audio.play();
    }
  }, [audio]);

  const stopAudio = useCallback(() => {
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
  }, [audio]);

  return {
    synthesizeSpeech,
    playAudio,
    stopAudio,
    isLoading,
    error,
    audio,
  };
};
