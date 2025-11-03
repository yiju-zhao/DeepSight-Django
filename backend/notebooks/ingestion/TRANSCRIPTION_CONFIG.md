# Transcription Configuration Guide

This guide documents the transcription configuration for audio/video ingestion in DeepSight.

## Overview

DeepSight supports multiple transcription providers for processing audio and video files:
- **WhisperX** (default): High-quality transcription with word-level alignment
- **Xinference**: Alternative provider for distributed inference

## Provider Selection

Configure the transcription provider using the `TRANSCRIPTION_PROVIDER` environment variable:

```bash
# WhisperX (default, recommended)
TRANSCRIPTION_PROVIDER=whisperx

# Xinference (alternative)
TRANSCRIPTION_PROVIDER=xinference

# Auto (tries WhisperX first, falls back to Xinference)
TRANSCRIPTION_PROVIDER=auto
```

## WhisperX Configuration

WhisperX provides state-of-the-art transcription with word-level timestamps and alignment.

### Environment Variables

```bash
# Provider selection
TRANSCRIPTION_PROVIDER=whisperx

# Model configuration
WHISPERX_MODEL_NAME=large-v3           # Options: tiny, base, small, medium, large-v2, large-v3
WHISPERX_DEVICE=auto                    # Options: auto, cuda, cpu, mps
WHISPERX_COMPUTE_TYPE=                  # Optional: float16 (CUDA), int8 (CPU), float32 (MPS)
WHISPERX_BATCH_SIZE=16                  # Batch size for transcription (higher = faster but more memory)

# Language configuration
WHISPERX_LANGUAGE=                      # Optional: Language code (e.g., 'en', 'zh', 'es')
                                        # If not set, language will be auto-detected

# Advanced options
WHISPERX_VAD=0                          # Voice Activity Detection: 0=off, 1=on (experimental)
WHISPERX_CACHE_DIR=                     # Optional: Custom HuggingFace cache directory

# Diarization (future feature - requires HF token)
# HF_TOKEN=                             # HuggingFace token for speaker diarization models
```

### Dependencies

WhisperX requires the following dependencies:

1. **Python packages** (already in requirements.txt):
   ```bash
   pip install whisperx
   ```

2. **FFmpeg** (system requirement):
   ```bash
   # macOS
   brew install ffmpeg

   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

3. **PyTorch** (with appropriate backend):
   ```bash
   # CPU only
   pip install torch torchvision torchaudio

   # CUDA 11.8 (NVIDIA GPU)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

   # CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### Model Selection Guide

| Model | Speed | Accuracy | VRAM (GPU) | RAM (CPU) | Use Case |
|-------|-------|----------|------------|-----------|----------|
| tiny | Fastest | Basic | ~1 GB | ~1 GB | Quick drafts, testing |
| base | Very Fast | Good | ~1 GB | ~1 GB | Low-resource environments |
| small | Fast | Better | ~2 GB | ~2 GB | Balanced performance |
| medium | Moderate | Great | ~5 GB | ~5 GB | High accuracy needed |
| large-v2 | Slow | Excellent | ~10 GB | ~10 GB | Production quality |
| large-v3 | Slow | Best | ~10 GB | ~10 GB | Maximum accuracy (recommended) |

### Device Selection

WhisperX will auto-select the best available device when `WHISPERX_DEVICE=auto`:

1. **CUDA (NVIDIA GPU)** - Fastest, requires NVIDIA GPU with CUDA support
   - Automatically uses `float16` compute type for speed and memory efficiency
   - Recommended for production workloads

2. **MPS (Apple Silicon)** - Fast on M1/M2/M3 Macs
   - Automatically uses `float32` compute type
   - Good for macOS development

3. **CPU** - Slowest but works everywhere
   - Automatically uses `int8` compute type for reduced memory usage
   - Suitable for light workloads or when GPU is unavailable

### First-Run Model Caching

On first use, WhisperX will download models from HuggingFace:

1. **Whisper model** (~3 GB for large-v3)
2. **Alignment models** (language-specific, ~100-500 MB each)

Models are cached at:
- Linux/macOS: `~/.cache/huggingface/`
- Windows: `C:\Users\<user>\.cache\huggingface\`
- Custom: Set `WHISPERX_CACHE_DIR` to override

**Note**: First transcription may take 5-10 minutes for model downloads. Subsequent runs will use cached models.

### Language Configuration

WhisperX supports 99+ languages. Common language codes:

```bash
WHISPERX_LANGUAGE=en    # English
WHISPERX_LANGUAGE=zh    # Chinese
WHISPERX_LANGUAGE=es    # Spanish
WHISPERX_LANGUAGE=fr    # French
WHISPERX_LANGUAGE=de    # German
WHISPERX_LANGUAGE=ja    # Japanese
WHISPERX_LANGUAGE=ko    # Korean
```

If `WHISPERX_LANGUAGE` is not set, the language will be auto-detected from the audio.

### Performance Tuning

For optimal performance:

1. **GPU Memory**: Increase `WHISPERX_BATCH_SIZE` if you have more VRAM
   - 8 GB VRAM: batch_size=8-16
   - 16 GB VRAM: batch_size=16-32
   - 24 GB+ VRAM: batch_size=32+

2. **CPU**: Use smaller models (tiny/base/small) or increase batch size modestly
   - Recommended: batch_size=4-8 for CPU

3. **Language Hints**: Set `WHISPERX_LANGUAGE` if you know the language to skip detection

### Troubleshooting

**ImportError: No module named 'whisperx'**
```bash
pip install whisperx
```

**CUDA out of memory**
- Reduce `WHISPERX_BATCH_SIZE` to 8 or 4
- Use a smaller model (e.g., medium instead of large-v3)
- Set `WHISPERX_COMPUTE_TYPE=int8` for lower memory usage

**FFmpeg not found**
```bash
# Install ffmpeg (see Dependencies section)
```

**Slow transcription on CPU**
- Use smaller models (tiny, base, or small)
- Consider using a GPU or cloud GPU instance
- Reduce batch size to avoid memory swapping

**Model download fails**
- Check internet connection
- Verify HuggingFace is accessible
- Set custom cache directory with `WHISPERX_CACHE_DIR`
- Check disk space (models can be 3+ GB)

## Xinference Configuration (Fallback)

Xinference is an alternative provider for distributed inference environments.

### Environment Variables

```bash
TRANSCRIPTION_PROVIDER=xinference
XINFERENCE_URL=http://localhost:9997
XINFERENCE_WHISPER_MODEL_UID=Bella-whisper-large-v3-zh
```

### Requirements

1. Xinference server running at configured URL
2. Whisper model deployed on Xinference
3. `xinference` Python client installed

## Integration Points

### IngestionOrchestrator

The transcription provider is configured in `notebooks/ingestion/orchestrator.py`:

```python
orchestrator = IngestionOrchestrator(
    transcription_provider="whisperx",
    whisperx_model_name="large-v3",
    whisperx_device="auto",
    # ... other config
)
```

### UploadProcessor

Upload processor reads configuration from environment variables in `notebooks/processors/upload_processor.py` and passes them to the orchestrator.

### MediaParser

MediaParser receives the transcription client from the orchestrator and uses it to transcribe audio/video files.

## Production Recommendations

For production deployments:

1. **Use GPU instances** for faster transcription (10-100x speedup)
2. **Set explicit language** with `WHISPERX_LANGUAGE` to skip detection
3. **Use large-v3 model** for best accuracy
4. **Monitor disk space** for model cache directory
5. **Consider batch processing** for large volumes (Celery tasks)
6. **Set TRANSCRIPTION_PROVIDER=auto** for automatic fallback

## Future Enhancements

Planned features for WhisperX integration:

- **Speaker diarization**: Identify different speakers in audio (requires `HF_TOKEN`)
- **Custom vocabulary**: Domain-specific terms and jargon
- **Streaming transcription**: Real-time processing for long files
- **Multi-lingual support**: Automatic language switching within files

## References

- [WhisperX GitHub](https://github.com/m-bain/whisperX)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [HuggingFace Model Hub](https://huggingface.co/models)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
