"""Restore the shipped, SHA-verified model without a Hugging Face download."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skillnet.model_assets import restore_bundled_model


def main():
    manifest = restore_bundled_model(ROOT / '.models/multilingual-e5-small')
    print('Restored encoder:', manifest['repository'], manifest['revision'])
    print('All model bytes match config/semantic_model.json; no network required.')


if __name__ == '__main__':
    main()
