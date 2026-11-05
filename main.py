"""Local-first CLI. Original entrypoint is preserved in legacy_main.py."""
from job_assistant.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
