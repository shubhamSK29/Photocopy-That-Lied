"""Export current processing records to backup file."""

import json
from pathlib import Path
from datetime import datetime

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"
backup_dir = Path(__file__).resolve().parent.parent / "backup"
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"processing_records_backup_{timestamp}.jsonl"

np_records = []
hn_records = []
total_records = 0

with manifest_path.open() as f:
    for line in f:
        if line.strip():
            total_records += 1
            record = json.loads(line)
            if record.get('category') == 'natural_processing':
                np_records.append(record)
            elif record.get('category') == 'hard_negative':
                hn_records.append(record)

print(f"Total records in manifest: {total_records}")
print(f"Natural-processing records: {len(np_records)}")
print(f"Hard-negative records: {len(hn_records)}")

all_processing = np_records + hn_records
if all_processing:
    with backup_file.open('w') as f:
        for record in all_processing:
            f.write(json.dumps(record) + '\n')
    print(f"Exported {len(all_processing)} processing records to: {backup_file}")
else:
    print("No processing records found to backup")
