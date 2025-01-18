# Leaky

A Python utility for detecting file descriptor leaks in Python applications. Leaky monitors file and socket operations in your application and reports any resources that remain open longer than expected.

## Purpose

File descriptor leaks can be difficult to track down, especially in long-running applications. These leaks can lead to:
- Resource exhaustion
- "Too many open files" errors
- Degraded system performance
- Memory leaks

Leaky helps you find these issues by:
- Tracking all file and socket operations
- Recording stack traces when resources are opened
- Detecting resources that remain open too long
- Reporting unclosed resources on shutdown

## Installation

```bash
pip install leaky
```

## Usage

Run your Python application with Leaky monitoring:

```bash
# Run a module
python -m leaky your_module

# Run a Python file
python -m leaky your_script.py
```

When a file descriptor remains open longer than the threshold (default 180 seconds), Leaky will log:
- The type of resource (file/socket)
- The stack trace from when it was opened
- The time it has been open

## Development

This project uses poetry for dependency management. To get started:

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest
```

## How it Works

Leaky works by:
1. Patching built-in file and socket operations
2. Tracking all open file descriptors
3. Monitoring for resources that remain open too long
4. Providing stack traces to help identify the source of leaks

The monitoring is only active when the DEBUG environment variable is set to '1', which is handled automatically when running through the leaky module.