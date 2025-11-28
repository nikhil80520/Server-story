#!/usr/bin/env python3
"""
Script to create a universal fallback ambient sound for stories
This creates a gentle, unobtrusive background sound that works for any story
"""

from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise
import os

def create_gentle_ambient(duration_ms=30000, output_path="gentle_ambient.wav"):
    """
    Create a gentle, CHILD-FRIENDLY ambient sound suitable for any story.
    Uses soft, pleasant tones that are calming and appropriate for young children.
    Think: gentle music box, soft bells, peaceful nature sounds.
    
    Args:
        duration_ms: Duration in milliseconds (default 30 seconds)
        output_path: Where to save the audio file
    """
    print(f"🎵 Creating child-friendly ambient sound ({duration_ms/1000}s)...")
    
    # Create a gentle, pleasant musical ambient perfect for children's stories
    # Think of it like a soft music box or gentle bells in the distance
    
    # Layer 1: Soft major chord (C major - happy, calming)
    # Using frequencies that form a pleasant C major chord
    note_c = Sine(261.63).to_audio_segment(duration=duration_ms)  # C4
    note_e = Sine(329.63).to_audio_segment(duration=duration_ms)  # E4
    note_g = Sine(392.00).to_audio_segment(duration=duration_ms)  # G4
    
    # Make them very soft and gentle
    note_c = note_c - 35  # Very quiet
    note_e = note_e - 37  # Even quieter
    note_g = note_g - 39  # Quietest
    
    # Layer 2: Add some gentle "sparkle" with a high note (like a music box)
    high_note = Sine(523.25).to_audio_segment(duration=duration_ms)  # C5 (octave higher)
    high_note = high_note - 42  # Very faint sparkle
    
    # Layer 3: Very gentle pink noise (softer than white noise - more natural)
    # Pink noise sounds like gentle rain or soft wind
    pink_noise = WhiteNoise().to_audio_segment(duration=duration_ms)
    pink_noise = pink_noise - 40  # Extremely quiet background texture
    
    # Mix all layers to create a pleasant, calming soundscape
    print("🎼 Mixing child-friendly layers...")
    ambient = note_c.overlay(note_e).overlay(note_g).overlay(high_note)
    ambient = ambient.overlay(pink_noise)
    
    # Apply gentle fade in/out for smooth looping (longer fade for more gentle effect)
    fade_duration = 3000  # 3 second fade - more gradual and gentle
    ambient = ambient.fade_in(fade_duration).fade_out(fade_duration)
    
    # Normalize to consistent, gentle level
    from pydub.effects import normalize
    ambient = normalize(ambient)
    # Reduce overall volume to ensure it's truly background
    ambient = ambient - 8  # Reduce by 8dB for very gentle background
    
    print(f"💾 Exporting to {output_path}...")
    # Export as WAV for best quality (will be compressed when mixed with narration)
    ambient.export(output_path, format="wav")
    
    file_size = os.path.getsize(output_path)
    print(f"✅ Created child-friendly ambient sound: {file_size:,} bytes")
    print(f"   Duration: {duration_ms/1000}s")
    print(f"   Format: WAV (uncompressed)")
    print(f"   Characteristics: Gentle, musical, child-friendly, calming")
    print(f"   Musical: Soft C major chord with gentle sparkle")
    
    return output_path

if __name__ == "__main__":
    import sys
    
    # Get output directory from command line or use default
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./static/fallback_audio"
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "universal_ambient.wav")
    
    print(f"📁 Output directory: {output_dir}")
    create_gentle_ambient(duration_ms=30000, output_path=output_path)
    
    print(f"\n✅ Done! Fallback ambient sound ready at:")
    print(f"   {output_path}")
    print(f"\n💡 This sound will be used as fallback when:")
    print(f"   - Freesound API is unavailable")
    print(f"   - No matching ambient sound is found")
    print(f"   - Download fails after retries")
