# SPDX-License-Identifier: AGPL-3.0-only
"""
Video Keyframe Processor — scene change detection + per-frame OCR.

Uses OpenCV for scene detection and Tesseract for OCR on extracted frames.
Falls back gracefully when dependencies are unavailable.
"""

from __future__ import annotations

import io
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger("crimescope.pipeline.keyframes")


async def extract_keyframes(
    video_bytes: bytes,
    video_index: int = 0,
    max_frames: int = 20,
    scene_threshold: float = 30.0,
    ext: str = ".mp4",
) -> Dict[str, Any]:
    """
    Extract keyframes from a video using scene change detection.

    Args:
        video_bytes: Raw video file bytes.
        video_index: Index for tracking in multi-video uploads.
        max_frames: Maximum number of keyframes to extract.
        scene_threshold: Histogram difference threshold for scene changes.
        ext: Video file extension.

    Returns:
        Dict with frames, OCR texts, and metadata.
    """
    start = time.time()
    result: Dict[str, Any] = {
        "video_index": video_index,
        "frames": [],
        "ocr_texts": [],
        "frame_count": 0,
        "method": "scene_change",
        "processing_time_ms": 0,
    }

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("OpenCV not available — falling back to interval-based extraction")
        return await _fallback_extraction(video_bytes, video_index, max_frames, ext, start)

    # Write video to temp file for OpenCV
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    try:
        tmp.write(video_bytes)
        tmp.flush()
        tmp_path = tmp.name
        tmp.close()

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            logger.warning(f"Failed to open video {video_index}")
            return result

        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = total_frames / fps if fps > 0 else 0

        result["fps"] = fps
        result["total_frames"] = total_frames
        result["duration_seconds"] = round(duration, 2)

        prev_hist = None
        frames_extracted = 0
        frame_idx = 0

        while cap.isOpened() and frames_extracted < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale and compute histogram
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            is_scene_change = False
            if prev_hist is None:
                is_scene_change = True  # First frame
            else:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
                if diff > scene_threshold:
                    is_scene_change = True

            if is_scene_change:
                timestamp = frame_idx / fps if fps > 0 else 0

                # Encode frame as JPEG bytes
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buf.tobytes()

                # OCR the frame
                ocr_text = _ocr_frame(frame)

                frame_data = {
                    "frame_index": frame_idx,
                    "timestamp_seconds": round(timestamp, 2),
                    "size_bytes": len(frame_bytes),
                    "ocr_text": ocr_text,
                }
                result["frames"].append(frame_data)
                if ocr_text.strip():
                    result["ocr_texts"].append(ocr_text)

                frames_extracted += 1

            prev_hist = hist
            frame_idx += 1

        cap.release()
        result["frame_count"] = frames_extracted

    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    result["processing_time_ms"] = (time.time() - start) * 1000
    logger.info(
        f"Keyframes: video {video_index} → {result['frame_count']} frames "
        f"({result['processing_time_ms']:.0f}ms), "
        f"{len(result['ocr_texts'])} OCR texts"
    )
    return result


def _ocr_frame(frame) -> str:
    """Run OCR on a single frame using Tesseract."""
    try:
        import pytesseract
        import cv2

        # Pre-process for better OCR
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        text = pytesseract.image_to_string(thresh, config="--psm 6")
        # Filter out noise (very short or garbage text)
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3]
        return "\n".join(lines)
    except ImportError:
        return ""
    except Exception as e:
        logger.debug(f"OCR failed: {e}")
        return ""


async def _fallback_extraction(
    video_bytes: bytes,
    video_index: int,
    max_frames: int,
    ext: str,
    start: float,
) -> Dict[str, Any]:
    """Fallback: extract frames at regular intervals when OpenCV is unavailable."""
    result: Dict[str, Any] = {
        "video_index": video_index,
        "frames": [],
        "ocr_texts": [],
        "frame_count": 0,
        "method": "interval_fallback",
        "processing_time_ms": (time.time() - start) * 1000,
    }

    try:
        import cv2
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(video_bytes)
        tmp.flush()
        tmp_path = tmp.name
        tmp.close()

        cap = cv2.VideoCapture(tmp_path)
        if cap.isOpened():
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            interval = max(total // max_frames, 1)

            for i in range(0, total, interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    timestamp = i / fps if fps > 0 else 0
                    ocr_text = _ocr_frame(frame)
                    result["frames"].append({
                        "frame_index": i,
                        "timestamp_seconds": round(timestamp, 2),
                        "ocr_text": ocr_text,
                    })
                    if ocr_text.strip():
                        result["ocr_texts"].append(ocr_text)
                if len(result["frames"]) >= max_frames:
                    break
            cap.release()
            result["frame_count"] = len(result["frames"])

        Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Fallback extraction failed: {e}")

    result["processing_time_ms"] = (time.time() - start) * 1000
    return result
