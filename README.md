# Masquerade Monitor

A Python application to automate monitoring for website masquerades using urlscan.io.

## Overview

Masquerade Monitor helps you track potential phishing attempts by searching for websites mimicking legitimate brands. The tool periodically queries urlscan.io for new scans that match your monitoring criteria, saving the results as HTML reports with thumbnail previews.

The basic idea:
It takes a list of monitoring pivots, and performs API calls to check if there is anything new since the last check.

It currently supports urlscan.io requests with plans to expand to other sources in the future. urlscan.io is used because they allow free API searches that should suffice for basic monitoring.

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

4. Edit `config.json` with your urlscan.io API key and desired monitoring queries.

## Usage

### List Available Queries

```
python masq_monitor.py --list
```

### Run a Specific Query

```
python masq_monitor.py --query usaa-domain
```

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

You can also limit all queries to a timeframe:

```
python masq_monitor.py --all -d 30
```

### Specify a Custom Config File

```
python masq_monitor.py --config my_custom_config.json --all
```

## Configuration

The configuration file is in JSON format with the following structure:

```json
{
    "api_key": "YOUR_URLSCAN_API_KEY",
    "output_directory": "output",
    "default_days": 7,
    "queries": {
        "query-name": {
            "description": "Description of the query",
            "query": "urlscan.io search query syntax",
            "last_run": null
        }
    }
}
```

### Configuration Options

- `api_key`: Your urlscan.io API key for accessing the API.
- `output_directory`: Directory to store reports and screenshots.
- `default_days`: Default number of days to limit the search to if no `last_run` timestamp exists and the `--days` flag is not specified.
- `queries`: A map of named queries to execute against urlscan.io.
  - `last_run`: Timestamp of when the query was last executed. Used to limit searches to only new results since the last run.

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

The tool generates HTML reports in the output directory with the following structure:

```
output/
  query-name_YYYYMMDD_HHMMSS/
    report.html
    images/
      [scan-uuid1].png
      [scan-uuid2].png
      ...
```

## Changelog

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
