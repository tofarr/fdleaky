import builtins
import socket
from tempfile import _io
import threading
from unittest.mock import patch, MagicMock

from fdleaky.fd import Fd
from fdleaky.fd_info import FdInfo
from fdleaky.fd_info_factory import FdInfoFactory
from fdleaky.fd_info_store import FdInfoStore
from fdleaky.fd_tracker import FdTracker, _get_subject


class TestFdTracker:
    """Unit tests for the FdTracker class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock objects
        self.mock_fd_info_factory = MagicMock(spec=FdInfoFactory)
        self.mock_long_term_store = MagicMock(spec=FdInfoStore)

        # Create the tracker with mocked dependencies
        self.tracker = FdTracker(
            fd_info_factory=self.mock_fd_info_factory,
            long_term_store=self.mock_long_term_store,
            sleep_interval=0.01,  # Use a small interval for faster tests
        )

        # Save original functions to restore later
        self.original_open = builtins.open
        self.original_socket_init = socket.socket.__init__
        self.original_socket_close = socket.socket.close
        self.original_socket_detach = socket.socket.detach
        self.original_io_open = _io.open

    def teardown_method(self):
        """Clean up after each test method."""
        # Ensure tracker is closed
        if self.tracker.is_open:
            # Set is_open to False to avoid hanging in _do_long_term_store
            self.tracker.is_open = False
            # Only join the worker if it exists
            if self.tracker._worker:
                self.tracker._worker.join()

        # Restore original functions
        builtins.open = self.original_open
        socket.socket.__init__ = self.original_socket_init
        socket.socket.close = self.original_socket_close
        socket.socket.detach = self.original_socket_detach
        _io.open = self.original_io_open

    def test_context_manager(self):
        """Test that the tracker works as a context manager."""
        # Arrange - Create a tracker with mocked Thread
        tracker = FdTracker(
            fd_info_factory=self.mock_fd_info_factory,
            long_term_store=self.mock_long_term_store,
            sleep_interval=0.01,
        )

        # Replace the _do_long_term_store method with a no-op to avoid the thread
        tracker._do_long_term_store = MagicMock()

        # Act
        with tracker as t:
            assert t.is_open is True
            # We can't directly compare the functions because they're patched
            # Instead, check that our tracker's original functions are set
            assert tracker._original_open is not None
            assert tracker._original_init is not None

        # Assert
        assert t.is_open is False

    def test_start_and_close(self):
        """Test starting and closing the tracker."""
        # Arrange - Create a tracker
        tracker = FdTracker(
            fd_info_factory=self.mock_fd_info_factory,
            long_term_store=self.mock_long_term_store,
            sleep_interval=0.01,
        )

        # Replace the _do_long_term_store method with a no-op to avoid the thread
        tracker._do_long_term_store = MagicMock()

        assert tracker.is_open is False
        assert tracker._worker is None

        # Act - Start
        tracker.start()

        # Assert - Started
        assert tracker.is_open is True
        assert tracker._worker is not None
        assert isinstance(tracker._worker, threading.Thread)

        # Act - Close
        tracker.close()

        # Assert - Closed
        assert tracker.is_open is False

    def test_start_idempotent(self):
        """Test that calling start multiple times only starts once."""
        # Arrange - Create a tracker
        tracker = FdTracker(
            fd_info_factory=self.mock_fd_info_factory,
            long_term_store=self.mock_long_term_store,
            sleep_interval=0.01,
        )

        # Replace the _do_long_term_store method with a no-op to avoid the thread
        tracker._do_long_term_store = MagicMock()

        # Act
        tracker.start()
        first_worker = tracker._worker
        tracker.start()  # Second call should be ignored

        # Assert
        assert tracker.is_open is True
        assert tracker._worker is first_worker  # Worker should be the same object

    def test_close_idempotent(self):
        """Test that calling close multiple times only closes once."""
        # Arrange
        self.tracker.start()
        worker = self.tracker._worker

        # Act
        self.tracker.close()
        self.tracker.close()  # Second call should be ignored

        # Assert
        assert self.tracker.is_open is False
        assert worker.is_alive() is False

    def test_patched_open(self):
        """Test that open is patched correctly."""
        # Arrange - Create a tracker with mocked Thread
        tracker = FdTracker(
            fd_info_factory=self.mock_fd_info_factory,
            long_term_store=self.mock_long_term_store,
            sleep_interval=0.01,
        )

        # Replace the _do_long_term_store method with a no-op to avoid the thread
        tracker._do_long_term_store = MagicMock()

        # Save the original open function
        original_open = builtins.open

        # Create a mock open function
        mock_file = MagicMock()
        original_close = mock_file.close
        mock_open = MagicMock(return_value=mock_file)

        try:
            # Start the tracker with our mock
            tracker._original_open = original_open
            builtins.open = mock_open

            # Act
            tracker.start()
            # Call the patched open function
            result = tracker._patched_open("test.txt", "r")
            # Call the patched close function
            result.close()

            # Assert
            mock_open.assert_called_once_with("test.txt", "r")
            assert result is mock_file
            # Verify that close was patched (it should be different from the original)
            assert mock_file.close is not original_close
            # After closing, the short_term_store should be empty
            assert len(tracker.short_term_store) == 0

            # Clean up
            tracker.close()
        finally:
            # Restore the original open function
            builtins.open = original_open

    @patch("socket.socket.__init__")
    @patch("threading.Thread")
    def test_patched_socket_init(self, mock_thread, mock_init):
        """Test that socket.__init__ is patched correctly."""
        # Arrange
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # We need to fix the _get_subject function for our test
        # Let's directly test the _patched_init method instead
        self.tracker._original_init = mock_init
        mock_init.return_value = None

        # Create a test socket
        sock = MagicMock()

        # Act
        with patch("fdleaky.fd_tracker.Thread", MagicMock()) as mock:
            self.tracker.start()
            mock.return_value.start.assert_called_once()

        # Directly call the patched init with our mock socket
        self.tracker._patched_init(sock)

        # Assert
        mock_init.assert_called_once_with(sock)
        # Verify that the socket was added to the short_term_store
        assert any(fd.subject is sock for fd in self.tracker.short_term_store.values())

    @patch("socket.socket.close")
    def test_patched_socket_close(self, mock_close):
        """Test that socket.close is patched correctly."""
        # Arrange
        mock_close.return_value = None
        self.tracker._original_close = mock_close
        sock = MagicMock()
        sock_id = id(sock)
        self.tracker.short_term_store[sock_id] = Fd(sock, ["stack1", "stack2"])

        # Act
        with self.tracker:
            socket.socket.close(sock)

        # Assert
        mock_close.assert_called_once_with(sock)
        assert sock_id not in self.tracker.short_term_store

    @patch("socket.socket.detach")
    def test_patched_socket_detach(self, mock_detach):
        """Test that socket.detach is patched correctly."""
        # Arrange
        mock_detach.return_value = 5  # Some file descriptor
        self.tracker._original_detach = mock_detach
        sock = MagicMock()
        sock_id = id(sock)
        self.tracker.short_term_store[sock_id] = Fd(sock, ["stack1", "stack2"])

        # Act
        with self.tracker:
            result = socket.socket.detach(sock)

        # Assert
        assert result == 5
        mock_detach.assert_called_once_with(sock)
        assert sock_id not in self.tracker.short_term_store

    def test_create_fd(self):
        """Test creating a file descriptor."""
        # Arrange
        file_obj = MagicMock()

        # Act
        fd_id = self.tracker._create_fd(file_obj)

        # Assert
        assert fd_id == id(file_obj)
        assert fd_id in self.tracker.short_term_store
        assert self.tracker.short_term_store[fd_id].subject is file_obj
        assert isinstance(self.tracker.short_term_store[fd_id].stack, list)

    def test_close_fd(self):
        """Test closing a file descriptor."""
        # Arrange
        file_obj = MagicMock()
        fd_id = id(file_obj)
        self.tracker.short_term_store[fd_id] = Fd(file_obj, ["stack1", "stack2"])
        stored_id = "stored-id-123"
        self.tracker._id_mapping[fd_id] = stored_id

        # Act
        self.tracker._close_fd(fd_id)

        # Assert
        assert fd_id not in self.tracker.short_term_store
        assert fd_id not in self.tracker._id_mapping
        self.mock_long_term_store.delete.assert_called_once_with(stored_id)

    def test_close_fd_not_in_long_term(self):
        """Test closing a file descriptor that's not in long-term storage."""
        # Arrange
        file_obj = MagicMock()
        fd_id = id(file_obj)
        self.tracker.short_term_store[fd_id] = Fd(file_obj, ["stack1", "stack2"])

        # Act
        self.tracker._close_fd(fd_id)

        # Assert
        assert fd_id not in self.tracker.short_term_store
        self.mock_long_term_store.delete.assert_not_called()

    def test_do_long_term_store_single_iteration(self):
        """Test a single iteration of the long-term storage logic."""
        # Arrange
        file_obj = MagicMock()
        fd_id = id(file_obj)
        fd = Fd(file_obj, ["stack1", "stack2"])
        self.tracker.short_term_store[fd_id] = fd

        mock_fd_info = MagicMock(spec=FdInfo)
        mock_fd_info.id = "fd-info-id-123"
        self.mock_fd_info_factory.create_fd_info.return_value = mock_fd_info

        # Act - directly test the logic inside _do_long_term_store without the loop
        for fd in list(self.tracker.short_term_store.values()):
            self.tracker._process_fd_for_long_term(fd)

        # Assert
        self.mock_fd_info_factory.create_fd_info.assert_called_with(fd)
        self.mock_long_term_store.create.assert_called_with(mock_fd_info)
        assert self.tracker._id_mapping[fd_id] == mock_fd_info.id

    def test_do_long_term_store_no_fd_info(self):
        """Test the long-term storage logic when no FdInfo is created."""
        # Arrange
        file_obj = MagicMock()
        fd_id = id(file_obj)
        fd = Fd(file_obj, ["stack1", "stack2"])
        self.tracker.short_term_store[fd_id] = fd

        self.mock_fd_info_factory.create_fd_info.return_value = None

        # Act - directly test the logic inside _do_long_term_store without the loop
        for fd in list(self.tracker.short_term_store.values()):
            self.tracker._process_fd_for_long_term(fd)

        # Assert
        self.mock_fd_info_factory.create_fd_info.assert_called_with(fd)
        self.mock_long_term_store.create.assert_not_called()
        assert fd_id not in self.tracker._id_mapping

    def test_do_long_term_store_already_mapped(self):
        """Test the long-term storage logic when fd is already mapped."""
        # Arrange
        file_obj = MagicMock()
        fd_id = id(file_obj)
        fd = Fd(file_obj, ["stack1", "stack2"])
        self.tracker.short_term_store[fd_id] = fd
        self.tracker._id_mapping[fd_id] = "existing-id"

        # Override the loop so that the value only appears once.
        original_process_fd_for_long_term = self.tracker._process_fd_for_long_term

        def override_process_fd_for_long_term(fd: Fd):
            self.tracker.is_open = False
            return original_process_fd_for_long_term(fd)

        self.tracker._process_fd_for_long_term = override_process_fd_for_long_term
        self.tracker.is_open = True
        self.tracker._do_long_term_store()

        # Assert
        self.mock_fd_info_factory.create_fd_info.assert_not_called()
        self.mock_long_term_store.create.assert_not_called()
        assert self.tracker._id_mapping[fd_id] == "existing-id"

    def test_get_subject_from_args(self):
        """Test getting the subject from args."""
        # Arrange
        subject = MagicMock()
        args = (subject, "arg2", "arg3")
        kwargs = {"kwarg1": "value1"}

        # Act
        result = _get_subject(args, kwargs)

        # Assert
        assert result is subject

    def test_get_subject_from_kwargs(self):
        """Test getting the subject from kwargs."""
        # Arrange
        subject = MagicMock()
        args = ()
        kwargs = {"self": subject, "kwarg1": "value1"}

        # Act
        result = _get_subject(args, kwargs)

        # Assert
        assert result is subject
