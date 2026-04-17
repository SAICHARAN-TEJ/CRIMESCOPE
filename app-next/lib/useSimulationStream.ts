'use client';
// lib/useSimulationStream.ts — SSE hook for real-time agent events
import { useState, useEffect, useRef, useCallback } from 'react';
import type { SimulationEvent } from '@/types/crimescope';

interface UseSimulationStreamOptions {
  simulationId: string | null;
  enabled?: boolean;
  maxEvents?: number;
  pollInterval?: number; // fallback polling ms when SSE unavailable
}

interface UseSimulationStreamResult {
  events: SimulationEvent[];
  isConnected: boolean;
  isPaused: boolean;
  pause: () => void;
  resume: () => void;
  clear: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:5001';

export function useSimulationStream({
  simulationId,
  enabled = true,
  maxEvents = 200,
  pollInterval = 3000,
}: UseSimulationStreamOptions): UseSimulationStreamResult {
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const pausedRef = useRef(false);
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const offsetRef = useRef(0);

  const addEvent = useCallback((ev: SimulationEvent) => {
    if (pausedRef.current) return;
    setEvents(prev => [ev, ...prev].slice(0, maxEvents));
  }, [maxEvents]);

  const pause = useCallback(() => { setIsPaused(true); pausedRef.current = true; }, []);
  const resume = useCallback(() => { setIsPaused(false); pausedRef.current = false; }, []);
  const clear = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!simulationId || !enabled) return;

    // Try SSE first
    let sseWorked = false;
    try {
      const es = new EventSource(`${API}/api/simulation/events/${simulationId}`);
      esRef.current = es;

      es.onopen = () => { setIsConnected(true); sseWorked = true; };
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as SimulationEvent;
          addEvent(data);
        } catch { /* ignore malformed */ }
      };
      es.onerror = () => {
        es.close();
        setIsConnected(false);
        if (!sseWorked) {
          // Fall back to polling
          startPolling();
        }
      };
    } catch {
      startPolling();
    }

    function startPolling() {
      pollRef.current = setInterval(async () => {
        if (pausedRef.current) return;
        try {
          const res = await fetch(
            `${API}/api/simulation/actions/${simulationId}?limit=20&offset=${offsetRef.current}`
          );
          if (!res.ok) return;
          const data = await res.json();
          const actions: SimulationEvent[] = data.actions ?? [];
          if (actions.length > 0) {
            offsetRef.current += actions.length;
            actions.reverse().forEach(addEvent);
            setIsConnected(true);
          }
        } catch {
          setIsConnected(false);
        }
      }, pollInterval);
    }

    return () => {
      esRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
      setIsConnected(false);
    };
  }, [simulationId, enabled, addEvent, pollInterval]);

  return { events, isConnected, isPaused, pause, resume, clear };
}
