# Masquerade Monitor

A Python application to help automate monitoring for website masquerades using urlscan.io.

## Overview

Masquerade Monitor can help you track potential phishing campaigns (or other campaigns) by searching for websites mimicking legitimate brands. The tool queries urlscan.io for new scans that match your monitoring criteria, saving the results as HTML reports with thumbnail previews.

The basic idea:
It takes a list of monitoring pivots, and performs API calls to check if there is anything new since the last check.

It currently supports urlscan.io requests with plans to expand to other sources in the future. urlscan.io is used because they allow free API searches that should suffice for basic monitoring.

## Features

- Queries urlscan.io for potential masquerade websites (BYO-Queries)
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
- API keys stored in separate file for easier team sharing of monitoring configurations

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

4. Create your API key file:
```
cp api_key.example.json api_key.json
```

5. Edit `api_key.json` with your urlscan.io API key:
```json
{
    "urlscan_api_key": "YOUR_URLSCAN_API_KEY"
}
```

6. Edit `config.json` with your desired monitoring queries.

## API Key Configuration

The API key is stored separately from the main configuration to make sharing monitoring configurations easier within teams. Store your URLScan.io API key in `api_key.json`:

```json
{
    "urlscan_api_key": "YOUR_URLSCAN_API_KEY"
}
```

This file is included in `.gitignore` to prevent accidentally committing your API key.

## Team Sharing

With this setup, team members can share their configuration files (queries, reporting preferences, etc.) without exposing their API keys. Simply share the `config.json` file, and each team member can use their own `api_key.json` file.

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

### Specify Custom Config and API Key Files

```
python masq_monitor.py --config my_custom_config.json --api-key-file my_api_key.json --all
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
- `queries`: A map of named queries to execute against urlscan.io.
  - `last_run`: Timestamp of when the query was last executed. Used to limit searches to only new results since the last run.
  - `query_tlp_level`: TLP (Traffic Light Protocol) classification for the query itself. Determines how sensitive the search pattern is. Values: "clear", "green", "amber", "red".
  - `default_tlp_level`: Default TLP classification for report content. Used for report elements without their own explicit TLP level. Values: "clear", "green", "amber", "red".
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

### Version 0.4.1 (April 24, 2025)
- Fixed error when listing queries with query groups by safely accessing query attributes
- Enhanced the query listing display to show query types (Query vs Query Group)
- Improved display of query groups to show member queries instead of query strings
- Better formatting for `--list` command output with consistent structure

### Version 0.4.0 (April 20, 2025)
- Added support for query groups to organize related queries
- Implemented hierarchical query structure with nested query groups
- Added group report generation with sections for each individual query
- Group reports combine results from all queries with source tracking
- Added new command-line options for managing query groups
- Updated HTML template to properly display grouped results

### Version 0.3.3 (April 20, 2025)
- Added support for custom templates per query
- Added `default_template_path` config option to set the global default template
- Added `template_path` option per query to specify a custom template
- Improved error handling for template loading with fallback to default template

### Version 0.3.2 (April 20, 2025)
- Fixed TLP color rendering when printing reports to PDF
- Added CSS rules to ensure background colors are correctly displayed in PDF output
- Preserved dark theme when printing to PDF if dark theme was selected in the UI
- Enhanced print media queries for better PDF export support

### Version 0.3.1 (April 20, 2025)
- Added interactive image viewer to expand screenshots to full view when clicked
- Implemented close functionality via X button, clicking outside the image, or pressing the Escape key
- Enhanced user experience by providing better visualization of screenshot details

### Version 0.3.0 (April 21, 2025)
- Added TLP (Traffic Light Protocol) support for reports
- Implemented `query_tlp_level` to determine sensitivity of the query itself
- Added `default_tlp_level` to set classification for report content by default
- Added TLP level in report filenames for easier identification
- Report headers now display TLP classification with appropriate color coding
- Added command-line flag `--tlp` to override default TLP level when generating reports

### Version 0.2.0 (April 20, 2025)
- Fixed URL defanging to preserve filenames in their original form
- Added specialized domain defanging function to properly handle domains
- Improved security of IOC handling while maintaining readability
- Fixed issue with domains showing unexpected protocol prefix in reports

### Version 0.1.9 (April 19, 2025)
- Added query metadata display in HTML reports
- Query reference, notes, frequency, priority, and tags are now shown in reports when available
- Improved report styling with metadata section and tag formatting
- Metadata section only appears when non-null metadata values exist

### Version 0.1.8 (April 19, 2025)
- Added URL and domain defanging for safer IOC handling
- Added customizable report username in configuration
- Updated report footer with GitHub project link and MalasadaTech branding
- Improved template to display the report generator's username

### Version 0.1.7 (April 19, 2025)
- Added dark mode support to HTML reports
- Implemented theme toggle with user preference memory
- Reports now automatically use system preferences for initial theme

### Version 0.1.6 (April 19, 2025)
- Added Base64 embedding of PNG screenshots in HTML reports
- Reports are now standalone files with no external dependencies
- Maintained backward compatibility with file references as fallback

### Version 0.1.5 (April 19, 2025)
- Added query metadata options: reference, notes, frequency, priority, and tags
- Enhanced query listing to display all metadata with improved formatting
- Updated documentation with explanation of hypothetical example queries

### Version 0.1.4 (April 19, 2025)
- Modified lookback logic to prioritize `last_run` timestamp before falling back to `default_days`
- Improved console output to show which lookback method is being used for each query

### Version 0.1.3 (April 19, 2025)
- Added automatic updating of `last_run` timestamp for each query after it is run
- Queries now track when they were last executed for better monitoring

### Version 0.1.2 (April 19, 2025)
- Added configurable default look-back period via `default_days` in config
- Query results now automatically use the default look-back period if `--days` flag is not specified

### Version 0.1.1 (April 18, 2025)
- Added `-d/--days` flag to limit search results to a specific number of days
- Improved console output to show number of results found

### Version 0.1.0 (April 18, 2025)
- Initial release
- Support for urlscan.io API queries
- HTML report generation with screenshots
- Command-line interface for running queries

## Roadmap

### Short-term (1-3 months)
- ✓ Add date filtering to only show results since last check
- ✓ Prioritize using `last_run` timestamp before falling back to `default_days`
- ✓ Add query metadata options (reference, notes, frequency, priority, tags)
- ✓ Add query groups for organizing related queries and generating comprehensive reports
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
