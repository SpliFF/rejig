"""Data processing library with various issues for testing."""
import csv
import json
from pathlib import Path
from datetime import datetime


def load_csv(file_path):
    """Load data from CSV file."""
    data = []
    with open(file_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def load_json(file_path):
    """Load data from JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)


def save_csv(data, file_path):
    """Save data to CSV file."""
    if not data:
        return

    with open(file_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def save_json(data, file_path):
    """Save data to JSON file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


# Loop that could be a comprehension
def filter_by_status(records, status):
    """Filter records by status."""
    result = []
    for record in records:
        if record.get("status") == status:
            result.append(record)
    return result


# Loop that could be a comprehension
def extract_field(records, field_name):
    """Extract a single field from all records."""
    result = []
    for record in records:
        if field_name in record:
            result.append(record[field_name])
    return result


# Loop that could use any()
def has_active_records(records):
    """Check if any records are active."""
    for record in records:
        if record.get("status") == "active":
            return True
    return False


# Loop that could use all()
def all_records_valid(records):
    """Check if all records are valid."""
    for record in records:
        if not record.get("is_valid"):
            return False
    return True


# Duplicate logic
def calculate_total_amount(records):
    """Calculate total amount from records."""
    total = 0
    for record in records:
        amount = record.get("amount", 0)
        total = total + amount
    return total


# Almost identical to calculate_total_amount
def sum_values(records, field):
    """Sum values of a field."""
    total = 0
    for record in records:
        value = record.get(field, 0)
        total = total + value
    return total


# Magic numbers
def process_batch(records):
    """Process a batch of records."""
    batch_size = 100
    max_retries = 3
    timeout = 30

    results = []
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        for record in batch:
            results.append(process_record(record))

    return results


def process_record(record):
    """Process a single record."""
    # Complex nested logic
    if record is None:
        return None

    result = {}

    if "name" in record:
        name = record["name"]
        if name:
            name = name.strip()
            if len(name) > 0:
                result["name"] = name

    if "amount" in record:
        amount = record["amount"]
        if amount is not None:
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except ValueError:
                    amount = 0
            if amount > 0:
                result["amount"] = amount

    if "date" in record:
        date_str = record["date"]
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                result["date"] = date.isoformat()
            except ValueError:
                pass

    return result


# Hardcoded strings
def format_output(records):
    """Format records for output."""
    output = []
    header = "=== DATA REPORT ==="
    footer = "=== END OF REPORT ==="
    separator = "-" * 40

    output.append(header)
    output.append(separator)

    for record in records:
        output.append(f"Name: {record.get('name', 'N/A')}")
        output.append(f"Amount: ${record.get('amount', 0):.2f}")
        output.append(separator)

    output.append(footer)
    return "\n".join(output)


# Duplicate of filter_by_status
def get_active_records(records):
    """Get active records."""
    result = []
    for record in records:
        if record.get("status") == "active":
            result.append(record)
    return result


# Duplicate of filter_by_status
def get_inactive_records(records):
    """Get inactive records."""
    result = []
    for record in records:
        if record.get("status") == "inactive":
            result.append(record)
    return result


class DataProcessor:
    """Processor class for data operations."""

    def __init__(self, config=None):
        self.config = config or {}
        self.batch_size = 100
        self.max_records = 10000

    def load(self, file_path):
        path = Path(file_path)
        if path.suffix == ".csv":
            return load_csv(file_path)
        elif path.suffix == ".json":
            return load_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def save(self, data, file_path):
        path = Path(file_path)
        if path.suffix == ".csv":
            save_csv(data, file_path)
        elif path.suffix == ".json":
            save_json(data, file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def process(self, records):
        results = []
        for record in records:
            processed = process_record(record)
            if processed:
                results.append(processed)
        return results

    def filter(self, records, field, value):
        result = []
        for record in records:
            if record.get(field) == value:
                result.append(record)
        return result

    # Duplicate of sum_values
    def aggregate(self, records, field):
        total = 0
        for record in records:
            total = total + record.get(field, 0)
        return total


# Unused class
class OldProcessor:
    """Old processor - deprecated."""

    def __init__(self):
        self.data = []

    def load(self, path):
        self.data = load_csv(path)

    def process(self):
        return [process_record(r) for r in self.data]


# TODO: Add async processing
# FIXME: Memory usage is high for large datasets

def validate_record(record):
    """Validate a record."""
    errors = []

    if not record.get("name"):
        errors.append("Missing name")

    if not record.get("amount"):
        errors.append("Missing amount")
    elif not isinstance(record.get("amount"), (int, float)):
        errors.append("Amount must be numeric")

    return errors


# Almost identical to validate_record
def check_record(record):
    """Check if a record is valid."""
    issues = []

    if not record.get("name"):
        issues.append("Name is required")

    if not record.get("amount"):
        issues.append("Amount is required")
    elif not isinstance(record.get("amount"), (int, float)):
        issues.append("Amount must be a number")

    return issues
