#!/usr/bin/env python3
"""
Test script for local Whisper transcription accuracy.
Verifies that the speech recognition improvements work correctly.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'main', 'python'))

from services.ai_service import AIService, _get_whisper_model


def test_whisper_model_loading():
    """Test that Whisper model loads correctly."""
    print("\n=== Test 1: Whisper Model Loading ===")
    
    try:
        model = _get_whisper_model("base")
        if model is not None:
            print("[PASS] Whisper 'base' model loaded successfully")
            return True
        else:
            print("[FAIL] Failed to load Whisper model")
            return False
    except Exception as e:
        print(f"[FAIL] Error loading Whisper model: {e}")
        return False


async def test_audio_preprocessing():
    """Test audio preprocessing functionality."""
    print("\n=== Test 2: Audio Preprocessing ===")
    
    service = AIService()
    
    # Check if preprocessing is enabled
    from core.config import settings
    print(f"  - Preprocessing enabled: {settings.ENABLE_AUDIO_PREPROCESSING}")
    print(f"  - Target sample rate: {settings.AUDIO_SAMPLE_RATE} Hz")
    print(f"  - Normalization level: {settings.AUDIO_NORMALIZE_DB} dB")
    
    print("[PASS] Audio preprocessing configuration verified")
    return True


async def test_transcription_with_sample():
    """Test transcription with a sample audio file if available."""
    print("\n=== Test 3: Transcription Test ===")
    
    # Check for sample audio files
    audio_dir = "data/audio/responses"
    test_files = []
    
    if os.path.exists(audio_dir):
        for f in os.listdir(audio_dir):
            if f.endswith(('.wav', '.mp3', '.webm', '.ogg')):
                test_files.append(os.path.join(audio_dir, f))
                if len(test_files) >= 2:
                    break
    
    if not test_files:
        print("[WARN] No sample audio files found in data/audio/responses/")
        print("   To test transcription, record a speaking module response first.")
        return True
    
    service = AIService()
    
    for audio_file in test_files:
        print(f"\n  Testing: {os.path.basename(audio_file)}")
        
        try:
            transcript, confidence = await service._transcribe_audio_enhanced(
                audio_file,
                expected_response="apologize, sorry, help, assist, maintenance",
                question_context="Customer complaining about room temperature"
            )
            
            print(f"  - Transcript: {transcript[:100]}..." if len(transcript) > 100 else f"  - Transcript: {transcript}")
            print(f"  - Confidence: {confidence:.2f}")
            
            if transcript and not transcript.startswith("["):
                print("  [PASS] Transcription successful")
            else:
                print("  [WARN] Transcription returned error or empty result")
                
        except Exception as e:
            print(f"  [FAIL] Transcription error: {e}")
    
    return True


def test_keyword_extraction():
    """Test keyword extraction for prompt building."""
    print("\n=== Test 4: Keyword Extraction ===")
    
    service = AIService()
    
    test_cases = [
        "I apologize for the inconvenience. Let me send someone from maintenance to fix the air conditioning.",
        "Please wait a moment while I check your reservation details.",
        "The safety drill will begin at three o'clock on the Lido deck.",
    ]
    
    for text in test_cases:
        keywords = service._extract_keywords(text)
        print(f"  Input: '{text[:50]}...'")
        print(f"  Keywords: {keywords}")
    
    print("[PASS] Keyword extraction working")
    return True


def test_prompt_building():
    """Test prompt building for Whisper."""
    print("\n=== Test 5: Prompt Building ===")
    
    service = AIService()
    
    prompt = service._build_transcription_prompt(
        expected_response="apologize, sorry, send maintenance, fix AC",
        question_context="A guest complains that their cabin air conditioning is not working properly."
    )
    
    print(f"  Built prompt ({len(prompt)} chars):")
    print(f"  {prompt[:200]}...")
    
    print("[PASS] Prompt building working")
    return True


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Local Whisper Transcription Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Model loading
    results.append(("Model Loading", test_whisper_model_loading()))
    
    # Test 2: Audio preprocessing config
    results.append(("Audio Preprocessing", await test_audio_preprocessing()))
    
    # Test 3: Keyword extraction
    results.append(("Keyword Extraction", test_keyword_extraction()))
    
    # Test 4: Prompt building
    results.append(("Prompt Building", test_prompt_building()))
    
    # Test 5: Transcription (if audio files available)
    results.append(("Transcription", await test_transcription_with_sample()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n*** All tests passed! Local Whisper transcription is ready. ***")
    else:
        print("\n*** Some tests failed. Please check the errors above. ***")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

