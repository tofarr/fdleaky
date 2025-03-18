import time
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from fdleaky.fd import Fd
from fdleaky.fd_info import FdInfo
from fdleaky.fd_info_factory import FdInfoFactory


class TestFdInfoFactory:
    """Unit tests for the FdInfoFactory class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.factory = FdInfoFactory(
            min_age=60, identifier_include_any_of=["test", "example"]
        )

        # Create a test Fd object
        self.current_time = time.time()
        self.old_time = self.current_time - 120  # 2 minutes ago (older than min_age)
        self.recent_time = self.current_time - 30  # 30 seconds ago (newer than min_age)

        self.test_stack = [
            'File "/usr/lib/python3.9/socket.py", line 232, in accept',
            'File "/usr/lib/python3.9/test_module.py", line 45, in test_function',
            'File "/usr/lib/python3.9/example_module.py", line 78, in example_function',
        ]

        self.old_fd = Fd(
            subject="test_subject", stack=self.test_stack, created_at=self.old_time
        )

        self.recent_fd = Fd(
            subject="test_subject", stack=self.test_stack, created_at=self.recent_time
        )

        self.no_match_fd = Fd(
            subject="test_subject",
            stack=[
                'File "/usr/lib/python3.9/socket.py", line 232, in accept',
                'File "/usr/lib/python3.9/other_module.py", line 45, in other_function',
                'File "/usr/lib/python3.9/another_module.py", line 78, in another_function',
            ],
            created_at=self.old_time,
        )

    def test_create_fd_info_with_old_fd(self):
        """Test creating an FdInfo from an old Fd (older than min_age)."""
        # Act
        result = self.factory.create_fd_info(self.old_fd)

        # Assert
        assert result is not None
        assert isinstance(result, FdInfo)
        assert (
            result.identifier
            == 'File "/usr/lib/python3.9/example_module.py", line 78, in example_function'
        )
        assert result.stack == self.test_stack
        assert result.created_at == datetime.fromtimestamp(self.old_time)

    def test_create_fd_info_with_recent_fd(self):
        """Test creating an FdInfo from a recent Fd (newer than min_age)."""
        # Act
        result = self.factory.create_fd_info(self.recent_fd)

        # Assert
        assert result is None

    def test_create_fd_info_with_no_identifier_match(self):
        """Test creating an FdInfo from an Fd with no matching identifier."""
        # Act
        result = self.factory.create_fd_info(self.no_match_fd)

        # Assert
        assert result is None

    def test_create_fd_info_with_empty_include_list(self):
        """Test creating an FdInfo with an empty identifier_include_any_of list."""
        # Arrange
        factory = FdInfoFactory(min_age=60, identifier_include_any_of=[])

        # Act
        result = factory.create_fd_info(self.old_fd)

        # Assert
        assert result is None

    def test_create_fd_info_with_default_include_empty_string(self):
        """Test creating an FdInfo with the default identifier_include_any_of=['']."""
        # Arrange
        factory = FdInfoFactory(min_age=60)  # Default is identifier_include_any_of=[""]

        # Act
        result = factory.create_fd_info(self.old_fd)

        # Assert
        assert result is not None
        assert isinstance(result, FdInfo)
        # Empty string is in every string, so the first stack frame should be used
        assert result.identifier == self.test_stack[-1]

    @patch("time.time")
    def test_create_fd_info_with_mocked_time(self, mock_time):
        """Test creating an FdInfo with a mocked current time."""
        # Arrange
        mock_time.return_value = self.current_time
        fd = Fd(
            subject="test_subject",
            stack=self.test_stack,
            created_at=self.current_time - 61,  # Just over min_age
        )

        # Act
        result = self.factory.create_fd_info(fd)

        # Assert
        assert result is not None
        assert isinstance(result, FdInfo)

    def test_get_identifier_with_match(self):
        """Test getting an identifier with a matching stack frame."""
        # Act
        result = self.factory.get_identifier(self.old_fd)

        # Assert
        assert (
            result
            == 'File "/usr/lib/python3.9/example_module.py", line 78, in example_function'
        )

    def test_get_identifier_with_multiple_matches(self):
        """Test getting an identifier with multiple matching stack frames."""
        # Arrange
        factory = FdInfoFactory(
            min_age=60, identifier_include_any_of=["test", "example"]
        )

        # Act
        result = factory.get_identifier(self.old_fd)

        # Assert
        # Should return the first match in the stack
        assert (
            result
            == 'File "/usr/lib/python3.9/example_module.py", line 78, in example_function'
        )

    def test_get_identifier_with_no_match(self):
        """Test getting an identifier with no matching stack frame."""
        # Act
        result = self.factory.get_identifier(self.no_match_fd)

        # Assert
        assert result is None

    def test_get_identifier_with_empty_include_list(self):
        """Test getting an identifier with an empty identifier_include_any_of list."""
        # Arrange
        factory = FdInfoFactory(min_age=60, identifier_include_any_of=[])

        # Act
        result = factory.get_identifier(self.old_fd)

        # Assert
        assert result is None

    def test_get_identifier_with_empty_string_include(self):
        """Test getting an identifier with identifier_include_any_of=['']."""
        # Arrange
        factory = FdInfoFactory(min_age=60, identifier_include_any_of=[""])

        # Act
        result = factory.get_identifier(self.old_fd)

        # Assert
        # Empty string is in every string, so the first stack frame should be used
        assert result == self.test_stack[-1]
