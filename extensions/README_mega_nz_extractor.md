# Mega.nz URL and Password Extractor

This extension extracts Mega.nz download URLs and passwords from URLScan results, specifically designed for analyzing malware delivery pages that serve Mega.nz links.

## Features

- Extracts Mega.nz URLs from HTML input fields with `id="txtfile"`
- Extracts associated passwords from text patterns like "Password is : 2025"
- Automatically defangs URLs for safe sharing
- Caches URLScan API responses to avoid repeated requests
- Supports both test mode and production mode
- Saves results in CSV format with comprehensive metadata
- Compatible with masq-monitor's extension framework

## Usage

### Via masq-monitor CLI (Recommended)

Run the extension with specific queries using the `-x` or `--extension` flag:

```bash
# Run with a specific query
python masq_monitor.py --query myquery --extension extract_mega_nz_url_and_password.py

# Run with hIGMA integration
python masq_monitor.py --higma input.yaml --extension extract_mega_nz_url_and_password.py

# Run with multiple extensions
python masq_monitor.py --query myquery -x extract_mega_nz_url_and_password.py -x other_extension.py
```

### Standalone Usage
```bash
python extract_mega_nz_url_and_password.py /path/to/masq-monitor/output/directory
```

### With Options
```bash
# Enable verbose logging
python extract_mega_nz_url_and_password.py --verbose /path/to/output/directory

# Disable response caching
python extract_mega_nz_url_and_password.py --no-cache /path/to/output/directory

# Run in test mode with sample data
python extract_mega_nz_url_and_password.py --test /path/to/output/directory
```

## Output

When run via masq-monitor, the extension creates a `mega_nz_extractions.csv` file in the `extensions/` subdirectory of the output directory:

```
output/
└── query_name_timestamp/
    ├── extensions/
    │   └── mega_nz_extractions.csv  # Output location
    ├── iocs/
    ├── images/
    └── report.html
```

When run standalone, the CSV file is created in the specified directory.

### CSV Format

The CSV file contains the following columns in order:

- `scan_id`: URLScan scan ID
- `response_hash`: Hash of the primary request response
- `password`: Extracted password
- `defanged_mega_url`: Defanged Mega.nz URL for safe sharing

## Example Output

```csv
scan_id,response_hash,password,defanged_mega_url
0198b472-c734-75f1-89a5-ff08f1f7e9b5,d6bd49a8af18d791ed343c6fbe72d725885ad35c451a5e2677cfc1722e95a190,2025,hxxps://mega[.]nz/file/bV00lCZK#-YMOA10utOaWZP9ZCyfHWPjBtIWHBLZBKZlwwaU0B8E
0198b102-4ee8-73ad-bf75-ee9fd638f1f8,6fc406816726d13bbeea18d60559717152e0ddf73d193b88329f47aab55457b4,2025,hxxps://mega[.]nz/file/hRYBlY5T#rwD5BTL9OSmfe6HbhR9CtGy-5H8O3QlF1YVdp86XjIA
```

## Integration with masq-monitor

### Automatic Execution via Configuration

This extension can be configured to run automatically as part of masq-monitor queries by adding it to the `extensions` list in your configuration:

```yaml
# Global extensions (run for all queries)
extensions:
  - extract_mega_nz_url_and_password.py

# Or query-specific extensions
queries:
  your-query-name:
    # ... other query configuration ...
    extensions:
      - extract_mega_nz_url_and_password.py
```

### CLI Override

When using the CLI extension flags (`-x` or `--extension`), they override any configuration-based extensions:

```bash
# This will ONLY run the specified extension, ignoring config
python masq_monitor.py --query myquery --extension extract_mega_nz_url_and_password.py

# If no CLI extensions specified, uses config-based extensions
python masq_monitor.py --query myquery
```

## Requirements

- Python 3.6+
- requests library
- Access to URLScan.io API (for fetching results and responses)
- Valid masq-monitor output directory with IOCs and scan IDs

## Error Handling

The extension includes comprehensive error handling for:
- Missing or corrupted scan ID files
- URLScan API request failures
- Invalid JSON responses
- Network connectivity issues
- Permission errors when saving files

## Performance Notes

- Responses are cached by default to avoid repeated API calls
- The extension runs in parallel with other extensions when triggered by masq-monitor
- Verbose logging is disabled when run via the framework to reduce noise
