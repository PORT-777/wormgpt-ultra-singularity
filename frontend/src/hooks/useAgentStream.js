import { useState, useCallback, useRef } from 'react';

/**
 * useAgentStream
 * Hook for managing the continuous SSE (Server-Sent Events) connection
 * with the Backend Intelligence Engine.
 * Supports structured events: stream, thought, action, observation, final, status, sources.
 */
export const useAgentStream = (baseUrl) => {
  const [messages, setMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const eventSourceRef = useRef(null);
  const abortControllerRef = useRef(null);

  const addLog = useCallback((type, message) => {
    setLogs((prev) => [...prev, { type, message, timestamp: Date.now() }]);
  }, []);

  const startStream = useCallback((sessionId, message, options = {}) => {
    const { mode = 'code', fullAccess = false } = options;

    // Reset state for a new task
    setIsStreaming(true);
    setStreamingText('');
    setLogs([]);

    const params = new URLSearchParams({
      session_id: sessionId,
      message: message,
      mode: mode,
      full_access: String(fullAccess),
    });

    // Use fetch + ReadableStream for better control (POST with body)
    const url = `${baseUrl}/api/chat/stream`;
    abortControllerRef.current = new AbortController();

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message, mode, full_access: fullAccess }),
      signal: abortControllerRef.current.signal,
    }).then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      function readStream() {
        return reader.read().then(({ done, value }) => {
          if (done) {
            flushBuffer();
            setIsStreaming(false);
            return;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              try {
                const event = JSON.parse(dataStr);
                handleEvent(event);
              } catch {
                // Not JSON - treat as raw text
                addLog('stream', dataStr);
              }
            }
          }

          return readStream();
        });
      }

      function flushBuffer() {
        if (buffer.trim()) {
          try {
            const event = JSON.parse(buffer);
            handleEvent(event);
          } catch {
            addLog('stream', buffer);
          }
        }
      }

      function handleEvent(event) {
        const { type, data } = event;

        switch (type) {
          case 'stream':
            setStreamingText((prev) => prev + data);
            break;
          case 'thought':
            addLog('thought', data);
            break;
          case 'action':
            addLog('tool', `${data?.tool || 'unknown'}(${JSON.stringify(data?.args || {})})`);
            break;
          case 'observation':
            addLog('observation', String(data?.output || data || '').slice(0, 300));
            break;
          case 'reflection':
            addLog('reflection', String(data).slice(0, 300));
            break;
          case 'sources':
            addLog('sources', `${data?.count || 0} sources found`);
            break;
          case 'status':
            addLog('status', data?.state || String(data));
            break;
          case 'final':
            setMessages((prev) => [...prev, { role: 'assistant', content: data }]);
            addLog('success', 'Final answer delivered');
            setIsStreaming(false);
            break;
          case 'failed':
            setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${data}` }]);
            addLog('error', String(data));
            setIsStreaming(false);
            break;
          case 'error':
            addLog('error', String(data));
            break;
          default:
            addLog('stream', String(data));
        }
      }

      return readStream().catch((err) => {
        addLog('error', err.message);
        setIsStreaming(false);
      });
    }).catch((err) => {
      if (err.name === 'AbortError') {
        addLog('error', 'Stream cancelled by user');
      } else {
        addLog('error', err.message || 'Connection failed');
      }
      setIsStreaming(false);
    });
  }, [baseUrl, addLog]);

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsStreaming(false);
  }, []);

  return {
    messages,
    setMessages,
    logs,
    setLogs,
    streamingText,
    isStreaming,
    startStream,
    stopStream,
  };
};