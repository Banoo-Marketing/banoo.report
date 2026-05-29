"""
export_context.py — Export your AI business context string.

Usage:
    python export_context.py              # Standard format
    python export_context.py --chatgpt   # ChatGPT-optimized
    python export_context.py --claude    # Claude-optimized (XML)
    python export_context.py --gemini    # Gemini compact
    python export_context.py --save      # Save to context.txt
    python export_context.py --chatgpt --save
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

_W = 54


def main() -> None:
    args = sys.argv[1:]

    fmt = "default"
    for flag in ("--chatgpt", "--claude", "--gemini"):
        if flag in args:
            fmt = flag.lstrip("-")
            break

    save = "--save" in args

    try:
        from api.context import get_context_string
        text = get_context_string(fmt=fmt)
    except Exception:
        print("\n  Cannot generate context.")
        print("  Run setup first: python onboarding/setup.py")
        sys.exit(1)

    print()
    print("─" * _W)
    print(f"  COPY FROM HERE  [{fmt.upper()}]")
    print("─" * _W)
    print()
    print(text)
    print()
    print("─" * _W)

    if save:
        out = Path("context.txt")
        try:
            out.write_text(text)
            print(f"\n  Saved to {out.resolve()}")
        except Exception:
            print("\n  Could not save file.")


if __name__ == "__main__":
    main()
