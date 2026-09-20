"""Export current manipulated records to backup file."""

import json
from pathlib import Path
from datetime import datetime

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"
backup_dir = Path(__file__).resolve().parent.parent / "backup"
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = backup_dir / f"manipulated_records_backup_{timestamp}.jsonl"

manipulated_records = []
total_records = 0

with manifest_path.open() as f:
    for line in f:
        if line.strip():
            total_records += 1
            record = json.loads(line)
            if record.get('category') == 'manipulated':
                manipulated_records.append(record)

print(f"Total records in manifest: {total_records}")
print(f"Manipulated records: {len(manipulated_records)}")

if manipulated_records:
    with backup_file.open('w') as f:
        for record in manipulated_records:
            f.write(json.dumps(record) + '\n')
    print(f"Exported {len(manipulated_records)} manipulated records to: {backup_file}")
else:
    print("No manipulated records found to backup")
