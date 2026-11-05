"""
### Unit tests for src/config/confluent_config.py
Tests config file parsing: key=value pairs, comment skipping, blank line skipping,
value-with-equals handling, and FileNotFoundError propagation.
"""

import pytest

from config.confluent_config import read_config


class TestReadConfig:
    ### Successful parsing

    def test_parses_key_value_pairs(self, tmp_path):
        config_file = tmp_path / "client.properties"
        config_file.write_text("bootstrap.servers=localhost:9092\nsasl.username=user\n")

        result = read_config(str(config_file))

        assert result["bootstrap.servers"] == "localhost:9092"
        assert result["sasl.username"] == "user"

    def test_skips_comment_lines(self, tmp_path):
        config_file = tmp_path / "client.properties"
        config_file.write_text("# This is a comment\nkey=value\n")

        result = read_config(str(config_file))

        assert "# This is a comment" not in result
        assert result["key"] == "value"

    def test_skips_blank_lines(self, tmp_path):
        config_file = tmp_path / "client.properties"
        config_file.write_text("\n\nkey=value\n\n")

        result = read_config(str(config_file))

        assert result == {"key": "value"}

    def test_strips_whitespace_around_values(self, tmp_path):
        config_file = tmp_path / "client.properties"
        config_file.write_text("key=  value with spaces  \n")

        result = read_config(str(config_file))

        assert result["key"] == "value with spaces"

    def test_value_containing_equals_sign(self, tmp_path):
        """Values that contain '=' should not be split on the second '='."""
        config_file = tmp_path / "client.properties"
        config_file.write_text(
            'sasl.jaas.config=org.apache.kafka.Mechanism required username="user" password="p=ass";\n'
        )

        result = read_config(str(config_file))

        assert "sasl.jaas.config" in result
        assert "p=ass" in result["sasl.jaas.config"]

    def test_returns_empty_dict_for_empty_file(self, tmp_path):
        config_file = tmp_path / "client.properties"
        config_file.write_text("")

        result = read_config(str(config_file))

        assert result == {}

    def test_all_properties_parsed(self, tmp_path):
        config_file = tmp_path / "client.properties"
        content = (
            "# Confluent config\n"
            "security.protocol=SASL_SSL\n"
            "sasl.mechanisms=PLAIN\n"
            "\n"
            "socket.keepalive.enable=True\n"
        )
        config_file.write_text(content)

        result = read_config(str(config_file))

        assert len(result) == 3
        assert result["security.protocol"] == "SASL_SSL"
        assert result["sasl.mechanisms"] == "PLAIN"
        assert result["socket.keepalive.enable"] == "True"

    ### Error handling

    def test_raises_file_not_found_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            read_config("/nonexistent/path/client.properties")

    def test_does_not_swallow_file_not_found(self):
        """Ensure the exception propagates rather than returning empty dict."""
        try:
            read_config("/no/such/file.properties")
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass
