import { useCallback, useRef, useState } from 'react';

export const useTextToSpeech = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [audio, setAudio] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioQueue = useRef([]);
  const processingQueue = useRef(false);

  // NPC voice configurations mapped by ID
  const npcVoiceConfigs = {
    npc_cult_leader: {
      languageCode: 'en-US',
      name: 'en-US-Chirp3-HD-Sadachbia',
      audioConfig: {
        effectsProfileId: ['small-bluetooth-speaker-class-device'],
        audioEncoding: 'LINEAR16',
        speakingRate: 0.5,
        pitch: -15,
      },
    },
    npc_sara: {
      languageCode: 'en-US',
      name: 'en-US-Chirp3-HD-Kore',
      audioConfig: {
        effectsProfileId: ['handset-class-device'],
        audioEncoding: 'LINEAR16',
      },
    },
    npc_elen: {
      languageCode: 'en-US',
      name: 'en-US-Chirp3-HD-Callirrhoe',
      audioConfig: {
        effectsProfileId: ['small-bluetooth-speaker-class-device'],
        audioEncoding: 'LINEAR16',
      },
    },
    npc_alex: {
      languageCode: 'en-US',
      name: 'en-US-Chirp3-HD-Enceladus',
      audioConfig: {
        effectsProfileId: ['small-bluetooth-speaker-class-device'],
        audioEncoding: 'LINEAR16',
      },
    },
    default: {
      languageCode: 'en-US',
      name: 'en-US-Chirp3-HD-Sadachbia',
      audioConfig: {
        effectsProfileId: ['small-bluetooth-speaker-class-device'],
        audioEncoding: 'LINEAR16',
        speakingRate: 0.5,
        pitch: -15,
      },
    },
  };

  const synthesizeSpeech = useCallback(
    async (text, npcId = 'default', options = {}) => {
      const projectId = import.meta.env.VITE_GOOGLE_PROJECT_ID;
      const apiKey = import.meta.env.VITE_GOOGLE_API_KEY;

      if (!projectId || !apiKey) {
        console.error('Missing Google Cloud credentials');
        setError('Missing Google Cloud credentials');
        return null;
      }

      // Get voice config for the specified NPC, fall back to default if not found
      const npcConfig = npcVoiceConfigs[npcId] || npcVoiceConfigs.default;

      const defaultOptions = {
        ...npcConfig,
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

        return audioElement;
      } catch (err) {
        setError(err.message);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const processQueue = useCallback(async () => {
    if (
      processingQueue.current ||
      audioQueue.current.length === 0 ||
      isPlaying
    ) {
      return;
    }

    processingQueue.current = true;

    const nextItem = audioQueue.current.shift();
    if (!nextItem) {
      processingQueue.current = false;
      return;
    }

    const { text, npcId } = nextItem;

    try {
      const audioElement = await synthesizeSpeech(text, npcId);
      if (audioElement) {
        setAudio(audioElement);
        setIsPlaying(true);

        audioElement.onended = () => {
          setIsPlaying(false);
          // Process the next item in the queue
          setTimeout(() => {
            processingQueue.current = false;
            processQueue();
          }, 300); // Small delay between audio clips
        };

        audioElement.play();
      } else {
        processingQueue.current = false;
        processQueue(); // Continue with next item if this one failed
      }
    } catch (error) {
      console.error('Error playing audio:', error);
      processingQueue.current = false;
      processQueue(); // Continue with next item if this one failed
    }
  }, [synthesizeSpeech, isPlaying]);

  // Add to queue and start processing if not already
  const queueAudio = useCallback(
    (text, npcId = 'default') => {
      if (!text) return;

      audioQueue.current.push({ text, npcId });
      processQueue();
    },
    [processQueue]
  );

  const playAudio = useCallback(
    (npcId = 'default', text = '') => {
      if (text) {
        queueAudio(text, npcId);
      } else if (audio && !isPlaying) {
        setIsPlaying(true);
        audio.play();
        audio.onended = () => {
          setIsPlaying(false);
        };
      }
    },
    [audio, queueAudio, isPlaying]
  );

  const stopAudio = useCallback(() => {
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      setIsPlaying(false);
    }
    // Clear the queue
    audioQueue.current = [];
  }, [audio]);

  const clearQueue = useCallback(() => {
    audioQueue.current = [];
  }, []);

  return {
    synthesizeSpeech,
    playAudio,
    stopAudio,
    clearQueue,
    isLoading,
    error,
    audio,
    isPlaying,
    queueAudio,
    npcVoiceConfigs,
  };
};
