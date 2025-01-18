"""Main entry point for leaky module"""
import importlib.util
import os
import sys
from pathlib import Path


def patch_fds():
    """Enable file descriptor tracking"""
    os.environ['DEBUG'] = '1'
    import leaky.leaky  # noqa


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m leaky module_to_run [args...]", file=sys.stderr)
        sys.exit(1)

    # Enable FD tracking
    patch_fds()

    # Get the module to run
    module_name = sys.argv[1]
    
    # Remove 'leaky' from sys.argv
    sys.argv = sys.argv[1:]

    # If it's a .py file, load it directly
    if module_name.endswith('.py'):
        module_path = Path(module_name).resolve()
        if not module_path.exists():
            print(f"Error: File {module_name} not found", file=sys.stderr)
            sys.exit(1)
        
        # Load the module from file
        spec = importlib.util.spec_from_file_location(
            module_path.stem, 
            str(module_path)
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
            importlib.import_module(module_name)
        except ImportError as e:
            print(f"Error: Could not import module {module_name}: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()