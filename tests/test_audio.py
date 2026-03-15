"""
Test script for audio modules
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from modules.audio.recorder import AudioRecorder
from modules.audio.analyzer import AudioAnalyzer

def test_audio_recording():
    """Test audio recording"""
    print("\n=== Testing Audio Recording ===")
    
    recorder = AudioRecorder()
    recorder.start_recording()
    
    print("Recording for 5 seconds...")
    time.sleep(5)
    
    # Get audio chunk
    chunk = recorder.get_audio_chunk(3)
    if chunk is not None:
        print(f"Recorded audio shape: {chunk.shape}")
        recorder.recorded_chunks.append(chunk)
    
    # Save recording
    filename = recorder.save_recording()
    print(f"Saved recording to: {filename}")
    
    recorder.stop_recording()
    return True

def test_audio_analysis():
    """Test audio analysis"""
    print("\n=== Testing Audio Analysis ===")
    
    recorder = AudioRecorder()
    analyzer = AudioAnalyzer()
    
    recorder.start_recording()
    
    print("Analyzing audio for 10 seconds...")
    print("Speak or make noise to see detection")
    
    try:
        for i in range(20):  # 10 seconds at 0.5s chunks
            chunk = recorder.get_audio_chunk(0.5)
            if chunk is not None:
                analysis = analyzer.analyze_audio(chunk)
                print(f"Voice: {analysis['voice_activity']:5} | "
                      f"Energy: {analysis['voice_energy']:.3f} | "
                      f"Speakers: {analysis['speaker_count']} | "
                      f"Multiple: {analysis['multiple_voices']}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nTest interrupted")
    
    recorder.stop_recording()
    analyzer.stop()
    return True

if __name__ == "__main__":
    print("Audio Module Tests")
    print("=" * 50)
    
    test_audio_recording()
    test_audio_analysis()
    
    print("\nAll audio tests completed!")