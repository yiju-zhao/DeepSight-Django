"""
Image processing module for video frame extraction, deduplication, and captioning.

All modules are imported lazily to avoid loading heavy dependencies
(torch, transformers, CLIP) at startup time.

Usage:
    from notebooks.utils.image_processing.caption_generator import generate_captions_for_directory
    from notebooks.utils.image_processing.image_deduplicator import global_deep_dedupe
"""

# Modules are imported directly from their respective files, not here,
# to avoid loading torch/transformers at import time

__all__ = [
    # Available modules (import directly from submodules):
    # - caption_generator: generate_captions_for_directory
    # - frame_extractor: extract_frames
    # - image_deduplicator: various deduplication functions
]
