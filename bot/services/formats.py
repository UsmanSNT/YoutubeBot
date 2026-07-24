"""Format handling module for VideoGrabberBot."""

from functools import lru_cache
from typing import Dict, List, Optional, Tuple, TypedDict

from bot.config import AUDIO_FORMAT, VIDEO_FORMATS


class FormatData(TypedDict):
    """Type definition for format data."""

    label: str
    format: str
    type: str


@lru_cache(maxsize=1)
def get_available_formats() -> Dict[str, FormatData]:
    """
    Get available formats for download.

    Returns:
        Dict of format types and their details.
    """
    # Use dictionary comprehension for better performance
    video_formats: Dict[str, FormatData] = {
        f"video:{format_id}": {
            "label": format_data["label"],
            "format": format_data["format"],
            "type": "video",
        }
        for format_id, format_data in VIDEO_FORMATS.items()
    }

    audio_formats: Dict[str, FormatData] = {
        f"audio:{format_id}": {
            "label": format_data["label"],
            "format": format_data["format"],
            "type": "audio",
        }
        for format_id, format_data in AUDIO_FORMAT.items()
    }

    result: Dict[str, FormatData] = {}
    result.update(video_formats)
    result.update(audio_formats)
    return result


@lru_cache(maxsize=1)
def get_format_options() -> List[Tuple[str, str]]:
    """
    Get format options for InlineKeyboard.

    Returns:
        List of (callback_data, label) tuples for InlineKeyboard buttons.
    """
    formats = get_available_formats()
    video_options = []
    audio_options = []

    # Group formats by type in a single pass
    for format_id, format_data in formats.items():
        if format_data["type"] == "video":
            video_options.append((format_id, format_data["label"]))
        elif format_data["type"] == "audio":
            audio_options.append((format_id, format_data["label"]))

    # Return combined list with videos first, then audio options
    return video_options + audio_options


def get_format_by_id(format_id: str) -> Optional[FormatData]:
    """
    Get format details by format ID.

    Args:
        format_id: Format ID in the format 'type:format' (e.g., 'video:HD')

    Returns:
        Format details dict or None if not found
    """
    return get_available_formats().get(format_id)
