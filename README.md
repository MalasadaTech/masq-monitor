# Masquerade Monitor

A Python application to help automate monitoring for website masquerades using urlscan.io and other search platforms.

## Overview

Masquerade Monitor can help you track potential phishing campaigns (or other campaigns) by searching for websites mimicking legitimate brands. The tool queries search platforms like urlscan.io for new scans that match your monitoring criteria, saving the results as HTML reports with thumbnail previews.

The basic idea:
It takes a list of monitoring pivots, and performs API calls to check if there is anything new since the last check.

It currently supports urlscan.io requests with plans to expand to other sources (including Silent Push API) in the future. urlscan.io is used because they allow free API searches that should suffice for basic monitoring.

## Features

- Queries search platforms for potential masquerade websites (BYO-Queries)
- Multiple platform support (urlscan.io, with Silent Push API coming soon)
- Modular architecture with platform-specific client modules
- Saves screenshots of detected sites
- Generates standalone HTML reports with embedded screenshots
- Includes query metadata (reference, notes, frequency, priority, tags) in reports
- Supports TLP (Traffic Light Protocol) classification for information sharing control
- Supports query groups for organizing related queries and generating comprehensive reports
- Allows hierarchical organization with nested query groups
- Dark mode support with user preference memory
- Interactive image viewer for examining thumbnails in full-screen mode
- Tracks the last run timestamp for each query
- Supports custom lookback periods for searches
- Defangs IOCs (URLs and domains) in reports for safer sharing
- Customizable report username
- Branded footer with project links
- API keys stored in .env file for better security

## Example Monitoring Techniques

To monitor for USAA masquerades:
- Method 1: Monitoring for scan tasks that have "USAA" in the page.title
- Method 2: Monitoring for scan tasks that have "usaa" in the domain
- Method 3: Monitoring for scan tasks that use the official USAA favicon hash (or any other official USAA asset hashes)

The monitoring techniques need to be periodically updated as needed.

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/masq-monitor.git
cd masq-monitor
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Create your configuration file:
```
cp config.example.json config.json
```

4. Create your .env file for API keys:
```
cp .env.example .env
```

5. Edit `.env` with your urlscan.io API key:
```
URLSCAN_API_KEY=your_urlscan_api_key_here
```

6. Edit `config.json` with your desired monitoring queries.

## API Key Configuration

API keys are stored in a `.env` file, following security best practices. This keeps sensitive credentials out of your code and configuration files. To set up your API key:

1. Create a `.env` file in the root directory of the project (or copy from `.env.example`)
2. Add your URLScan.io API key:
```
URLSCAN_API_KEY=your_urlscan_api_key_here
```

The `.env` file is included in `.gitignore` to prevent accidentally committing your API keys to version control.

## Team Sharing

With this setup, team members can share their configuration files (queries, reporting preferences, etc.) without exposing their API keys. Simply share the `config.json` file, and each team member can use their own `.env` file with their personal API key.

## Usage

### List Available Queries

```
python masq_monitor.py --list
```

### Run a Specific Query

```
python masq_monitor.py --query usaa-domain
```

### Run a Query Group

```
python masq_monitor.py --query-group usaa-monitoring
```

Query groups run multiple related queries and create a combined report with sections for each query.

### Limit Results to a Specific Number of Days

Especially useful for initial runs to avoid processing too many results:

```
python masq_monitor.py --query usaa-domain -d 7
```

This limits the search to results from the last 7 days.

### Run All Queries

```
python masq_monitor.py --all
```

This runs all individual queries (not query groups).

### Run All Query Groups

```
python masq_monitor.py --all-groups
```

This runs all query groups defined in the configuration.

### Run All Queries and Query Groups

You can combine the --all and --all-groups flags:

```
python masq_monitor.py --all --all-groups
```

You can also limit all queries to a timeframe:

```
python masq_monitor.py --all --all-groups -d 30
```

### Specify Custom Config File

```
python masq_monitor.py --config my_custom_config.json --all
```

### Override Default TLP Level

You can override the default TLP level specified in the configuration file:

```
python masq_monitor.py --query usaa-domain --tlp red
```

This will generate the report with a TLP:RED classification regardless of the default setting in the config file.

## Configuration

The configuration file is in JSON format with the following structure:

```json
{
    "output_directory": "output",
    "default_days": 7,
    "report_username": "Your Name",
    "default_tlp_level": "clear",
    "default_template_path": "templates/report_template.html",
    "queries": {
        "usaa-title": {
            "query": "page.title:\"Member Account Login | USAA\"",
            "platform": "urlscan",
            "description": "This report shows one subset of phishing sites that masquerade as USAA.",
            "description_tlp_level": "clear",
            "query_tlp_level": "green",
            "default_tlp_level": "clear",
            "template_path": "templates/custom_template.html",
            "notes": [
                {
                    "tlp_level": "clear",
                    "text": "This is a report of phishing sites that masquerade as USAA."
                },
                {
                    "tlp_level": "green",
                    "text": "The query tracks the masqs by the page title. This is data that could be released to fellow analysts, but should be generally withheld from the bad guys."
                },
                {
                    "tlp_level": "red",
                    "text": "This note has something that shouldn't be shared with the world. This note may contain info like an analyst's name or something."
                }
            ],
            "references": [
                {
                    "tlp_level": "clear",
                    "url": "https://www.usaa.com/security"
                },
                {
                    "tlp_level": "green",
                    "url": "https://intranet.example.com/usaa-phishing-analysis"
                },
                {
                    "tlp_level": "amber",
                    "url": "https://intel.example.com/confidential/usaa-2025-report.pdf"
                }
            ],
            "frequency": "Daily",
            "frequency_tlp_level": "green",
            "priority": "High",
            "priority_tlp_level": "green",
            "tags": [
                "phishing",
                "banking"
            ],
            "tags_tlp_level": "green",
            "days": 7,
            "last_run": "2025-04-20T23:59:54.633456"
        },
        "usaa-monitoring": {
            "type": "query_group",
            "description": "Comprehensive monitoring for USAA masquerades using multiple detection methods",
            "description_tlp_level": "clear",
            "default_tlp_level": "green",
            "queries": ["usaa-domain", "usaa-title", "usaa-favicon"],
            "titles": [
                {
                    "title": "USAA MASQUERADE MONITORING - COMBINED REPORT",
                    "tlp_level": "green"
                },
                {
                    "title": "USAA MASQUERADE MONITORING - COMPREHENSIVE DETECTION",
                    "tlp_level": "amber"
                }
            ],
            "notes": [
                {
                    "tlp_level": "green",
                    "text": "This group combines multiple detection methods for a comprehensive view of USAA masquerade attempts."
                },
                {
                    "tlp_level": "amber",
                    "text": "The combined approach detects phishing sites through domain patterns, page titles, and favicon hashes."
                }
            ],
            "frequency": "Daily",
            "frequency_tlp_level": "clear",
            "priority": "High",
            "priority_tlp_level": "clear",
            "tags": ["financial", "usaa", "combined-monitoring"],
            "tags_tlp_level": "clear",
            "last_run": null
        }
    }
}
```

> **Note:** The queries in `config.example.json` are hypothetical examples to demonstrate the configuration structure. They are not guaranteed to return results and references may not be valid links. You should create your own queries based on your specific monitoring needs.

### Configuration Options

- `output_directory`: Directory to store reports and screenshots.
- `default_days`: Default number of days to limit the search to if no `last_run` timestamp exists and the `--days` flag is not specified.
- `report_username`: Your name or username to be displayed in generated reports.
- `default_template_path`: The default template to use for all queries that don't have a specific template.
- `queries`: A map of named queries to execute against search platforms.
  - `platform`: Search platform to use for this query. Currently supported: "urlscan", "silentpush" (coming soon). Defaults to "urlscan" if not specified.
  - `query`: The search query string formatted for the specified platform.
  - `last_run`: Timestamp of when the query was last executed. Used to limit searches to only new results since the last run.
  - `query_tlp_level`: TLP (Traffic Light Protocol) classification for the query itself. Determines how sensitive the search pattern is. Values: "clear", "white", "green", "amber", "red".
  - `default_tlp_level`: Default TLP classification for report content. Used for report elements without their own explicit TLP level. Values: "clear", "white", "green", "amber", "red".
  - `template_path`: Optional per-query HTML template to use for the report. If not specified, falls back to the global `default_template_path`.
  - `reference`: Optional link to documentation or source for the query.
  - `notes`: Additional contextual information about the query.
  - `frequency`: Suggested frequency for running this query (e.g., "daily", "weekly").
  - `priority`: Indicates importance of the query (e.g., "high", "medium", "low").
  - `tags`: List of keywords to categorize the query.

### Query Group Configuration

Query groups allow you to organize related queries and generate combined reports. A query group is defined with the following options:

- `type`: Must be set to "query_group" to identify this entry as a query group rather than a regular query.
- `queries`: An array of query names (or other query groups) that belong to this group.
- `description`: Description of the query group's purpose.
- `description_tlp_level`: TLP classification for the description.
- `default_tlp_level`: Default TLP classification for the group report.
- `titles`: Array of titles with TLP classifications, similar to regular queries.
- `notes`, `references`, `frequency`, `priority`, `tags`: Same metadata fields as regular queries.
- `last_run`: Timestamp of when the group was last executed.

Query groups can be nested, allowing for a hierarchical organization of your monitoring activities. For example:
- A "banking-group" query group might contain:
  - The "usaa-monitoring" query group (which itself contains individual queries)
  - The "chase-domain" query

### Query Examples

1. Domain contains specific text:
```
domain:*bank*
```

2. Page title contains specific text:
```
page.title:*login*
```

3. Multiple conditions:
```
domain:*paypal* AND page.title:*secure*
```

4. Specific hash (e.g., favicon):
```
hash:"fa6a5a3224d7da66d9e0bdec25f62cf0"
```

## Output

The tool generates standalone HTML reports in the output directory with the following structure:

For individual queries:
```
output/
  query-name_YYYYMMDD_HHMMSS/
    report_query-name_YYYYMMDD_HHMMSS_TLP-level.html
    images/
      [scan-uuid1].png
      [scan-uuid2].png
      ...
```

For query groups:
```
output/
  group-name_YYYYMMDD_HHMMSS_group/
    report_group-name_YYYYMMDD_HHMMSS_TLP-level.html
    images/
      [scan-uuid1].png
      [scan-uuid2].png
      ...
```

The HTML reports are self-contained files with all screenshots embedded as Base64-encoded images, allowing them to be shared or archived as single files without external dependencies.

## Changelog

For a detailed history of changes and improvements, please see the [changelog.md](changelog.md) file.

## Roadmap

### Short-term (1-3 months)
- ✓ Add date filtering to only show results since last check
- ✓ Prioritize using `last_run` timestamp before falling back to `default_days`
- ✓ Add query metadata options (reference, notes, frequency, priority, tags)
- ✓ Add query groups for organizing related queries and generating comprehensive reports
- ✓ Move API keys to .env file for better security
- ✓ Add support for multiple search platforms including "urlscan" and "silentpush"
- Implement Silent Push API integration
- Implement email notifications for new findings
- Support for custom report templates
- Add ability to export results to CSV/JSON

### Medium-term (3-6 months)
- Integrate additional data sources beyond urlscan.io
- Add machine learning capabilities to detect similar domains
- Implement a web dashboard for monitoring results
- Support for scheduled automatic checks

### Long-term (6+ months)
- Create an API for programmatic access to monitoring results
- Develop plugins for security tools integration
- Implement advanced analytics to detect sophisticated phishing techniques
- Add collaborative features for team-based monitoring

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
