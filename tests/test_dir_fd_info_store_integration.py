import json
import datetime
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from fdleaky.dir_fd_info_store import DirFdInfoStore
from fdleaky.fd_info import FdInfo


class TestDirFdInfoStoreIntegration:
    """Integration tests for the DirFdInfoStore class with actual file system."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.store = DirFdInfoStore(dir=self.temp_dir)

        # Create a test FdInfo object
        self.test_fd_info = FdInfo(
            identifier="test-identifier",
            stack=["line1", "line2", "line3"],
            created_at=datetime.datetime(2023, 1, 1, 12, 0, 0),
        )
        # Store the ID for later use
        self.test_id = self.test_fd_info.id

    def teardown_method(self):
        """Clean up after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.temp_dir)

    def test_create_and_verify_file_content(self):
        """Test creating an FdInfo object and verify the file content."""
        # Act
        self.store.create(self.test_fd_info)

        # Assert
        file_path = self.temp_dir / f"{self.test_id}.json"
        assert file_path.exists(), f"File {file_path} should exist"

        # Read the file content and verify it
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)

        assert content["id"] == self.test_id
        assert content["identifier"] == "test-identifier"
        assert content["stack"] == ["line1", "line2", "line3"]
        assert isinstance(content["created_at"], str)

    def test_delete_existing_file(self):
        """Test deleting an existing file."""
        # Arrange
        self.store.create(self.test_fd_info)
        file_path = self.temp_dir / f"{self.test_id}.json"
        assert file_path.exists(), "File should exist before deletion"

        # Act
        result = self.store.delete(self.test_id)

        # Assert
        assert result is True, "Delete should return True for existing file"
        assert not file_path.exists(), "File should not exist after deletion"

    def test_delete_nonexistent_file(self):
        """Test deleting a non-existent file."""
        # Act
        result = self.store.delete("nonexistent-id")

        # Assert
        assert result is False, "Delete should return False for non-existent file"

    def test_multiple_creates_and_deletes(self):
        """Test creating and deleting multiple FdInfo objects."""
        # Create multiple FdInfo objects
        fd_infos = []
        for i in range(5):
            fd_info = FdInfo(
                identifier=f"test-identifier-{i}",
                stack=[f"line{j}" for j in range(i + 1)],
                created_at=datetime.datetime(2023, 1, i + 1, 12, 0, 0),
            )
            fd_infos.append(fd_info)
            self.store.create(fd_info)

        # Verify all files exist
        for fd_info in fd_infos:
            file_path = self.temp_dir / f"{fd_info.id}.json"
            assert file_path.exists(), f"File {file_path} should exist"

        # Delete some files
        for i, fd_info in enumerate(fd_infos):
            if i % 2 == 0:  # Delete even-indexed files
                result = self.store.delete(fd_info.id)
                assert result is True, f"Delete should return True for {fd_info.id}"
                file_path = self.temp_dir / f"{fd_info.id}.json"
                assert (
                    not file_path.exists()
                ), f"File {file_path} should not exist after deletion"

        # Verify remaining files still exist
        for i, fd_info in enumerate(fd_infos):
            file_path = self.temp_dir / f"{fd_info.id}.json"
            if i % 2 == 0:
                assert not file_path.exists(), f"File {file_path} should not exist"
            else:
                assert file_path.exists(), f"File {file_path} should exist"
