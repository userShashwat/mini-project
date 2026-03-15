"""
Audio recording module
"""
import sounddevice as sd
import numpy as np
import threading
import queue
import time
import soundfile as sf
from datetime import datetime
from config.settings import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_DURATION

class AudioRecorder:
    def __init__(self, sample_rate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS):
        """
        Initialize audio recorder
        
        Args:
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.recorded_chunks = []
        self.thread = None
        
        # Check available devices
        self.devices = sd.query_devices()
        self.default_device = sd.default.device
        
        print(f"[AudioRecorder] Initialized with {sample_rate}Hz, {channels} channels")
        print(f"[AudioRecorder] Default device: {self.default_device}")
    
    def start_recording(self):
        """Start audio recording in background thread"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.recorded_chunks = []
        
        # Clear queue
        while not self.audio_queue.empty():
            self.audio_queue.get()
        
        self.thread = threading.Thread(target=self._record_audio, daemon=True)
        self.thread.start()
        print("[AudioRecorder] Started recording")
    
    def _record_audio(self):
        """Record audio continuously"""
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[AudioRecorder] Status: {status}")
            self.audio_queue.put(indata.copy())
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback,
                blocksize=int(self.sample_rate * 0.1)  # 100ms blocks
            ):
                while self.is_recording:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[AudioRecorder] Error: {e}")
            self.is_recording = False
    
    def get_audio_chunk(self, duration=AUDIO_DURATION):
        """
        Get a chunk of audio data
        
        Args:
            duration: Duration in seconds
            
        Returns:
            numpy array of audio data
        """
        samples_needed = int(self.sample_rate * duration)
        audio_chunk = []
        
        while len(audio_chunk) < samples_needed:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                audio_chunk.extend(chunk)
            except queue.Empty:
                break
        
        if audio_chunk:
            return np.array(audio_chunk)
        return None
    
    def save_recording(self, filename=None):
        """Save current recording to file"""
        if not self.recorded_chunks:
            return None
        
        if filename is None:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        audio_data = np.concatenate(self.recorded_chunks, axis=0)
        sf.write(filename, audio_data, self.sample_rate)
        return filename
    
    def stop_recording(self):
        """Stop audio recording"""
        self.is_recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        print("[AudioRecorder] Stopped recording")

# Test function
if __name__ == "__main__":
    # Test audio recording
    recorder = AudioRecorder()
    
    print("Recording for 5 seconds...")
    recorder.start_recording()
    
    # Record for 5 seconds
    time.sleep(5)
    
    # Get final chunk
    chunk = recorder.get_audio_chunk(5)
    if chunk is not None:
        print(f"Recorded audio shape: {chunk.shape}")
        recorder.recorded_chunks.append(chunk)
    
    recorder.stop_recording()
    
    # Save recording
    filename = recorder.save_recording()
    print(f"Saved recording to: {filename}")