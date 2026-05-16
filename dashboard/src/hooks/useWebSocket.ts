import { useState, useEffect, useCallback, useRef } from 'react';

interface AnalysisUpdate {
  stage: string;
  percentage: number;
  message: string;
}

export function useWebSocket(analysisId: string | null, token: string | null) {
  const [status, setStatus] = useState<AnalysisUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!analysisId || !token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/api/ws/analysis/${analysisId}?token=${token}`;
    
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log(`WebSocket connected to analysis ${analysisId}`);
    };

    socket.onmessage = (event) => {
      try {
        const data: AnalysisUpdate = JSON.parse(event.data);
        setStatus(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  }, [analysisId, token]);

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect]);

  return { status, isConnected };
}
