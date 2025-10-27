"""
Image processing module for video frame extraction, deduplication, and captioning.
"""

from .caption_generator import generate_captions_for_directory
from .frame_extractor import extract_frames
from .image_deduplicator import (
    get_optimal_device,
    global_deep_dedupe,
    global_pixel_dedupe,
    load_clip_model_and_preprocessing,
    prepare_work_dir,
    sequential_deep_dedupe,
    setup_cuda_environment,
    text_ocr_filter_dedupe,
)

__all__ = [
    "extract_frames",
    "prepare_work_dir",
    "text_ocr_filter_dedupe",
    "global_pixel_dedupe",
    "sequential_deep_dedupe",
    "global_deep_dedupe",
    "load_clip_model_and_preprocessing",
    "setup_cuda_environment",
    "get_optimal_device",
    "generate_captions_for_directory",
]
