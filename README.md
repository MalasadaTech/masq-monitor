# Masquerade Monitor

A Python application to help automate monitoring for website masquerades using urlscan.io and other search platforms.

## Overview

Masquerade Monitor can help you track potential phishing campaigns (or other campaigns) by searching for websites mimicking legitimate brands. The tool queries search platforms for new scans that match your monitoring criteria, saving the results as HTML reports with thumbnail previews.

The basic idea:
It takes a list of monitoring pivots, and performs API calls to check if there is anything new since the last check.

It currently supports urlscan.io requests and the Silent Push API (as of April 2025, the results rendering is not yet optimized).

## Features

- Queries search platforms for potential masquerade websites (BYO-Queries)
- Multiple platform support (urlscan.io and Silent Push with both WHOIS and webscan data)
- Modular architecture with platform-specific client modules
- Modular template system with components for different report sections and result types
- Extensible template registry for automatically selecting the right template for each result type
- Saves screenshots of detected sites
- Generates standalone HTML reports with embedded screenshots
- Automatically extracts and saves IOCs (Indicators of Compromise) for both urlscan and Silent Push results
- Flexible IOC extraction supporting varied result formats from different endpoints
- CSV and JSON export of extracted IOCs (domains, IPs, URLs, etc.)
- Dedicated report generation module separated from main application logic
- Includes query metadata (reference, notes, frequency, priority, tags) in reports
- Supports TLP (Traffic Light Protocol) classification for information sharing control
- Supports query groups for organizing related queries and generating comprehensive reports
- Allows hierarchical organization with nested query groups
- Dark mode support with user preference memory
- Interactive image viewer for examining thumbnails in full-screen mode
- Tracks the last run timestamp for each query
- Supports custom lookback periods for searches
- Defangs IOCs (URLs and domains) in reports for safer sharing
- Platform-independent saving and loading of results for testing and development
- Customizable report username
- Branded footer with project links
- API keys stored in .env file for better security
- Automatic data type detection for Silent Push results (WHOIS vs webscan)
- Specialized report formatting for different data types
- Support for all Silent Push API endpoints with configurable endpoint parameter

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

By default, IOCs (domains, IPs, URLs, etc.) are automatically extracted from the results and saved to CSV files.

### Run a Query Group

```
python masq_monitor.py --query-group usaa-monitoring
```

Query groups run multiple related queries and create a combined report with sections for each query. IOCs from all queries in the group are consolidated and saved.

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

### Disable IOC Extraction

If you don't want to save IOCs to CSV files, you can disable this feature:

```
python masq_monitor.py --query usaa-domain --no-iocs
```

## Configuration

The configuration file can be in either JSON or YAML format. Use `.json` or `.yaml`/`.yml` file extension to specify the format:

### JSON Format

```json
{
    "output_directory": "output",
    "default_days": 7,
    "report_username": "Your Name",
    "default_tlp_level": "clear",
    "default_template_path": "templates/report_template.html",
    "queries": {
        // query configurations...
    }
}
```

### YAML Format

```yaml
output_directory: output
default_days: 7
report_username: Your Name
default_tlp_level: clear
default_template_path: templates/report_template.html
queries:
  # query configurations...
```

When creating your configuration file, you can choose either format:
```
cp config.example.json config.json
# OR
cp config.example.yaml config.yaml
```

YAML format provides a more readable structure for complex configurations, especially for nested query properties and is recommended for easier maintenance as your monitoring queries grow.

### Configuration Options

- `output_directory`: Directory to store reports and screenshots.
- `default_days`: Default number of days to limit the search to if no `last_run` timestamp exists and the `--days` flag is not specified.
- `report_username`: Your name or username to be displayed in generated reports.
- `default_template_path`: The default template to use for all queries that don't have a specific template.
- `queries`: A map of named queries to execute against search platforms.
  - `platform`: Search platform to use for this query. Currently supported: "urlscan", "silentpush". Defaults to "urlscan" if not specified.
  - `query`: The search query string formatted for the specified platform.
  - `endpoint`: (Silent Push only) API endpoint to use. Should start with a leading slash (e.g., "/explore/domain/search"). If not specified, defaults to "/explore/scandata/search/raw" for scandata queries.
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

### Silent Push Query Configuration

For Silent Push queries, you can use any of the available API endpoints by specifying the `endpoint` parameter in your query configuration:

```json
{
  "silentpush-domain-search": {
    "platform": "silentpush",
    "endpoint": "/explore/domain/search",
    "query": "domain=example.com",
    "description": "Search for domains matching example.com"
  },
  "silentpush-domain-info": {
    "platform": "silentpush",
    "endpoint": "/explore/domain/domaininfo/example.com",
    "query": "",
    "description": "Get detailed information about example.com"
  },
  "silentpush-scandata": {
    "platform": "silentpush",
    "query": "domain=*phish*",
    "description": "Search for phishing domains in scandata (using default endpoint)"
  }
}
```

If no endpoint is specified for a Silent Push query, the system will default to `/explore/scandata/search/raw`, which is used for general scandata searches.

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
    iocs/
      query-name_YYYYMMDD_HHMMSS_all_iocs.csv
      query-name_YYYYMMDD_HHMMSS_domains.csv
      query-name_YYYYMMDD_HHMMSS_ips.csv
      query-name_YYYYMMDD_HHMMSS_urls.csv
      query-name_YYYYMMDD_HHMMSS_iocs.json
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
    iocs/
      group-name_combined_YYYYMMDD_HHMMSS_all_iocs.csv
      group-name_combined_YYYYMMDD_HHMMSS_domains.csv
      group-name_combined_YYYYMMDD_HHMMSS_iocs.json
      ...
```

The HTML reports are self-contained files with all screenshots embedded as Base64-encoded images, allowing them to be shared or archived as single files without external dependencies.

## IOC Extraction

Masq Monitor automatically extracts Indicators of Compromise (IOCs) from search results for both urlscan and Silent Push platforms. This feature is enabled by default and extracts the following types of indicators:

- Domains
- IP addresses
- URLs
- Page titles
- Server details
- Email addresses (Silent Push)
- Registrars (Silent Push)
- Nameservers (Silent Push)
- Organizations (Silent Push)

IOCs are saved to CSV files in an "iocs" directory within each query's output folder. The following files are generated:

- `all_iocs.csv`: Contains all IOCs in a single file with columns for IOC type, value, and scan ID
- Individual type files (e.g., `domains.csv`, `ips.csv`) that contain just that specific IOC type
- `iocs.json`: A complete JSON representation of all extracted IOCs

For query groups, a consolidated set of IOCs from all member queries is also generated.

To disable IOC extraction, use the `--no-iocs` flag when running a query.

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
- ✓ Implement Silent Push API integration with both WHOIS and webscan data handling
- ✓ Implement IOC extraction and saving for both urlscan and Silent Push
- ✓ Add ability to export results to CSV/JSON
- Implement email notifications for new findings
- Support for custom report templates

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
