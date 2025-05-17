import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';

const WebsocketContext = createContext();

export const WebsocketProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  const connectWebsocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;
    if (isConnected) return;

    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.dialog) {
        setMessages((prev) => [
          ...prev,
          {
            type: 'dialog',
            text: data.dialog,
            npc_id: data?.npc_id ?? 'unknown',
            suspicion_level: data?.suspicion_level ?? 0,
          },
        ]);
      } else if (data.game_over) {
        setMessages((prev) => [
          ...prev,
          {
            type: 'game_over',
            ending_type: data.ending_type,
            analysis: data.analysis,
          },
        ]);
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
  }, []);

  // Connect to websocket on component mount
  useEffect(() => {
    connectWebsocket();

    // Cleanup function to disconnect when component unmounts
    return () => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.close();
      }
    };
  }, [connectWebsocket]);

  const disconnectWebsocket = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.close();
      setIsConnected(false);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return (
    <WebsocketContext.Provider
      value={{
        messages,
        isConnected,
        connectWebsocket,
        disconnectWebsocket,
        clearMessages,
      }}
    >
      {children}
    </WebsocketContext.Provider>
  );
};

export const useWebsocket = () => {
  const context = useContext(WebsocketContext);
  if (context === undefined) {
    throw new Error('useWebsocket must be used within a WebsocketProvider');
  }
  return context;
};
