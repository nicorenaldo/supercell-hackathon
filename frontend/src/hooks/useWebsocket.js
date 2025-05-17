import { useCallback, useRef, useState } from 'react';

export const useWebsocket = () => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  const connectWebsocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.dialog && data.npc_id && data.suspicion_level) {
        setMessages((prev) => [
          ...prev,
          {
            type: 'dialog',
            text: data.dialog,
            npc_id: data.npc_id,
            suspicion_level: data.suspicion_level,
          },
        ]);
      } else if (data.game_over) {
        setMessages((prev) => [...prev, { type: 'game_over' }]);
      } else if (data.achievement_unlocked) {
        setMessages((prev) => [
          ...prev,
          {
            type: 'achievement',
            achievements: data.achievement_unlocked,
          },
        ]);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    socketRef.current = ws;

    return () => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.close();
      }
    };
  }, []);

  const disconnectWebsocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.close();
      setIsConnected(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isConnected,
    connectWebsocket,
    disconnectWebsocket,
    clearMessages,
  };
};
