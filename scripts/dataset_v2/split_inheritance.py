"""Split inheritance for Dataset V2 variants."""

import json
from pathlib import Path
from typing import Dict, Set


class SplitInheritance:
    """Manages split inheritance for source families."""

    def __init__(self, splits_dir: Path):
        """
        Initialize split inheritance from splits directory.

        Args:
            splits_dir: Path to splits directory containing train.json, validation.json, test.json
        """
        self.splits_dir = splits_dir
        self.source_to_split: Dict[str, str] = {}
        self._load_splits()

    def _load_splits(self):
        """Load split files and build source-to-split mapping."""
        splits_file = self.splits_dir / 'splits.json'
        if not splits_file.exists():
            raise FileNotFoundError(f"Splits file not found: {splits_file}")

        with splits_file.open() as f:
            splits_data = json.load(f)

        # Build mapping from source ID to split
        for split_name in ['train', 'validation', 'test']:
            for source_id in splits_data.get(split_name, []):
                self.source_to_split[source_id] = split_name

    def get_split(self, source_id: str) -> str:
        """
        Get the split assignment for a source ID.

        Args:
            source_id: Source identifier

        Returns:
            Split name ('train', 'validation', or 'test')

        Raises:
            ValueError: If source ID is not found in any split
        """
        if source_id not in self.source_to_split:
            raise ValueError(f"Source ID {source_id} not found in any split")
        return self.source_to_split[source_id]

    def is_split_safe(self, source_id_1: str, source_id_2: str) -> bool:
        """
        Check if two source IDs belong to the same split.

        This is important for splicing operations to ensure
        donor and target images are from the same split.

        Args:
            source_id_1: First source ID
            source_id_2: Second source ID

        Returns:
            True if both sources are in the same split
        """
        if source_id_1 not in self.source_to_split or source_id_2 not in self.source_to_split:
            return False
        return self.source_to_split[source_id_1] == self.source_to_split[source_id_2]

    def get_all_sources_in_split(self, split_name: str) -> Set[str]:
        """
        Get all source IDs in a specific split.

        Args:
            split_name: Split name ('train', 'validation', or 'test')

        Returns:
            Set of source IDs in the split
        """
        return {
            source_id for source_id, split in self.source_to_split.items()
            if split == split_name
        }


# Global instance for convenience
_global_split_inheritance = None


def get_source_split(source_id: str, splits_dir: Path = None) -> str:
    """
    Get the split for a source ID using a global instance.

    Args:
        source_id: Source identifier
        splits_dir: Path to splits directory (optional, uses default if not provided)

    Returns:
        Split name
    """
    global _global_split_inheritance

    if splits_dir is None:
        from pathlib import Path
        splits_dir = Path(__file__).resolve().parent.parent.parent / 'dataset_v2' / 'splits'

    if _global_split_inheritance is None or _global_split_inheritance.splits_dir != splits_dir:
        _global_split_inheritance = SplitInheritance(splits_dir)

    return _global_split_inheritance.get_split(source_id)
