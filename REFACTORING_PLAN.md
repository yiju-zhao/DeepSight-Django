# Refactoring Plan: Image Captioning with Qwen2.5-VL and Xinference (Revised)

**1. Introduction**

This plan outlines the steps to refactor the image captioning pipeline to use the Qwen2.5-VL model served by Xinference. This will replace the current implementation that relies on the OpenAI Vision API.

**2. Motivation**

*   **Unify AI model serving:** Use Xinference for both embedding and vision models, simplifying the architecture and reducing dependencies.
*   **Cost-effective:** Potentially reduce costs by using a self-hosted open-source model instead of a paid API.
*   **Flexibility:** Easily swap out different vision models supported by Xinference in the future.

**3. Current Implementation**

The current image captioning pipeline is triggered after a PDF file is parsed by the MinerU service.

*   **PDF Parsing:** `notebooks/processors/file_type_processors.py` calls the MinerU API to extract text and images from PDFs.
*   **File Storage:** `notebooks/processors/minio_post_processor.py` stores the extracted files (Markdown, images) in MinIO.
*   **Captioning Task:** After storing the files, `minio_post_processor.py` schedules a Celery task `generate_image_captions_task` defined in `notebooks/tasks.py`.
*   **Caption Service:** The Celery task uses `notebooks/processors/caption_service.py` to orchestrate the captioning process.
*   **Caption Generation:** `caption_service.py` calls `generate_caption_for_image` in `notebooks/utils/image_processing/caption_generator.py`, which in turn calls the OpenAI Vision API.

**4. Proposed Refactoring**

The refactoring will be done in two phases:

**Phase 1: Replace the existing Caption Generator**

1.  **Update `caption_generator.py`:**
    *   Modify `notebooks/utils/image_processing/caption_generator.py`.
    *   Instead of a simple function, create a `CaptionGenerator` class.
    *   This class will be responsible for:
        *   Connecting to the Xinference server.
        *   Getting the Qwen2.5-VL model.
        *   Providing a `generate_caption` method that takes an image path and a prompt, and returns a caption.
    *   This class will be modeled after the existing `TranscriptionService` in `notebooks/processors/transcription_service.py`.
    *   The existing `generate_caption_for_image` function will be replaced by the `generate_caption` method of the `CaptionGenerator` class.
    *   The `generate_captions_for_directory` will be updated to use the new `CaptionGenerator` class.

2.  **Update Caption Service:**
    *   Review `notebooks/processors/caption_service.py`.
    *   Update the `_generate_ai_caption_for_upload` method to instantiate the new `CaptionGenerator` class and call its `generate_caption` method.
    *   Remove the `api_key` parameter from the function call.

3.  **Configuration:**
    *   Add a new environment variable `XINFERENCE_VL_MODEL_UID` to `.env.example` and `env.template` for the Qwen2.5-VL model UID.
    *   Update `backend/settings/base.py` to read this new environment variable.

**Phase 2: Remove Legacy Code**

1.  **Remove OpenAI Code:**
    *   Delete the OpenAI API call and related logic from `notebooks/utils/image_processing/caption_generator.py`.
2.  **Remove Unused Configuration:**
    *   Remove any configuration variables related to the OpenAI API key from the codebase.
3.  **Clean up `caption_service.py`:**
    *   Remove any code from `notebooks/processors/caption_service.py` that is specific to the old OpenAI implementation.

**5. Testing**

*   After the refactoring, it's crucial to test the new image captioning pipeline thoroughly.
*   This includes:
    *   Uploading a PDF with images.
    *   Verifying that the `generate_image_captions_task` is triggered and completes successfully.
    *   Checking the generated captions in the database and the application.
    *   The existing `test_caption_generation_task` in `notebooks/tasks.py` can be used for this purpose.