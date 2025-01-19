import os
import sys
import pytest
from leaky.__main__ import main


def test_main_no_args(capsys):
    """Test main with no arguments"""
    sys.argv = ["leaky"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Usage: python -m leaky module_to_run [args...]" in captured.err


def test_main_with_nonexistent_module(capsys):
    """Test main with a module that doesn't exist"""
    sys.argv = ["leaky", "nonexistent_module"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Could not import module nonexistent_module" in captured.err


def test_main_with_python_file(tmp_path, capsys):
    """Test main with a Python file"""
    # Create a test Python file
    test_file = tmp_path / "test_script.py"
    test_file.write_text("print('Hello from test script')")

    sys.argv = ["leaky", str(test_file)]
    main()
    captured = capsys.readouterr()
    assert "Hello from test script" in captured.out


def test_main_with_nonexistent_file(capsys):
    """Test main with a Python file that doesn't exist"""
    sys.argv = ["leaky", "nonexistent.py"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: File nonexistent.py not found" in captured.err
