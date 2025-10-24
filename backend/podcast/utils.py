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
import unicodedata
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import os

import base64
import requests
from django.conf import settings

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Content extraction limits
MAX_CONTENT_LENGTH = 8000
MAX_ITEM_PREVIEW_LENGTH = 500

logger = logging.getLogger(__name__)


# =============================================================================
# CONVERSATION PARSING FUNCTIONS
# =============================================================================

def parse_conversation(conversation_text: str) -> Tuple[Optional[str], str]:
    """
    Extract only the title from the conversation text and keep the
    original conversation content unchanged.

    Expected format (title optional):
    #播客标题
    [speaker_name] content
    [speaker_name] content

    Returns (title, original_text)
    - title: Extracted from first line starting with '#', otherwise None
    - original_text: The input conversation_text unchanged
    """
    title: Optional[str] = None
    lines = conversation_text.split('\n')
    if lines and lines[0].strip().startswith('#'):
        title = lines[0].strip()[1:].strip()
        logger.info(f"Extracted podcast title: {title}")
    return title, conversation_text


def parse_bracket_turns(conversation_text: str) -> List[Dict[str, str]]:
    """
    Parse bracket-formatted conversation into structured turns without altering
    original content or speaker names.

    Pattern: [speaker] content ... until next [ or end.
    """
    pattern = r'\[([^\]]+)\]\s*(.*?)(?=\n\[|$)'
    matches = re.findall(pattern, conversation_text, re.DOTALL)
    turns: List[Dict[str, str]] = []
    for speaker, content in matches:
        s = speaker.strip()
        c = content.strip()
        if s and c:
            turns.append({'speaker': s, 'content': c})
    logger.info(f"Extracted {len(turns)} conversation turns from bracket format")
    return turns


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

def _normalize_chinese_punctuation(text: str) -> str:
    """Convert full-width Chinese punctuation to half-width English equivalents."""
    mapping = {
        "，": ", ",
        "。": ".",
        "：": ":",
        "；": ";",
        "？": "?",
        "！": "!",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "《": "<",
        "》": ">",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "、": ",",
        "—": "-",
        "…": "...",
        "·": ".",
        "「": '"',
        "」": '"',
        "『": '"',
        "』": '"',
    }
    for zh, en in mapping.items():
        text = text.replace(zh, en)
    return text


def _remove_extra_punctuation(text: str) -> str:
    """
    Remove all punctuation except comma, period, exclamation mark, and question mark.
    Preserves XML-like tags (e.g., <SE>, </SE>) used for TTS special events.

    Keeps: , . ! ? ， 。 ！ ？ (and XML tags)
    Removes: All other punctuation including : ; " ' ( ) [ ] - — … etc.
    """
    # Pattern to match XML-like tags (e.g., <SE>, </SE>, <SE_s>, <SE_e>)
    tag_pattern = r'<[^>]+>'

    # Find all tags and replace them with placeholders
    tags = re.findall(tag_pattern, text)
    placeholder_template = "___TAG{:04d}___"
    for i, tag in enumerate(tags):
        text = text.replace(tag, placeholder_template.format(i), 1)

    # Now remove unwanted punctuation
    result = []
    for char in text:
        # Keep alphanumeric and whitespace
        if char.isalnum() or char.isspace() or char == '_':
            result.append(char)
        # Keep allowed punctuation (comma, period, exclamation, question mark)
        elif char in ',.!?，。！？':
            result.append(char)
        # Check if it's a punctuation character in Unicode
        elif unicodedata.category(char).startswith('P'):
            # Skip this punctuation - it's not in our allowed list
            continue
        else:
            # Keep other characters (e.g., Chinese characters, special symbols that aren't punctuation)
            result.append(char)

    text = ''.join(result)

    # Restore tags
    for i, tag in enumerate(tags):
        text = text.replace(placeholder_template.format(i), tag)

    return text


def normalize_tts_text(text: str) -> str:
    """Normalize transcript/content prior to TTS generation.

    Performs the following steps:
    1. Convert Chinese punctuation to English equivalents
    2. Replace temperature units
    3. Convert stage/event markers to TTS-compatible tags
    4. Remove all punctuation except comma, period, exclamation mark, and question mark
    5. Collapse excessive whitespace
    6. Ensure terminal punctuation
    """
    if not text:
        return text

    # 1) Chinese punctuation to half-width
    text = _normalize_chinese_punctuation(text)

    # 2) Replace temperature units (before removing punctuation)
    text = text.replace("°F", " degrees Fahrenheit")
    text = text.replace("°C", " degrees Celsius")

    # 3) Convert common stage/event markers to tags the model can understand
    # Note: Do this BEFORE removing punctuation so we can match [brackets]
    stage_tags = [
        ("[laugh]", "<SE>[Laughter]</SE>"),
        ("[humming start]", "<SE_s>[Humming]</SE_s>"),
        ("[humming end]", "<SE_e>[Humming]</SE_e>"),
        ("[music start]", "<SE_s>[Music]</SE_s>"),
        ("[music end]", "<SE_e>[Music]</SE_e>"),
        ("[music]", "<SE>[Music]</SE>"),
        ("[sing start]", "<SE_s>[Singing]</SE_s>"),
        ("[sing end]", "<SE_e>[Singing]</SE_e>"),
        ("[applause]", "<SE>[Applause]</SE>"),
        ("[cheering]", "<SE>[Cheering]</SE>"),
        ("[cough]", "<SE>[Cough]</SE>"),
    ]
    for a, b in stage_tags:
        text = text.replace(a, b)

    # 4) Remove all punctuation except comma, period, exclamation mark, and question mark
    # This includes: parentheses, brackets, quotes, colons, semicolons, dashes, etc.
    text = _remove_extra_punctuation(text)

    # 5) Collapse excessive whitespace and empty lines
    lines = [" ".join(line.split()) for line in text.split("\n") if line.strip()]
    text = "\n".join(lines).strip()

    # 6) Ensure terminal punctuation for smoother prosody
    if text and not any(text.endswith(c) for c in [".", "!", "?", ",", "。", "！", "？", "，", "</SE_e>", "</SE>"]):
        text += "."

    return text


# =============================================================================
# HIGGS TTS SESSION (INIT ONCE PER AUDIO JOB)
# =============================================================================

class HiggsTTSSession:
    """
    Manage a single OpenAI-compatible client + model for Higgs across one audio job.
    Avoids repeated model listing and client creation per chunk.
    """

    def __init__(self) -> None:
        self.client = None
        self.model = None
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover - optional dependency
            logger.error(f"OpenAI client not available for Higgs: {e}")
            return

        base_url = getattr(settings, 'HIGGS_API_BASE', 'http://localhost:8000/v1')
        model = getattr(settings, 'HIGGS_TTS_MODEL', None)
        try:
            client = OpenAI(api_key="EMPTY", base_url=base_url)  # type: ignore
            if not model:
                try:
                    models = client.models.list()
                    if models and getattr(models, 'data', None):
                        model = models.data[0].id
                    else:
                        logger.error("Higgs: no models returned; set HIGGS_TTS_MODEL in settings")
                except Exception as e:
                    logger.error(f"Higgs: failed to list models: {e}")
            self.client = client
            self.model = model
        except Exception as e:
            logger.error(f"Failed to init Higgs client: {e}")
            self.client = None
            self.model = None

    def smart_voice(self, text: str) -> Optional[bytes]:
        if not self.client or not self.model:
            return None
        DEFAULT_SYSTEM_PROMPT = (
            "Generate audio following instruction.\n\n"
            "<|scene_desc_start|>\n"
            "Audio is recorded from a quiet room.\n"
            "Speaker will speak chinese mixed with a few english words.\n"
            "<|scene_desc_end|>"
        )
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                model=self.model,
                max_completion_tokens=1000,
                stream=False,
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

    def voice_clone(self, seed_audio_wav: bytes, seed_text: str, new_text: str) -> Optional[bytes]:
        if not self.client or not self.model:
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
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
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


def _chunk_text_by_length(text: str, max_chars: int = 250) -> List[str]:
    """
    Chunk a single speaker's turn into smaller pieces by length, with boundary awareness.

    Strategy:
    - Prefer splitting at strong boundaries within the window: "\n\n" > "\n" > sentence punctuation (。！？；.!?;:) > comma/space.
    - As a last resort, hard-cut at max_chars.
    - Avoid cutting inside simple XML-like tags (e.g., <SE>...</SE>): if the cut falls within an unclosed '<', backtrack to before '<'.
    """
    if not text:
        return []

    text = text.strip()
    n = len(text)
    i = 0
    out: List[str] = []
    strong_punct = "。！？；.!?:;"

    def _avoid_mid_tag(start: int, end: int) -> int:
        segment = text[start:end]
        last_lt = segment.rfind("<")
        last_gt = segment.rfind(">")
        if last_lt != -1 and (last_gt == -1 or last_lt > last_gt):
            # We're inside a tag; backtrack to before '<'
            return start + last_lt
        return end

    while i < n:
        j = min(i + max_chars, n)
        window = text[i:j]

        cut = -1
        # 1) Double newline
        cut = window.rfind("\n\n")
        if cut == -1:
            # 2) Single newline
            cut = window.rfind("\n")
        if cut == -1:
            # 3) Sentence punctuation
            cut = max((window.rfind(c) for c in strong_punct), default=-1)
        if cut == -1:
            # 4) Comma/space
            cut = max(window.rfind(","), window.rfind(" "))

        if cut != -1 and i + cut + 1 <= n:
            candidate_end = i + cut + 1
        else:
            candidate_end = j

        candidate_end = _avoid_mid_tag(i, candidate_end)
        if candidate_end <= i:  # fallback to hard cut to avoid infinite loop
            candidate_end = j

        chunk = text[i:candidate_end].strip()
        if chunk:
            out.append(chunk)
        i = candidate_end

    return out


def _openai_tts(text: str) -> Optional[bytes]:
    """Fallback TTS using OpenAI gpt-4o-mini-tts via REST to produce WAV bytes.
    Note: voice cloning is not supported here; used for both first and later segments if Higgs fails.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set; cannot use fallback TTS")
        return None
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


def _synthesize_and_merge_turn_chunks(
    chunks: List[str],
    speaker: str,
    segment_index: int,
    audio_output_dir: Path,
    speaker_state: Dict[str, Dict[str, Any]],
    higgs_session: Optional[HiggsTTSSession] = None,
) -> Optional[Path]:
    """
    Given pre-chunked text for a single speaker turn, synthesize each chunk to audio,
    then concatenate into a single segment file. Manages per-speaker cloning seed.
    """
    try:
        if not chunks:
            return None

        # Ensure we have a session; prefer caller-provided (one per job)
        session = higgs_session or HiggsTTSSession()

        chunk_files: List[Path] = []
        for ci, chunk_text in enumerate(chunks):
            audio_bytes: Optional[bytes] = None

            if speaker not in speaker_state:
                audio_bytes = session.smart_voice(chunk_text)
                if audio_bytes:
                    speaker_state[speaker] = {"seed_audio": audio_bytes, "seed_text": chunk_text}
            else:
                seed = speaker_state[speaker]
                audio_bytes = session.voice_clone(
                    seed.get("seed_audio", b""), seed.get("seed_text", ""), chunk_text
                )
                if not audio_bytes:
                    audio_bytes = session.smart_voice(chunk_text)

            if not audio_bytes:
                audio_bytes = _openai_tts(chunk_text)

            if not audio_bytes:
                logger.warning(
                    f"Failed to generate audio for chunk {ci} of segment {segment_index} ({speaker})"
                )
                # Abort the whole segment on first failure to avoid broken audio
                for f in chunk_files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
                return None

            temp_chunk_name = f"segment_{segment_index:03d}_{speaker}_{ci:02d}.wav"
            temp_chunk_path = audio_output_dir / temp_chunk_name
            os.makedirs(os.path.dirname(temp_chunk_path), exist_ok=True)
            with open(temp_chunk_path, "wb") as f:
                f.write(audio_bytes)
            if temp_chunk_path.exists() and os.path.getsize(temp_chunk_path) > 0:
                chunk_files.append(temp_chunk_path)
            else:
                logger.warning(f"Invalid chunk file: {temp_chunk_path}")
                for f in chunk_files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
                return None

        # Concatenate chunk files into final segment file
        temp_filename = f"segment_{segment_index:03d}_{speaker}.wav"
        temp_file_path = audio_output_dir / temp_filename
        success = concatenate_audio_segments(chunk_files, temp_file_path, audio_output_dir)

        # Cleanup chunk files
        for f in chunk_files:
            try:
                f.unlink()
            except Exception:
                pass

        if success and temp_file_path.exists() and os.path.getsize(temp_file_path) > 0:
            return temp_file_path

        logger.warning(f"Generated segment but concatenation failed: {temp_file_path}")
        return None
    except Exception as e:
        logger.error(f"Error synthesizing/merging chunks for {speaker}: {e}")
        return None


def generate_audio_segment(
    content: str,
    speaker: str,
    segment_index: int,
    audio_output_dir: Path,
    speaker_state: Dict[str, Dict[str, Any]],
    higgs_session: Optional[HiggsTTSSession] = None,
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
        
        # Normalize content prior to TTS
        content = normalize_tts_text(content)

        # Split the single speaker's turn into chunks by length (uniformly)
        chunks: List[str] = _chunk_text_by_length(content, max_chars=250) or [content]

        return _synthesize_and_merge_turn_chunks(
            chunks=chunks,
            speaker=speaker,
            segment_index=segment_index,
            audio_output_dir=audio_output_dir,
            speaker_state=speaker_state,
            higgs_session=higgs_session,
        )
            
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
        # Initialize one Higgs client/model session for the whole job
        higgs_session = HiggsTTSSession()

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
                higgs_session=higgs_session,
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
            # Try ffmpeg concatenation with stream copy (fast, requires same codec/params)
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", str(concat_list_file),
                "-c", "copy", str(output_file)
            ], check=True, capture_output=True, timeout=300)

            concat_list_file.unlink()
            return True

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Retry with re-encode to a common PCM WAV to handle mismatched params
            try:
                subprocess.run([
                    "ffmpeg", "-f", "concat", "-safe", "0",
                    "-i", str(concat_list_file),
                    "-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1", str(output_file)
                ], check=True, capture_output=True, timeout=300)

                concat_list_file.unlink()
                return True
            except Exception:
                # Fallbacks
                if len(segments) == 1:
                    import shutil
                    shutil.copy2(segments[0], output_file)
                    return True
                else:
                    logger.warning("ffmpeg failed; using simple concatenation as last resort")
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
