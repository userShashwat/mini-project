"""
Audio analysis module for voice activity and multiple speakers detection
"""
import numpy as np
import scipy.signal
from scipy.io import wavfile
import threading
from collections import deque
import time
from config.settings import AUDIO_THRESHOLD, MULTIPLE_VOICES_THRESHOLD

class AudioAnalyzer:
    def __init__(self, sample_rate=16000):
        """
        Initialize audio analyzer
        
        Args:
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate
        self.voice_activity = False
        self.voice_energy = 0
        self.speaker_count = 0
        self.multiple_voices_detected = False
        self.background_noise_level = 0
        
        # History for smoothing
        self.energy_history = deque(maxlen=50)
        self.voice_activity_history = deque(maxlen=10)
        
        # Voice detection parameters
        self.voice_threshold = AUDIO_THRESHOLD
        self.silence_threshold = 0.01
        self.min_voice_frequency = 85  # Hz
        self.max_voice_frequency = 255  # Hz
        
        # Multiple speakers detection
        self.f0_history = deque(maxlen=100)  # Fundamental frequency history
        
        # Threading
        self.lock = threading.Lock()
        self.is_running = True
        
        print("[AudioAnalyzer] Initialized")
    
    def analyze_audio(self, audio_data):
        """
        Analyze audio chunk for voice activity and multiple speakers
        
        Args:
            audio_data: numpy array of audio samples
            
        Returns:
            dict with analysis results
        """
        if audio_data is None or len(audio_data) == 0:
            return self._get_empty_analysis()
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Normalize
        audio_data = audio_data / np.max(np.abs(audio_data) + 1e-10)
        
        # Calculate energy
        energy = np.sqrt(np.mean(audio_data**2))
        self.energy_history.append(energy)
        
        # Adaptive threshold
        if len(self.energy_history) > 10:
            background_noise = np.percentile(self.energy_history, 20)
            dynamic_threshold = max(self.voice_threshold, background_noise * 2)
        else:
            dynamic_threshold = self.voice_threshold
            background_noise = 0
        
        # Voice activity detection
        voice_active = energy > dynamic_threshold
        self.voice_activity_history.append(voice_active)
        
        # Smooth voice activity
        smoothed_voice = sum(self.voice_activity_history) / len(self.voice_activity_history) > 0.3
        
        # Multiple speakers detection (simplified)
        multiple_speakers = False
        if smoothed_voice and len(audio_data) > self.sample_rate * 0.1:  # At least 100ms
            # Simple pitch-based multiple speaker detection
            # In production, use more sophisticated methods
            f0 = self._estimate_pitch(audio_data)
            if f0 is not None:
                self.f0_history.append(f0)
                
                # Check for multiple distinct pitches
                if len(self.f0_history) > 20:
                    unique_pitches = len(set([round(p/10) for p in self.f0_history if p > 0]))
                    multiple_speakers = unique_pitches > 2
        
        with self.lock:
            self.voice_activity = smoothed_voice
            self.voice_energy = energy
            self.multiple_voices_detected = multiple_speakers
            self.background_noise_level = background_noise
            
            # Count speakers (simplified)
            if multiple_speakers:
                self.speaker_count = 2
            elif smoothed_voice:
                self.speaker_count = 1
            else:
                self.speaker_count = 0
        
        return self.get_analysis()
    
    def _estimate_pitch(self, audio_data):
        """Estimate fundamental frequency using autocorrelation"""
        # Autocorrelation pitch detection
        correlation = np.correlate(audio_data, audio_data, mode='full')
        correlation = correlation[len(correlation)//2:]
        
        # Find peaks
        min_freq_idx = int(self.sample_rate / self.max_voice_frequency)
        max_freq_idx = int(self.sample_rate / self.min_voice_frequency)
        
        if max_freq_idx >= len(correlation):
            return None
        
        peak_idx = np.argmax(correlation[min_freq_idx:max_freq_idx]) + min_freq_idx
        
        if correlation[peak_idx] < 0.1 * correlation[0]:
            return None
        
        f0 = self.sample_rate / peak_idx
        return f0
    
    def _get_empty_analysis(self):
        """Return empty analysis result"""
        return {
            'voice_activity': False,
            'voice_energy': 0,
            'speaker_count': 0,
            'multiple_voices': False,
            'background_noise': 0
        }
    
    def get_analysis(self):
        """Get current audio analysis"""
        with self.lock:
            return {
                'voice_activity': self.voice_activity,
                'voice_energy': self.voice_energy,
                'speaker_count': self.speaker_count,
                'multiple_voices': self.multiple_voices_detected,
                'background_noise': self.background_noise_level
            }
    
    def stop(self):
        """Stop audio analyzer"""
        self.is_running = False
        print("[AudioAnalyzer] Stopped")

# Test function
if __name__ == "__main__":
    from recorder import AudioRecorder
    
    # Test audio analysis
    recorder = AudioRecorder()
    analyzer = AudioAnalyzer()
    
    print("Analyzing audio for 10 seconds...")
    recorder.start_recording()
    
    try:
        for i in range(20):  # 10 seconds at 0.5s chunks
            chunk = recorder.get_audio_chunk(0.5)
            if chunk is not None:
                analysis = analyzer.analyze_audio(chunk)
                print(f"Voice: {analysis['voice_activity']}, "
                      f"Energy: {analysis['voice_energy']:.3f}, "
                      f"Speakers: {analysis['speaker_count']}, "
                      f"Multiple: {analysis['multiple_voices']}")
            time.sleep(0.5)
    finally:
        recorder.stop_recording()
        analyzer.stop()