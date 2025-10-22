"""
Podcast generation utilities.

This module provides utilities for:
- Bracket-format conversation parsing
- Content extraction from knowledge base items
- Text-to-speech generation via Higgs (primary) and OpenAI (fallback)
- Audio processing and concatenation (WAV output)
"""

import logging
import uuid
import json
import subprocess
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os   

import base64
import time
import requests
from django.conf import settings

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Content extraction limits
MAX_CONTENT_LENGTH = 8000
MAX_ITEM_PREVIEW_LENGTH = 500

logger = logging.getLogger(__name__)

# Module-level cache for Higgs client/model
_HIGGS_CLIENT_CACHE = None
_HIGGS_MODEL_CACHE = None


# =============================================================================
# CONVERSATION PARSING FUNCTIONS
# =============================================================================

def parse_conversation(conversation_text: str) -> List[Dict[str, str]]:
    """
    Parse conversation into structured turns using bracket format.
    
    Expected format: [speaker_name] content
    
    Args:
        conversation_text: Raw conversation text with bracket format
        
    Returns:
        List of conversation turns with speaker and content
    """
    conversation_turns = []
    
    # Pattern to match bracket format: [speaker] content
    pattern = r'\[([^\]]+)\]\s*(.*?)(?=\n\[|$)'
    matches = re.findall(pattern, conversation_text, re.DOTALL)
    
    for speaker, content in matches:
        # Clean up speaker name and content
        speaker = speaker.strip()
        content = content.strip()
        
        # Extract just the name from role descriptions (e.g., "AI研究科学家 - 伊利亚" -> "伊利亚")
        if " - " in speaker:
            speaker = speaker.split(" - ")[-1].strip()
        
        if speaker and content:
            conversation_turns.append({
                'speaker': speaker,
                'content': content
            })
    
    logger.info(f"Extracted {len(conversation_turns)} conversation turns from bracket format")
    return conversation_turns


# =============================================================================
# CONTENT EXTRACTION FUNCTIONS
# =============================================================================

async def extract_selected_content(selected_item_ids: List[int]) -> str:
    """
    Extract content from selected knowledge base items.
    
    Args:
        selected_item_ids: List of KnowledgeBaseItem IDs selected by frontend
        
    Returns:
        Extracted content string from selected items
    """
    if not selected_item_ids:
        return "No content selected for podcast generation."
    
    try:
        from asgiref.sync import sync_to_async
        from notebooks.models import KnowledgeBaseItem
        
        content_parts = []
        
        # Get selected knowledge base items asynchronously
        kb_items = await sync_to_async(list)(
            KnowledgeBaseItem.objects.filter(id__in=selected_item_ids)
        )
        
        for item in kb_items:
            
            # Add main content
            if hasattr(item, 'content') and item.content:
                content_parts.append(f"Content: {item.content}")
            elif hasattr(item, 'summary') and item.summary:
                content_parts.append(f"Summary: {item.summary}")
            
            # Add separator between items
            content_parts.append("---")
        
        # Join all content
        full_content = "\n\n".join(content_parts)
        
        # Return truncated content if too long
        if len(full_content) > MAX_CONTENT_LENGTH:
            return full_content[:MAX_CONTENT_LENGTH] + "..."
        
        return full_content if full_content else "No content found for selected items."
        
    except Exception as e:
        logger.error(f"Content extraction failed for selected items {selected_item_ids}: {e}")
        return f"Error extracting content: {str(e)}"


# =============================================================================
# AUDIO PROCESSING FUNCTIONS
# =============================================================================

def _get_higgs_client_and_model():
    """Create an OpenAI-compatible client for Higgs and choose a model.
    Returns a tuple (client, model_id).
    """
    try:
        from openai import OpenAI
    except Exception as e:
        logger.error(f"OpenAI client not available for Higgs: {e}")
        return None, None

    global _HIGGS_CLIENT_CACHE, _HIGGS_MODEL_CACHE
    if _HIGGS_CLIENT_CACHE and _HIGGS_MODEL_CACHE:
        return _HIGGS_CLIENT_CACHE, _HIGGS_MODEL_CACHE
    base_url = getattr(settings, 'HIGGS_API_BASE', 'http://localhost:8000/v1')
    model = getattr(settings, 'HIGGS_TTS_MODEL', None)
    try:
        client = OpenAI(api_key="EMPTY", base_url=base_url)
        if not model:
            # Discover first available model
            try:
                models = client.models.list()
                if models and getattr(models, 'data', None):
                    model = models.data[0].id
                else:
                    logger.error("Higgs: no models returned; set HIGGS_TTS_MODEL in settings")
                    return client, None
            except Exception as e:
                logger.error(f"Higgs: failed to list models: {e}")
                return client, None
        _HIGGS_CLIENT_CACHE, _HIGGS_MODEL_CACHE = client, model
        return _HIGGS_CLIENT_CACHE, _HIGGS_MODEL_CACHE
    except Exception as e:
        logger.error(f"Failed to init Higgs client: {e}")
        return None, None


def _higgs_smart_voice(text: str) -> Optional[bytes]:
    """Generate WAV audio bytes using Higgs 'smart voice' (no reference)."""
    client, model = _get_higgs_client_and_model()
    if not client or not model:
        return None
    scene_desc = getattr(settings, 'TTS_SCENE_PROMPT', 'Audio is recorded from a quiet room.')
    DEFAULT_SYSTEM_PROMPT = (
        "Generate audio following instruction.\n\n"
        "<|scene_desc_start|>\n"
        f"{scene_desc}\n"
        "<|scene_desc_end|>"
    )
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            model=model,
            modalities=["text", "audio"],
            temperature=1.0,
            top_p=0.95,
            extra_body={"top_k": 50},
            stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
        )
        audio_b64 = chat_completion.choices[0].message.audio.data
        return base64.b64decode(audio_b64)
    except Exception as e:
        logger.error(f"Higgs smart voice failed: {e}")
        return None


def _higgs_voice_clone(seed_audio_wav: bytes, seed_text: str, new_text: str) -> Optional[bytes]:
    """Generate WAV audio bytes using Higgs 'voice clone' given a seed audio+text."""
    client, model = _get_higgs_client_and_model()
    if not client or not model:
        return None
    try:
        audio_b64 = base64.b64encode(seed_audio_wav).decode("utf-8")
        messages = [
            {"role": "user", "content": seed_text},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": "wav"},
                    }
                ],
            },
            {"role": "user", "content": new_text},
        ]
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model,
            max_completion_tokens=1000,
            stream=False,
            modalities=["text", "audio"],
            temperature=1.0,
            top_p=0.95,
            extra_body={"top_k": 50},
            stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
        )
        audio_b64_out = chat_completion.choices[0].message.audio.data
        return base64.b64decode(audio_b64_out)
    except Exception as e:
        logger.error(f"Higgs voice clone failed: {e}")
        return None


def _openai_tts(text: str) -> Optional[bytes]:
    """Fallback TTS using OpenAI gpt-4o-mini-tts via REST to produce WAV bytes.
    Note: voice cloning is not supported here; used for both first and later segments if Higgs fails.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set; cannot use fallback TTS")
        return None


# =============================
# Text normalization and chunking
# =============================

FULL_TO_HALF_PUNCT = {
    "，": ",", "。": ".", "：": ":", "；": ";", "？": "?", "！": "!",
    "（": "(", "）": ")", "【": "[", "】": "]", "《": "<", "》": ">",
    "“": '"', "”": '"', "‘": "'", "’": "'", "、": ",", "—": "-",
    "…": "...", "·": ".", "「": '"', "」": '"', "『": '"', "』": '"',
}

def normalize_text_for_tts(text: str) -> str:
    if not getattr(settings, 'TTS_ENABLE_NORMALIZATION', True):
        return text
    # convert full-width punctuation; light cleanup
    for zh, en in FULL_TO_HALF_PUNCT.items():
        text = text.replace(zh, en)
    # lightweight symbol cleanup
    text = text.replace("\u200b", " ").strip()
    return text


PUNCT_SPLIT_REGEX = re.compile(r"([。.!！?？;；]\s*)")

def chunk_text_by_punct(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    parts: List[str] = []
    # split while keeping delimiters
    tokens = PUNCT_SPLIT_REGEX.split(text)
    buf = ""
    for tok in tokens:
        if len(buf) + len(tok) > max_chars and buf:
            parts.append(buf.strip())
            buf = tok
        else:
            buf += tok
    if buf.strip():
        parts.append(buf.strip())
    # fallback: if any very long chunk remains, force-cut
    out: List[str] = []
    for p in parts:
        if len(p) <= max_chars:
            out.append(p)
        else:
            for i in range(0, len(p), max_chars):
                out.append(p[i:i+max_chars])
    return out
    try:
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini-tts",
            "voice": "alloy",
            "input": text,
            "format": "wav",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.content if resp.content else None
    except Exception as e:
        logger.error(f"OpenAI TTS fallback failed: {e}")
        try:
            logger.error(f"Response: {resp.status_code} {resp.text[:200]}...")
        except Exception:
            pass
        return None


def generate_audio_segment(
    content: str,
    speaker: str,
    segment_index: int,
    audio_output_dir: Path,
    speaker_state: Dict[str, Dict[str, Any]],
) -> Optional[Path]:
    """
    Generate audio segment for a single conversation turn.
    
    Args:
        content: Text content to convert
        speaker: Speaker name
        segment_index: Index of this segment
        audio_output_dir: Directory for audio output
        speaker_state: Tracks first-segment seed per speaker for cloning
        
    Returns:
        Path to generated audio segment or None if failed
    """
    try:
        logger.debug(f"generate_audio_segment called: speaker='{speaker}', segment_index={segment_index}")
        
        # Prepare temp files
        temp_filename = f"segment_{segment_index:03d}_{speaker}.wav"
        temp_file_path = audio_output_dir / temp_filename
        
        # Optional normalization
        content_norm = normalize_text_for_tts(content)
        # Chunk long content
        max_chars = getattr(settings, 'TTS_MAX_CHARS_PER_CHUNK', 800)
        chunks = chunk_text_by_punct(content_norm, max_chars=max_chars)

        chunk_files: List[Path] = []
        start_ts = time.time()
        for ci, chunk in enumerate(chunks):
            path_used = None
            audio_bytes: Optional[bytes] = None
            origin = None
            if speaker not in speaker_state:
                # First chunk for this speaker → smart voice
                audio_bytes = _higgs_smart_voice(chunk)
                origin = 'higgs_smart'
                if audio_bytes:
                    # Cache seed only once (use first chunk output and text)
                    speaker_state[speaker] = {"seed_audio": audio_bytes, "seed_text": chunk, "history": [chunk]}
                else:
                    # fallback to OpenAI
                    audio_bytes = _openai_tts(chunk)
                    origin = 'openai_fallback'
            else:
                # Subsequent chunks → try clone first
                seed = speaker_state[speaker]
                hist_window = getattr(settings, 'TTS_HISTORY_WINDOW', 0)
                history = seed.get("history", [])
                context_suffix = ("\n" + "\n".join(history[-hist_window:])) if hist_window and history else ""
                audio_bytes = _higgs_voice_clone(seed.get("seed_audio", b""), seed.get("seed_text", ""), chunk + context_suffix)
                origin = 'higgs_clone'
                if not audio_bytes:
                    # Try trimmed seed text
                    trimmed_seed = seed.get("seed_text", "")[:200]
                    audio_bytes = _higgs_voice_clone(seed.get("seed_audio", b""), trimmed_seed, chunk)
                    origin = 'higgs_clone_trimmed'
                if not audio_bytes:
                    # As last resort, smart voice again
                    audio_bytes = _higgs_smart_voice(chunk)
                    origin = 'higgs_smart_retry'
                if not audio_bytes:
                    audio_bytes = _openai_tts(chunk)
                    origin = 'openai_fallback'

                # update history
                history.append(chunk)
                seed["history"] = history[-max(1, hist_window):] if hist_window else history

            if not audio_bytes:
                logger.warning(f"Chunk generation failed: seg={segment_index} chunk={ci} speaker={speaker}")
                continue

            # Write chunk wav
            chunk_file = audio_output_dir / f"segment_{segment_index:03d}_{speaker}_chunk{ci}.wav"
            os.makedirs(os.path.dirname(chunk_file), exist_ok=True)
            with open(chunk_file, "wb") as f:
                f.write(audio_bytes)
            # Apply fade + resample to unify format
            processed_chunk = _process_segment_wave(chunk_file)
            if processed_chunk:
                chunk_files.append(processed_chunk)
                # cleanup raw chunk
                try:
                    if chunk_file.exists():
                        chunk_file.unlink()
                except Exception:
                    pass
            else:
                chunk_files.append(chunk_file)

            logger.info(f"TTS chunk generated: seg={segment_index} chunk={ci} speaker={speaker} origin={origin} bytes={len(audio_bytes)}")

        if not chunk_files:
            logger.warning(f"Failed to generate any chunks for seg={segment_index} speaker={speaker}")
            return None

        # Concatenate chunk files into a single segment wav
        ok = concatenate_audio_segments(chunk_files, temp_file_path, audio_output_dir)
        # Cleanup chunk files
        for cf in chunk_files:
            try:
                if cf.exists():
                    cf.unlink()
            except Exception:
                pass
        if ok and temp_file_path.exists() and os.path.getsize(temp_file_path) > 0:
            logger.info(f"Segment generated: seg={segment_index} speaker={speaker} chunks={len(chunks)} dur_ms={int((time.time()-start_ts)*1000)}")
            return temp_file_path
        logger.warning(f"Generated segment but invalid file: {temp_file_path}")
        return None
            
    except Exception as e:
        logger.error(f"Error generating audio segment for {speaker}: {e}")
        return None


def generate_conversation_audio_optimized(
    conversation_turns: List[Dict[str, str]], 
    audio_output_dir: Path
) -> Optional[Path]:
    """
    Generate audio file from conversation turns using optimized approach:
    1. Group content by speaker
    2. Generate audio for each speaker's content in bulk
    3. Create individual segments and concatenate in original order
    
    Args:
        conversation_turns: List of conversation turns with speaker and content
        audio_output_dir: Directory for audio output
        
    Returns:
        Path to generated audio file or None if failed
    """
    try:
        # Track per-speaker seed (first segment) to support cloning later
        speaker_state: Dict[str, Dict[str, Any]] = {}

        # Generate per-turn segments in order, grouping by speaker implicitly
        audio_segments: List[Path] = []
        for i, turn in enumerate(conversation_turns):
            speaker = turn.get('speaker', '').strip()
            content = (turn.get('content') or '').strip()
            if not speaker or not content:
                continue
            segment_file = generate_audio_segment(
                content=content,
                speaker=speaker,
                segment_index=i,
                audio_output_dir=audio_output_dir,
                speaker_state=speaker_state,
            )
            if segment_file and segment_file.exists():
                audio_segments.append(segment_file)

        # Generate final audio file (WAV)
        if audio_segments:
            audio_filename = f"panel_podcast_optimized_{uuid.uuid4().hex[:8]}.wav"
            final_audio_path = audio_output_dir / audio_filename

            success = concatenate_audio_segments(audio_segments, final_audio_path, audio_output_dir)

            # Clean up temporary files
            for segment in audio_segments:
                try:
                    segment.unlink()
                except Exception:
                    pass

            if success and final_audio_path.exists():
                return final_audio_path

        logger.error("No audio segments generated in optimized approach")
        return None
        
    except Exception as e:
        logger.error(f"Optimized audio generation failed: {e}")
        return None


def concatenate_audio_segments(
    segments: List[Path], 
    output_file: Path, 
    audio_output_dir: Path
) -> bool:
    """
    Concatenate multiple audio segments into a single file.
    
    Args:
        segments: List of audio segment file paths
        output_file: Final output file path
        audio_output_dir: Directory for temporary files
        
    Returns:
        True if successful, False otherwise
    """
    if not segments:
        return False
    
    try:
        # Create a temporary file list for ffmpeg
        concat_list_file = audio_output_dir / f"concat_list_{uuid.uuid4().hex[:8]}.txt"
        
        with open(concat_list_file, 'w') as f:
            for segment in segments:
                f.write(f"file '{segment.absolute()}'\n")
        
        try:
            # Re-encode to enforce sample rate, mono, and avoid header mismatches
            target_sr = str(getattr(settings, 'TTS_TARGET_SAMPLE_RATE', 24000))
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", str(concat_list_file),
                "-ar", target_sr, "-ac", "1", "-c:a", "pcm_s16le",
                str(output_file)
            ], check=True, capture_output=True, timeout=300)
            
            # Clean up concat list file
            concat_list_file.unlink()
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback: copy first file if only one segment
            if len(segments) == 1:
                import shutil
                shutil.copy2(segments[0], output_file)
                return True
            else:
                logger.warning("ffmpeg not available and multiple segments - using simple concatenation")
                return _simple_audio_concatenation(segments, output_file)
        
        finally:
            # Clean up concat list file if it exists
            if concat_list_file.exists():
                try:
                    concat_list_file.unlink()
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"Error concatenating audio segments: {e}")
        return False


def _process_segment_wave(input_wav: Path) -> Optional[Path]:
    """Apply tiny fade in/out and resample to target SR/mono. Returns new file path."""
    try:
        target_sr = str(getattr(settings, 'TTS_TARGET_SAMPLE_RATE', 24000))
        fade_ms = max(0, int(getattr(settings, 'TTS_CROSSFADE_MS', 10)))
        fade_s = str(fade_ms / 1000.0)
        out_path = input_wav.with_name(input_wav.stem + "_proc.wav")
        # Apply fade in/out with afade; resample and set mono
        # For fade-out, estimate duration dynamically is hard without probing; we apply symmetric fades by re-encoding twice is complex.
        # Use short fade-in and fade-out by chaining filters; ffmpeg handles end fade with 'st=duration-...:d=...'.
        # We'll use simple fades that won't error if duration < fade length.
        cmd = [
            "ffmpeg", "-y", "-i", str(input_wav),
            "-af", f"afade=t=in:st=0:d={fade_s},afade=t=out:st=0:d={fade_s}",
            "-ar", target_sr, "-ac", "1", "-c:a", "pcm_s16le",
            str(out_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return out_path if out_path.exists() else None
    except Exception as e:
        logger.warning(f"Segment post-process failed for {input_wav}: {e}")
        return None


def _simple_audio_concatenation(segments: List[Path], output_file: Path) -> bool:
    """
    Simple fallback concatenation by combining binary data.
    
    Note: This is a basic approach and may not work well with all audio formats.
    """
    try:
        with open(output_file, 'wb') as outfile:
            for segment in segments:
                with open(segment, 'rb') as infile:
                    outfile.write(infile.read())
        return True
    except Exception as e:
        logger.error(f"Simple concatenation failed: {e}")
        return False


    # Minimax TTS removed
    pass
