"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, MicOff, Pause, Play, StopCircle, Languages, Settings } from 'lucide-react';
import { useVoiceRecognition } from '@/hooks/useVoiceRecognition';
import { formatDuration } from '@/lib/utils';

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  onSubmit?: (text: string) => void;
  language?: string;
  autoSubmit?: boolean;
  className?: string;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
  onTranscript,
  onSubmit,
  language = 'en-US',
  autoSubmit = false,
  className = '',
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [duration, setDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState(language);
  const [showLanguageMenu, setShowLanguageMenu] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const {
    isSupported,
    isListening,
    transcript: voiceTranscript,
    interimTranscript: voiceInterim,
    error,
    startListening,
    stopListening,
    resetTranscript,
  } = useVoiceRecognition({
    lang: selectedLanguage,
    continuous: true,
    interimResults: true,
  });

  // Supported languages
  const languages = [
    { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
    { code: 'en-GB', name: 'English (UK)', flag: '🇬🇧' },
    { code: 'es-ES', name: 'Spanish', flag: '🇪🇸' },
    { code: 'fr-FR', name: 'French', flag: '🇫🇷' },
    { code: 'de-DE', name: 'German', flag: '🇩🇪' },
    { code: 'it-IT', name: 'Italian', flag: '🇮🇹' },
    { code: 'pt-BR', name: 'Portuguese', flag: '🇧🇷' },
    { code: 'ru-RU', name: 'Russian', flag: '🇷🇺' },
    { code: 'ja-JP', name: 'Japanese', flag: '🇯🇵' },
    { code: 'ko-KR', name: 'Korean', flag: '🇰🇷' },
    { code: 'zh-CN', name: 'Chinese (Simplified)', flag: '🇨🇳' },
    { code: 'ar-SA', name: 'Arabic', flag: '🇸🇦' },
    { code: 'hi-IN', name: 'Hindi', flag: '🇮🇳' },
  ];

  // Update transcript when voice recognition updates
  useEffect(() => {
    if (voiceTranscript) {
      setTranscript(voiceTranscript);
      onTranscript(voiceTranscript);
    }
    if (voiceInterim) {
      setInterimTranscript(voiceInterim);
    }
  }, [voiceTranscript, voiceInterim, onTranscript]);

  // Timer for recording duration
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording, isPaused]);

  // Audio level visualization
  const updateAudioLevel = useCallback(() => {
    if (analyserRef.current && isRecording && !isPaused) {
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(Math.min(100, (average / 255) * 100));
      animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
    }
  }, [isRecording, isPaused]);

  useEffect(() => {
    if (isRecording && !isPaused) {
      updateAudioLevel();
    } else {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      setAudioLevel(0);
    }
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isRecording, isPaused, updateAudioLevel]);

  // Initialize audio context for visualization
  const initializeAudioContext = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);
    } catch (error) {
      console.error('Failed to initialize audio context:', error);
    }
  };

  const handleStartRecording = async () => {
    setIsRecording(true);
    setIsPaused(false);
    setDuration(0);
    resetTranscript();
    await initializeAudioContext();
    startListening();
  };

  const handlePauseRecording = () => {
    setIsPaused(!isPaused);
    if (!isPaused) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    setIsPaused(false);
    stopListening();

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (autoSubmit && transcript) {
      onSubmit?.(transcript);
      setTranscript('');
      setInterimTranscript('');
    }
  };

  const handleSubmit = () => {
    if (transcript) {
      onSubmit?.(transcript);
      setTranscript('');
      setInterimTranscript('');
      handleStopRecording();
    }
  };

  const handleLanguageChange = (langCode: string) => {
    setSelectedLanguage(langCode);
    setShowLanguageMenu(false);
    if (isRecording) {
      stopListening();
      setTimeout(() => startListening(), 100);
    }
  };

  if (!isSupported) {
    return (
      <div className="p-4 text-sm text-yellow-800 bg-yellow-100 border border-yellow-300 rounded-lg dark:bg-yellow-900/20 dark:text-yellow-400">
        Voice input is not supported in your browser. Please use Chrome, Edge, or Safari.
      </div>
    );
  }

  return (
    <div className={`voice-input-container ${className}`}>
      {/* Transcript Display */}
      {(isRecording || transcript) && (
        <div className="mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="mb-2 text-xs font-medium text-gray-600 dark:text-gray-400">
            Transcript:
          </div>
          <div className="min-h-[60px] max-h-[200px] overflow-y-auto">
            <p className="text-sm text-gray-900 dark:text-white">
              {transcript}
              {interimTranscript && (
                <span className="text-gray-500 dark:text-gray-400"> {interimTranscript}</span>
              )}
            </p>
          </div>
          {isRecording && (
            <div className="mt-3 flex items-center gap-3">
              {/* Audio Level Visualization */}
              <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-100"
                  style={{ width: `${audioLevel}%` }}
                />
              </div>
              {/* Duration */}
              <span className="text-xs font-mono text-gray-600 dark:text-gray-400">
                {formatDuration(duration)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-2">
        {!isRecording ? (
          <button
            onClick={handleStartRecording}
            className="flex items-center justify-center w-12 h-12 text-white bg-blue-600 rounded-full hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 transition-all hover:scale-105"
            aria-label="Start recording"
            title="Start voice input"
          >
            <Mic className="w-5 h-5" />
          </button>
        ) : (
          <>
            {/* Pause/Resume */}
            <button
              onClick={handlePauseRecording}
              className="flex items-center justify-center w-10 h-10 text-gray-700 bg-gray-200 rounded-full hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              aria-label={isPaused ? 'Resume recording' : 'Pause recording'}
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </button>

            {/* Stop */}
            <button
              onClick={handleStopRecording}
              className="flex items-center justify-center w-12 h-12 text-white bg-red-600 rounded-full hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 transition-all hover:scale-105 animate-pulse"
              aria-label="Stop recording"
              title="Stop recording"
            >
              <StopCircle className="w-5 h-5" />
            </button>

            {/* Submit (if not auto-submit) */}
            {!autoSubmit && transcript && (
              <button
                onClick={handleSubmit}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
              >
                Submit
              </button>
            )}
          </>
        )}

        {/* Language Selector */}
        <div className="relative ml-auto">
          <button
            onClick={() => setShowLanguageMenu(!showLanguageMenu)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"
            aria-label="Select language"
          >
            <Languages className="w-4 h-4" />
            <span className="hidden sm:inline">
              {languages.find((l) => l.code === selectedLanguage)?.flag}
            </span>
          </button>

          {/* Language Menu */}
          {showLanguageMenu && (
            <div className="absolute right-0 z-10 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg dark:bg-gray-800 dark:border-gray-700 max-h-96 overflow-y-auto">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => handleLanguageChange(lang.code)}
                  className={`w-full flex items-center gap-3 px-4 py-2 text-sm text-left hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    selectedLanguage === lang.code
                      ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                      : 'text-gray-700 dark:text-gray-300'
                  }`}
                >
                  <span className="text-xl">{lang.flag}</span>
                  <span>{lang.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 p-3 text-sm text-red-800 bg-red-100 border border-red-300 rounded-lg dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Instructions */}
      {!isRecording && !transcript && (
        <p className="mt-3 text-xs text-center text-gray-500 dark:text-gray-500">
          Click the microphone to start speaking. Your speech will be transcribed in real-time.
        </p>
      )}
    </div>
  );
};
