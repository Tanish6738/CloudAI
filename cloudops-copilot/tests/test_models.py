"""Property-based tests for LogRecord normalization.

Property 1: LogRecord Normalization Produces Valid Sentinels
Validates: Requirements 3.4, 3.5, 3.7
"""

from datetime import datetime
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from core.models import LogRecord
from plugins.base import LogPlugin


class TestLogRecordNormalization:
    """Test LogRecord sentinel normalization."""

    @given(
        id_=st.text(),
        timestamp=st.one_of(st.none(), st.datetimes()),
        source=st.one_of(st.none(), st.text()),
        service=st.one_of(st.none(), st.text()),
        level=st.one_of(st.none(), st.text()),
        message=st.one_of(st.none(), st.text()),
        attributes=st.one_of(st.none(), st.dictionaries(st.text(), st.text())),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_record_normalization_produces_valid_sentinels(
        self, id_, timestamp, source, service, level, message, attributes
    ):
        """Test that LogRecord normalizes missing/None fields to correct sentinels."""
        # Create record with potentially None values
        record = LogRecord(
            id=id_ or "",
            timestamp=timestamp,
            source=source,
            service=service,
            level=level,
            message=message,
            attributes=attributes,
        )

        # Verify normalization
        assert isinstance(record.attributes, dict), "attributes must be a dict"
        assert record.timestamp is None or isinstance(
            record.timestamp, datetime
        ), "timestamp must be datetime or None"
        assert isinstance(record.source, str), "source must be str"
        assert isinstance(record.service, str), "service must be str"
        assert isinstance(record.level, str), "level must be str"
        assert isinstance(record.message, str), "message must be str"


class TestPluginNameEnforcement:
    """Test LogPlugin name attribute enforcement."""

    def test_plugin_missing_name_raises_typeerror(self):
        """Subclass without 'name' attribute should raise TypeError."""

        with __import__("pytest").raises(TypeError, match="non-empty 'name'"):

            class BadPlugin(LogPlugin):
                def fetch(self, since, until):
                    yield

    def test_plugin_empty_name_raises_typeerror(self):
        """Subclass with empty 'name' should raise TypeError."""

        with __import__("pytest").raises(TypeError, match="non-empty 'name'"):

            class BadPlugin(LogPlugin):
                name = ""

                def fetch(self, since, until):
                    yield

    def test_plugin_valid_name_succeeds(self):
        """Subclass with non-empty 'name' should succeed."""

        class GoodPlugin(LogPlugin):
            name = "test-plugin"

            def fetch(self, since, until):
                yield

        assert GoodPlugin.name == "test-plugin"
