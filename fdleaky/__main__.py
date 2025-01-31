"""Main entry point for fdleaky module"""

import importlib.util
import sys
from pathlib import Path

from uvicorn.main import main as uvicorn_main

from fdleaky.fdleaky import patch_fds


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m fdleaky module_to_run [args...]", file=sys.stderr)
        sys.exit(1)

    # Enable FD tracking
    patch_fds()

    # Get the module to run
    module_name = sys.argv[1]

    # Remove 'fdleaky' from sys.argv
    sys.argv = sys.argv[1:]

    if module_name == "uvicorn":
        # We handle uvicorn as it's own special case.
        uvicorn_main()  # pylint: disable=E1120

    elif module_name.endswith(".py"):
        # If it's a .py file, load it directly
        module_path = Path(module_name).resolve()
        if not module_path.exists():
            print(f"Error: File {module_name} not found", file=sys.stderr)
            sys.exit(1)

        # Load the module from file
        spec = importlib.util.spec_from_file_location(
            module_path.stem, str(module_path)
        )
        if spec is None or spec.loader is None:
            print(f"Error: Could not load {module_name}", file=sys.stderr)
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path.stem] = module
        spec.loader.exec_module(module)
    else:
        # Try to import the module by name
        try:
            # This works as long as the module does not check "if __name__ == "__main__"
            module = importlib.import_module(f"{module_name}.__main__")
        except ImportError:
            try:
                # This works as long as the module does not check "if __name__ == "__main__"
                importlib.import_module(module_name)
            except ImportError as e:
                print(
                    f"Error: Could not import module {module_name}: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)


if __name__ == "__main__":
    main()
