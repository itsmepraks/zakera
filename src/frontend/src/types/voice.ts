/**
 * Voice Input Type Definitions
 */

export interface VoiceRecognitionConfig {
  lang: string;
  continuous?: boolean;
  interimResults?: boolean;
  maxAlternatives?: number;
}

export interface VoiceRecognitionHook {
  isSupported: boolean;
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
}

export interface AudioVisualizationData {
  timestamp: number;
  level: number;
}
