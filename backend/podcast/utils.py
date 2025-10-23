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
import requests
from django.conf import settings
try:
    import langid  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    langid = None  # type: ignore

try:
    import jieba  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    jieba = None  # type: ignore

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

def parse_conversation(conversation_text: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Parse conversation into structured turns using bracket format, and extract title.

    Expected format:
    #播客标题
    [speaker_name] content
    [speaker_name] content

    Args:
        conversation_text: Raw conversation text with bracket format and optional title

    Returns:
        Tuple of (title, conversation_turns)
        - title: Extracted title from #标题 line, or None if not found
        - conversation_turns: List of conversation turns with speaker and content
    """
    title = None
    conversation_turns = []

    # Extract title from first line if it starts with #
    lines = conversation_text.split('\n')
    if lines and lines[0].strip().startswith('#'):
        title = lines[0].strip()[1:].strip()  # Remove # and whitespace
        logger.info(f"Extracted podcast title: {title}")

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
    return title, conversation_turns


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


def normalize_tts_text(text: str) -> str:
    """Normalize transcript/content prior to TTS generation.

    Mirrors the example normalization: punctuation, special-event tags, whitespace cleanup,
    temperature units, and ensuring terminal punctuation.
    """
    if not text:
        return text

    # 1) Chinese punctuation to half-width
    text = _normalize_chinese_punctuation(text)

    # 2) Replace some symbols/units and parentheses
    replacements_simple = [
        ("(", " "),
        (")", " "),
        ("°F", " degrees Fahrenheit"),
        ("°C", " degrees Celsius"),
    ]
    for a, b in replacements_simple:
        text = text.replace(a, b)

    # 3) Convert common stage/event markers to tags the model can understand
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

    # 4) Collapse excessive whitespace and empty lines
    lines = [" ".join(line.split()) for line in text.split("\n") if line.strip()]
    text = "\n".join(lines).strip()

    # 5) Ensure terminal punctuation for smoother prosody
    if text and not any(text.endswith(c) for c in [".", "!", "?", ",", ";", '"', "'", "</SE_e>", "</SE>"]):
        text += "."

    return text


# =============================================================================
# TEXT CHUNKING FUNCTIONS
# =============================================================================

_CJK_RANGE = (
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x20000, 0x2A6DF),  # Extension B
    (0x2A700, 0x2B73F),  # Extension C
    (0x2B740, 0x2B81F),  # Extension D
    (0x2B820, 0x2CEAF),  # Extension E
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
)


def _has_cjk(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        for lo, hi in _CJK_RANGE:
            if lo <= code <= hi:
                return True
    return False


def _detect_language(text: str) -> str:
    if langid is not None:
        try:
            return langid.classify(text)[0]
        except Exception:
            pass
    # Heuristic fallback
    return "zh" if _has_cjk(text) else "en"


def _split_sentences_en(paragraph: str) -> List[str]:
    # Simple sentence splitter that keeps punctuation.
    # Splits on . ! ? ; : while preserving delimiter with the sentence.
    parts: List[str] = []
    buf: List[str] = []
    for token in re.split(r"(\s+)", paragraph):
        buf.append(token)
        if re.search(r"[\.!?;:][\)\"]?$", token.strip()):
            parts.append("".join(buf).strip())
            buf = []
    if buf:
        parts.append("".join(buf).strip())
    return [s for s in parts if s]


def prepare_chunk_text(
    text: str,
    chunk_method: Optional[str] = None,
    chunk_max_word_num: int = 100,
    chunk_max_num_turns: int = 1,
) -> List[str]:
    """Chunk text into smaller pieces for TTS generation.

    chunk_method:
      - None: no chunking
      - "speaker": merge lines by speaker tags like [SPEAKER0]
      - "word": paragraph-first, then sentence/word granularity with language awareness
    """
    if not text:
        return [text]

    if chunk_method is None:
        return [text]

    if chunk_method == "speaker":
        lines = text.split("\n")
        speaker_chunks: List[str] = []
        speaker_utterance = ""
        for line in lines:
            line = line.strip()
            if line.startswith("[SPEAKER") or line.startswith("<|speaker_id_start|>"):
                if speaker_utterance:
                    speaker_chunks.append(speaker_utterance.strip())
                speaker_utterance = line
            else:
                if speaker_utterance:
                    speaker_utterance += "\n" + line
                else:
                    speaker_utterance = line
        if speaker_utterance:
            speaker_chunks.append(speaker_utterance.strip())
        if chunk_max_num_turns > 1:
            merged_chunks: List[str] = []
            for i in range(0, len(speaker_chunks), chunk_max_num_turns):
                merged_chunk = "\n".join(speaker_chunks[i : i + chunk_max_num_turns])
                merged_chunks.append(merged_chunk)
            return merged_chunks
        return speaker_chunks

    if chunk_method == "word":
        language = _detect_language(text)
        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        for paragraph in paragraphs:
            para = paragraph.strip()
            if not para:
                continue
            lang = _detect_language(para) or language
            if lang == "zh":
                if jieba is not None:
                    tokens = list(jieba.cut(para, cut_all=False))
                else:
                    tokens = list(para)  # fallback: character-level
                for i in range(0, len(tokens), chunk_max_word_num):
                    chunk = "".join(tokens[i : i + chunk_max_word_num])
                    if chunk:
                        chunks.append(chunk + "\n\n")
            else:
                # sentence-aware accumulation up to word limit
                sentences = _split_sentences_en(para)
                buf: List[str] = []
                count = 0
                for sent in sentences:
                    words = sent.split()
                    if count + len(words) > chunk_max_word_num and buf:
                        chunks.append(" ".join(buf) + "\n\n")
                        buf = []
                        count = 0
                    buf.append(sent)
                    count += len(words)
                if buf:
                    chunks.append(" ".join(buf) + "\n\n")
        return chunks if chunks else [text]

    raise ValueError(f"Unknown chunk method: {chunk_method}")

def _get_higgs_client_and_model():
    """Create an OpenAI-compatible client for Higgs and choose a model.
    Returns a tuple (client, model_id).
    """
    try:
        from openai import OpenAI
    except Exception as e:
        logger.error(f"OpenAI client not available for Higgs: {e}")
        return None, None

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
        return client, model
    except Exception as e:
        logger.error(f"Failed to init Higgs client: {e}")
        return None, None


def _higgs_smart_voice(text: str) -> Optional[bytes]:
    """Generate WAV audio bytes using Higgs 'smart voice' (no reference)."""
    client, model = _get_higgs_client_and_model()
    if not client or not model:
        return None
    DEFAULT_SYSTEM_PROMPT = (
        "Generate audio following instruction.\n\n"
        "<|scene_desc_start|>\n"
        "Audio is recorded from a quiet room.\n"
        "Speaker will speak chinese mixed with a few english words.\n"
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
        
        # Normalize content prior to TTS
        content = normalize_tts_text(content)

        # Decide whether to chunk: only chunk if content is relatively long
        words_count = len(content.split())
        do_chunk = words_count > 100 or len(content) > 400
        chunks: List[str] = (
            prepare_chunk_text(content, chunk_method="word", chunk_max_word_num=100)
            if do_chunk
            else [content]
        )

        # For each chunk, generate a small WAV and then concatenate
        chunk_files: List[Path] = []
        for ci, chunk_text in enumerate(chunks):
            audio_bytes: Optional[bytes] = None

            if speaker not in speaker_state:
                audio_bytes = _higgs_smart_voice(chunk_text)
                if audio_bytes:
                    speaker_state[speaker] = {"seed_audio": audio_bytes, "seed_text": chunk_text}
            else:
                seed = speaker_state[speaker]
                audio_bytes = _higgs_voice_clone(
                    seed.get("seed_audio", b""), seed.get("seed_text", ""), chunk_text
                )
                if not audio_bytes:
                    audio_bytes = _higgs_smart_voice(chunk_text)

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


    # Minimax TTS removed
    pass
