import React, { useEffect, useRef, useState } from 'react';

const WebcamVideo = ({
  width = 320,
  height = 240,
  onStreamReady,
  onRecordingData,
  onRecordingStop,
  isRecording,
}) => {
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const [hasPermission, setHasPermission] = useState(null);
  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [initialized, setInitialized] = useState(false);
  const [lastRecordingState, setLastRecordingState] = useState(false);

  // Wait for component to fully mount before attempting webcam access
  useEffect(() => {
    setInitialized(true);
  }, []);

  // Initialize webcam after component is mounted
  useEffect(() => {
    if (!initialized) return;

    async function setupWebcam() {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: width },
            height: { ideal: height },
            facingMode: 'user',
          },
          audio: true,
        });

        // Double-check videoRef before assigning
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          // Make sure the video is playing
          try {
            await videoRef.current.play();
          } catch (playError) {
            console.warn(
              'Auto-play failed, user interaction may be needed:',
              playError
            );
          }

          setStream(mediaStream);
          setHasPermission(true);

          if (onStreamReady) {
            onStreamReady(mediaStream);
          }
        } else {
          // If videoRef not available, clean up stream
          mediaStream.getTracks().forEach((track) => track.stop());
          setError(
            'Video element not available. Please try refreshing the page.'
          );
        }
      } catch (err) {
        setHasPermission(false);
        if (
          err.name === 'NotAllowedError' ||
          err.name === 'PermissionDeniedError'
        ) {
          setError(
            'Camera access denied. Please allow camera access in your browser settings.'
          );
        } else if (
          err.name === 'NotFoundError' ||
          err.name === 'DevicesNotFoundError'
        ) {
          setError(
            'No camera detected. Please connect a camera and try again.'
          );
        } else {
          setError(`Camera error: ${err.message || 'Unknown error'}`);
        }
      }
    }

    setupWebcam();

    // Cleanup function
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [initialized, width, height, onStreamReady]);

  // Handle retry
  const handleRetry = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    setError(null);
    setHasPermission(null);

    // Short timeout to ensure DOM is ready
    setTimeout(() => {
      if (!videoRef.current) {
        setError('Video element not available. Please refresh the page.');
        return;
      }

      navigator.mediaDevices
        .getUserMedia({
          video: {
            width: { ideal: width },
            height: { ideal: height },
            facingMode: 'user',
          },
          audio: true,
        })
        .then(async (mediaStream) => {
          if (videoRef.current) {
            videoRef.current.srcObject = mediaStream;
            try {
              await videoRef.current.play();
            } catch (playError) {
              console.warn('Auto-play failed during retry:', playError);
            }

            setStream(mediaStream);
            setHasPermission(true);

            if (onStreamReady) {
              onStreamReady(mediaStream);
            }
          } else {
            mediaStream.getTracks().forEach((track) => track.stop());
            setError('Video element not available during retry.');
          }
        })
        .catch((err) => {
          setHasPermission(false);
          setError(`Camera error: ${err.message || 'Unknown error'}`);
        });
    }, 100);
  };

  // Clean up MediaRecorder when switching from recording to not recording
  useEffect(() => {
    // Handle case when switching from recording to not recording
    if (lastRecordingState && !isRecording) {
      // Clean up after recording stops
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state === 'recording'
      ) {
        mediaRecorderRef.current.stop();
      }

      // Reset the mediaRecorderRef to null after stopping
      setTimeout(() => {
        mediaRecorderRef.current = null;
      }, 100);
    }

    setLastRecordingState(isRecording);
  }, [isRecording, lastRecordingState]);

  // Handle recording state changes
  useEffect(() => {
    if (!stream) return;

    if (isRecording) {
      // Start recording
      recordedChunksRef.current = [];

      // Make sure we're not already recording
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state === 'recording'
      ) {
        mediaRecorderRef.current.stop();
      }

      try {
        // Recreate the MediaRecorder with a fresh instance
        mediaRecorderRef.current = new MediaRecorder(stream, {
          mimeType: 'video/webm;codecs=vp8,opus',
        });
      } catch (e) {
        // Fallback
        mediaRecorderRef.current = new MediaRecorder(stream);
      }

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
          if (onRecordingData) {
            onRecordingData(event.data);
          }
        }
      };

      mediaRecorderRef.current.onstop = () => {
        if (recordedChunksRef.current.length > 0) {
          const blob = new Blob(recordedChunksRef.current, {
            type: 'video/webm',
          });

          // Create a new array instead of clearing the existing one
          const chunks = [...recordedChunksRef.current];
          recordedChunksRef.current = [];

          if (onRecordingStop && blob.size > 0) {
            onRecordingStop(blob);
          }
        }
      };

      mediaRecorderRef.current.start(100); // Collect data every second
    } else if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === 'recording'
    ) {
      mediaRecorderRef.current.stop();
    }
  }, [isRecording, stream, onRecordingData, onRecordingStop]);

  return (
    <div
      className='webcam-container'
      style={{
        position: 'fixed',
        top: '1rem',
        left: '1rem',
        zIndex: 100,
      }}
    >
      {hasPermission === null && (
        <div
          style={{
            color: 'white',
            backgroundColor: 'rgba(0,0,0,0.7)',
            padding: '10px',
            borderRadius: '5px',
          }}
        >
          <p>Requesting webcam access...</p>
        </div>
      )}
      {hasPermission === false && (
        <div
          style={{
            color: 'red',
            backgroundColor: 'rgba(255,255,255,0.8)',
            padding: '10px',
            borderRadius: '5px',
          }}
        >
          <p>No access to webcam. Please check browser permissions.</p>
          <button
            onClick={handleRetry}
            style={{
              marginTop: '10px',
              padding: '5px 10px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}
      {error && (
        <div
          style={{
            color: 'red',
            backgroundColor: 'rgba(255,255,255,0.8)',
            padding: '10px',
            marginBottom: '10px',
            borderRadius: '5px',
          }}
        >
          <p>{error}</p>
          <button
            onClick={handleRetry}
            style={{
              marginTop: '5px',
              padding: '5px 10px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}
      <div
        style={{
          width: width,
          height: height,
          borderRadius: '8px',
          overflow: 'hidden',
          backgroundColor: '#000',
          position: 'relative',
        }}
      >
        <video
          ref={videoRef}
          width='100%'
          height='100%'
          autoPlay
          playsInline
          muted
          style={{
            objectFit: 'cover',
            display: hasPermission ? 'block' : 'none',
          }}
        />
        {hasPermission && isRecording && (
          <div
            className='recording-indicator'
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: 'red',
              animation: 'pulse 1s infinite',
            }}
          />
        )}
      </div>
    </div>
  );
};

export default WebcamVideo;
