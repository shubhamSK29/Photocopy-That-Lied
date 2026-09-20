"""Wrapper script to run Dataset V2 pilot generation."""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from dataset_v2.pilot_generator import main

if __name__ == '__main__':
    main()
