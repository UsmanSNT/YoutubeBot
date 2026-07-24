"""Tests for formats module."""

import importlib

import pytest

from bot.services.formats import (
    get_available_formats,
    get_format_by_id,
    get_format_options,
)


@pytest.fixture
def reload_formats_module():
    """Reload formats module to pick up config changes."""
    import sys

    formats_module = sys.modules.get("bot.services.formats")
    if formats_module:
        importlib.reload(formats_module)


class TestFormats:
    """Group tests for the formats module."""

    def test_get_available_formats(
        self,
        mock_video_formats,
        mock_audio_formats,
        clear_format_cache,
        reload_formats_module,
    ):
        """Test getting available formats with mocked configuration."""
        # Now get formats
        formats = get_available_formats()

        # Check that we have both video and audio formats
        expected_count = len(mock_video_formats) + len(mock_audio_formats)
        assert len(formats) == expected_count

        # Check that keys are properly prefixed
        for key in formats.keys():
            assert key.startswith("video:") or key.startswith("audio:")

        # Check structure of format data
        for format_data in formats.values():
            assert "label" in format_data
            assert "format" in format_data
            assert "type" in format_data
            assert format_data["type"] in ["video", "audio"]

        # Check specific formats exist with correct data
        for format_id, format_data in mock_video_formats.items():
            key = f"video:{format_id}"
            assert key in formats
            assert formats[key]["label"] == format_data["label"]
            assert formats[key]["format"] == format_data["format"]
            assert formats[key]["type"] == "video"

        for format_id, format_data in mock_audio_formats.items():
            key = f"audio:{format_id}"
            assert key in formats
            assert formats[key]["label"] == format_data["label"]
            assert formats[key]["format"] == format_data["format"]
            assert formats[key]["type"] == "audio"

    def test_get_format_options(
        self,
        mock_video_formats,
        mock_audio_formats,
        clear_format_cache,
        reload_formats_module,
    ):
        """Test getting format options for inline keyboard."""
        options = get_format_options()

        # Check that options are not empty
        assert len(options) > 0
        assert len(options) == len(mock_video_formats) + len(mock_audio_formats)

        # Check that each option is a tuple of (callback_data, label)
        for option in options:
            assert len(option) == 2
            assert isinstance(option[0], str)
            assert isinstance(option[1], str)

        # Extract ids and labels
        ids = [opt[0] for opt in options]
        labels = [opt[1] for opt in options]

        # Check that all mocked formats are represented
        for format_id in mock_video_formats.keys():
            assert f"video:{format_id}" in ids

        for format_id in mock_audio_formats.keys():
            assert f"audio:{format_id}" in ids

        # Check that labels match the mocked values
        for format_data in mock_video_formats.values():
            assert format_data["label"] in labels

        for format_data in mock_audio_formats.values():
            assert format_data["label"] in labels

        # Check that video formats come before audio formats
        video_formats = [opt for opt in options if opt[0].startswith("video:")]
        audio_options = [opt for opt in options if opt[0].startswith("audio:")]

        assert len(video_formats) > 0
        assert len(audio_options) > 0

        # Get indices of first video and first audio format
        first_video_idx = options.index(video_formats[0])
        first_audio_idx = options.index(audio_options[0])

        assert first_video_idx < first_audio_idx

    def test_get_format_by_id(
        self,
        mock_video_formats,
        mock_audio_formats,
        clear_format_cache,
        reload_formats_module,
    ):
        """Test getting format by ID."""
        # Test with valid video format ID
        first_video_key = list(mock_video_formats.keys())[0]
        video_format_id = f"video:{first_video_key}"
        format_data = get_format_by_id(video_format_id)
        assert format_data is not None
        assert format_data["type"] == "video"
        original_data = mock_video_formats[video_format_id.split(":")[1]]
        assert format_data["label"] == original_data["label"]
        assert format_data["format"] == original_data["format"]

        # Test with valid audio format ID
        first_audio_key = list(mock_audio_formats.keys())[0]
        audio_format_id = f"audio:{first_audio_key}"
        format_data = get_format_by_id(audio_format_id)
        assert format_data is not None
        assert format_data["type"] == "audio"
        original_data = mock_audio_formats[audio_format_id.split(":")[1]]
        assert format_data["label"] == original_data["label"]
        assert format_data["format"] == original_data["format"]

        # Test with invalid format ID
        format_data = get_format_by_id("invalid:format")
        assert format_data is None

    def test_get_format_by_id_edge_cases(
        self,
        mock_video_formats,
        mock_audio_formats,
        clear_format_cache,
        reload_formats_module,
    ):
        """Test edge cases for get_format_by_id."""
        # Test with empty string
        format_data = get_format_by_id("")
        assert format_data is None

        # Test with None-like values
        format_data = get_format_by_id("no_colon_here")
        assert format_data is None

    def test_format_data_type_safety(self, reload_formats_module):
        """Test that FormatData TypedDict enforces type safety."""
        # This test ensures that FormatData TypedDict is used correctly
        formats = get_available_formats()

        # All returned formats should conform to FormatData structure
        for _, format_data in formats.items():
            # Explicitly verify each required field with correct types
            assert isinstance(format_data["label"], str)
            assert isinstance(format_data["format"], str)
            assert isinstance(format_data["type"], str)
            assert format_data["type"] in ["video", "audio"]

    def test_empty_formats(self, clear_format_cache, reset_modules):
        """Test behavior with empty format configurations."""
        import sys

        # Temporarily patch config with empty formats
        from bot import config

        # Store original values
        original_video_formats = config.VIDEO_FORMATS
        original_audio_format = config.AUDIO_FORMAT

        # Set empty formats
        config.VIDEO_FORMATS = {}
        config.AUDIO_FORMAT = {}

        # Reload formats module to apply empty configs
        reset_modules("bot.services.formats")
        formats_module = sys.modules.get("bot.services.formats")
        if formats_module:
            importlib.reload(formats_module)

            # Make sure to clear any caches
            if hasattr(formats_module.get_available_formats, "cache_clear"):
                formats_module.get_available_formats.cache_clear()
            if hasattr(formats_module.get_format_options, "cache_clear"):
                formats_module.get_format_options.cache_clear()

            # Check behavior with empty formats
            formats = formats_module.get_available_formats()
            assert len(formats) == 0

            options = formats_module.get_format_options()
            assert len(options) == 0

        # Restore original values
        config.VIDEO_FORMATS = original_video_formats
        config.AUDIO_FORMAT = original_audio_format

        # Reload module to restore original state for other tests
        formats_module = sys.modules.get("bot.services.formats")
        if formats_module:
            importlib.reload(formats_module)

            # Clear caches again to ensure fresh state
            if hasattr(formats_module.get_available_formats, "cache_clear"):
                formats_module.get_available_formats.cache_clear()
            if hasattr(formats_module.get_format_options, "cache_clear"):
                formats_module.get_format_options.cache_clear()

    def test_format_id_construction(
        self,
        mock_video_formats,
        mock_audio_formats,
        clear_format_cache,
        reload_formats_module,
    ):
        """Test that format IDs are correctly constructed."""
        formats = get_available_formats()

        # Check that all format IDs follow the expected pattern
        for format_id in formats.keys():
            parts = format_id.split(":")
            assert len(parts) == 2
            assert parts[0] in ["video", "audio"]

            # The format key should exist in the original config
            if parts[0] == "video":
                assert parts[1] in mock_video_formats
            elif parts[0] == "audio":
                assert parts[1] in mock_audio_formats
