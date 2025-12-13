#!/usr/bin/env python3
"""
Generate natural-sounding audio files using Edge TTS
Replaces machine-like browser TTS with human-like neural voices
"""

import json
import asyncio
import edge_tts
from pathlib import Path
import sys

# Add src/main/python to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src" / "main" / "python"
sys.path.insert(0, str(src_path))

# Paths
questions_config_path = src_path / "data" / "questions_config.json"
audio_output_dir = src_path / "static" / "audio"
audio_output_dir.mkdir(parents=True, exist_ok=True)

# Edge TTS voice selection (natural neural voices)
VOICE = "en-US-JennyNeural"  # Natural female voice
# Alternative: "en-US-GuyNeural" for male voice


async def generate_audio(text: str, output_path: Path) -> bool:
    """
    Generate audio file from text using Edge TTS
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Try with rate and pitch adjustments for more natural sound
        communicate = edge_tts.Communicate(text, VOICE, rate="+0%", pitch="+0Hz")
        await communicate.save(str(output_path))
        print(f"✅ Generated: {output_path.name}")
        return True
    except Exception as e:
        # If 403 error, try alternative voice or method
        if "403" in str(e) or "Invalid response" in str(e):
            print(f"⚠️  Edge TTS API error, trying alternative method...")
            try:
                # Try with different voice
                alt_voice = "en-US-AriaNeural"
                communicate = edge_tts.Communicate(text, alt_voice)
                await communicate.save(str(output_path))
                print(f"✅ Generated with alternative voice: {output_path.name}")
                return True
            except Exception as e2:
                print(f"❌ Error generating {output_path.name}: {e2}")
                print(f"   Note: Edge TTS may require network access or have rate limits")
                print(f"   You can manually generate audio files or use the TTS fallback")
                return False
        else:
            print(f"❌ Error generating {output_path.name}: {e}")
            return False


async def main():
    """Generate audio files for all questions with audio_text"""
    
    print("=" * 70)
    print("Generating Natural Voice Audio Files with Edge TTS")
    print("=" * 70)
    print(f"Voice: {VOICE}")
    print(f"Output directory: {audio_output_dir}")
    print()
    
    # Load questions config
    if not questions_config_path.exists():
        print(f"❌ Questions config not found: {questions_config_path}")
        return
    
    with open(questions_config_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    # Find all questions with audio_text
    audio_questions = []
    for q_num, q_data in questions.items():
        if "audio_text" in q_data:
            audio_questions.append((q_num, q_data))
    
    print(f"Found {len(audio_questions)} questions with audio text")
    print()
    
    # Generate audio files
    success_count = 0
    for q_num, q_data in audio_questions:
        audio_text = q_data["audio_text"]
        module = q_data.get("module", "unknown")
        
        # Generate filename: q{number}_{module}.mp3
        filename = f"q{q_num}_{module}.mp3"
        output_path = audio_output_dir / filename
        
        print(f"Generating Q{q_num} ({module}): {audio_text[:50]}...")
        
        success = await generate_audio(audio_text, output_path)
        if success:
            success_count += 1
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    print()
    print("=" * 70)
    print(f"✅ Generated {success_count}/{len(audio_questions)} audio files")
    print("=" * 70)
    
    if success_count == len(audio_questions):
        print("🎉 All audio files generated successfully!")
    else:
        print(f"⚠️  {len(audio_questions) - success_count} files failed to generate")


if __name__ == "__main__":
    asyncio.run(main())

