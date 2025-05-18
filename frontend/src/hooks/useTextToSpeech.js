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

  const synthesizeSpeech = useCallback(async (text, npcId = 'default') => {
    const projectId = import.meta.env.VITE_GOOGLE_PROJECT_ID;
    const apiKey = import.meta.env.VITE_GOOGLE_API_KEY;

    if (!projectId || !apiKey) {
      console.error('Missing Google Cloud credentials');
      setError('Missing Google Cloud credentials');
      return null;
    }

    try {
      let voiceOptions = npcVoiceConfigs[npcId];
      if (!voiceOptions) {
        voiceOptions = npcVoiceConfigs.default;
      }
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
              languageCode: voiceOptions.languageCode,
              name: voiceOptions.name,
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
      const audioSource = `data:audio/mp3;base64,${audioContent}`;
      return new Audio(audioSource);
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const processQueue = useCallback(async () => {
    if (processingQueue.current || audioQueue.current.length === 0) {
      return;
    }

    processingQueue.current = true;

    try {
      const { text, npcId } = audioQueue.current.shift();
      const audioElement = await synthesizeSpeech(text, npcId);

      if (audioElement) {
        setAudio(audioElement);
        setIsPlaying(true);

        audioElement.onended = () => {
          setIsPlaying(false);
          processingQueue.current = false;
          // Process next item with a small delay
          setTimeout(processQueue, 300);
        };

        // Handle possible errors during playback
        audioElement.onerror = () => {
          setIsPlaying(false);
          processingQueue.current = false;
          setTimeout(processQueue, 300);
        };

        audioElement.play().catch((err) => {
          console.error('Error playing audio:', err);
          setIsPlaying(false);
          processingQueue.current = false;
          setTimeout(processQueue, 300);
        });
      } else {
        processingQueue.current = false;
        processQueue();
      }
    } catch (error) {
      console.error('Error in audio queue processing:', error);
      processingQueue.current = false;
      processQueue();
    }
  }, [synthesizeSpeech]);

  const queueAudio = useCallback(
    (text, npcId = 'default') => {
      if (!text) return;

      audioQueue.current.push({ text, npcId });
      processQueue();
    },
    [processQueue]
  );

  const stopAudio = useCallback(() => {
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
      setIsPlaying(false);
    }
    processingQueue.current = false;
    // Critical: ensure we reset the audio state properly
    setAudio(null);
  }, [audio]);

  const clearQueue = useCallback(() => {
    audioQueue.current = [];
  }, []);

  return {
    synthesizeSpeech,
    playAudio: queueAudio, // Simplify API by making playAudio alias to queueAudio
    stopAudio,
    clearQueue,
    isLoading,
    error,
    isPlaying,
    queueAudio,
    npcVoiceConfigs,
  };
};
