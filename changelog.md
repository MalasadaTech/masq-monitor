# Changelog

## May 7, 2025
- Enhanced group report template to match the styling of individual reports
- Added proper `meta` and `metadata-section` elements to group reports for visual consistency
- Implemented metadata sections for both the group overview and individual queries within group reports
- Ensured TLP markings appear consistently in both group and individual reports
- Fixed group report appearance to maintain the same professional format as individual reports
- Improved group report organization with clearer query sections and result numbering
- Added consistent styling for query descriptions, references, notes, and other metadata elements
- Enhanced Silent Push results visualization by refactoring to use table-based display for all result types
- Consolidated all Silent Push templates to use silentpush_domainsearch.html as the main template
- Implemented specialized table layouts for different Silent Push data types (webscan, whois, domain search)
- Added dynamic card headers that adapt based on the detected data type
- Created a flexible generic display mode for uncommon result types
- Maintained all interactive features (resizable/draggable columns, tooltips) across all result types
- Improved maintenance by centralizing template logic in a single file
- Made all Silent Push results consistent with the same tabular display format
- Optimized template selection logic to always use silentpush_domainsearch.html for any Silent Push platform result
- Enhanced readability with consistent column formatting across different result types

## May 6, 2025
- Fixed SilentPush report generation by adding missing data type determination methods
- Implemented `_determine_silentpush_data_type` method to properly identify webscan, whois, and domain search results
- Added `_process_silentpush_webscan` method with proper raw record preservation for template access
- Added `_process_silentpush_whois` method with date formatting and domain defanging
- Enhanced Silent Push rendering for search types other than webscan and whois
- Implemented consolidated table view for displaying multiple non-webscan/whois results in a single card
- Added proper indexing for table rows with numbered entries
- Added horizontal scrolling with sticky headers and index column for better navigation of large tables
- Fixed table width to stay within container boundaries
- Improved user experience with floating headers that stay visible during vertical scrolling
- Added visual separation between table headers and content for better readability
- Optimized table display for both light and dark themes
- Enhanced domain search tables with adjustable column widths via drag handles
- Added column reordering via drag and drop functionality
- Implemented text truncation with ellipsis for narrow columns
- Added tooltips to show full content when hovering over truncated cells
- Ensured table columns can be independently resized without affecting other columns
- Added horizontal scrollbar when table width exceeds container
- Improved resize handles with visual indicators to prevent accidental column dragging

## May 1, 2025
- Fixed Silent Push API integration to only apply scan_date filter to scandata queries
- Added intelligent endpoint detection to determine if a query is using the scandata endpoint
- Added better logging to show which Silent Push endpoints are being used
- Improved error handling for non-scandata Silent Push API endpoints
- Updated query processing to preserve backwards compatibility
- Fixed domain search endpoint integration by using GET requests with URL parameters instead of POST requests
- Added support for different request formats required by different Silent Push API endpoints
- Implemented parameter parsing for endpoints that use URL query parameters instead of request bodies

## April 30, 2025
- Implemented Silent Push Domain Search capability
- Added support for all Silent Push API endpoints via configurable `endpoint` parameter
- Modified SilentPushClient to use the new API base URL structure (`/api/v1/merge-api`)
- Added proper handling of endpoints with leading slashes to match documentation
- Updated MasqMonitor to pass the endpoint parameter to SilentPushClient
- Default endpoint set to `/explore/scandata/search/raw` when none specified
- Updated documentation to explain endpoint configuration for Silent Push queries
- Fixed URL construction to ensure proper formatting regardless of how endpoints are specified

## April 27, 2025
- Added result numbering to reports to simplify referencing specific results during analysis
- Positioned numbers in the top-left corner of each result card for clear visibility
- Ensured consistent numbering across different result types (URLScan, SilentPush WHOIS, etc.)
- Added proper padding to prevent number overlapping with screenshots and content
- Implemented numbered results for both individual query reports and group reports
- Maintained styling consistency between light and dark themes for result numbers
- Implemented modular template system with components for easier maintenance and extension
- Created separate template components for different parts of the report (header, footer, styles, etc.)
- Added platform-specific templates for different result types
- Implemented template registry for automatic selection of appropriate template based on result type
- Improved code organization with separate template utility functions
- Added support for easily adding new result type templates in the future
- Enhanced template inheritance for more consistent styling across different result types
- Refactored template loading in generate_report.py to use the new modular system
- Maintained backward compatibility with existing report functionality

## April 26, 2025
- Improved Silent Push integration to properly handle multiple data types (webscan and WHOIS)
- Added automatic detection of Silent Push data types based on record fields
- Added specialized webscan result rendering in reports with organized sections for website, SSL, and GeoIP data
- Fixed ISO 8601 date formatting with T and Z modifiers for Silent Push queries (scan_date field)
- Enhanced report templates to properly display different types of Silent Push results
- Refactored report generation code into a separate file (`generate_report.py`)
- Created a dedicated `ReportGenerator` class to handle all report generation functionality
- Improved code organization and maintainability by separating concerns
- Reduced the size of the main `masq_monitor.py` file
- Updated `MasqMonitor` class to delegate report generation to the `ReportGenerator` instance

## April 25, 2025
- Added Silent Push WHOIS scan query capability.

## April 24, 2025
- Refactored `save_urlscan_results` into platform-independent `save_results` function
- Added platform-independent `load_results` function to work with any API platform
- Maintained backward compatibility with legacy `save_urlscan_results` and `load_urlscan_results` methods
- Updated main function to use the new platform-agnostic saving/loading methods with `--save-results` and `--cached-results` flags
- Refactored `test_report_generation` to use platform-independent functions
- Improved error handling for cached results
- Refactored urlscan-specific code into separate client modules (`urlscan_client.py` and `silentpush_client.py`) to prepare for Silent Push API implementation
- Improved code organization with platform-specific client classes
- Modified masq_monitor.py to use the appropriate client based on the "platform" field
- Added placeholder implementation for Silent Push API client
- Added "platform" property to query objects to support multiple search platforms
- Added support for specifying "urlscan" or "silentpush" as the query platform
- Modified code to handle platform-specific query execution
- Updated example configuration with platform property for all queries
- Migrated API key storage from JSON to .env file for improved security
- Added python-dotenv integration for loading environment variables
- Removed all references to api_key.json while maintaining backward compatibility
- Added .env and related files to .gitignore
- Created .env.example template file for easier setup
- Updated documentation for new API key configuration approach
- Fixed error when listing queries with query groups by safely accessing query attributes
- Enhanced the query listing display to show query types (Query vs Query Group)
- Improved display of query groups to show member queries instead of query strings
- Better formatting for `--list` command output with consistent structure
- Refactored result-card link in template from "URLScan Link:" to "Query Link:" for platform-agnostic labeling

## April 20, 2025
- Added support for query groups to organize related queries
- Implemented hierarchical query structure with nested query groups
- Added group report generation with sections for each individual query
- Group reports combine results from all queries with source tracking
- Added new command-line options for managing query groups
- Updated HTML template to properly display grouped results
- Added support for custom templates per query
- Added `default_template_path` config option to set the global default template
- Added `template_path` option per query to specify a custom template
- Improved error handling for template loading with fallback to default template
- Fixed TLP color rendering when printing reports to PDF
- Added CSS rules to ensure background colors are correctly displayed in PDF output
- Preserved dark theme when printing to PDF if dark theme was selected in the UI
- Enhanced print media queries for better PDF export support
- Added interactive image viewer to expand screenshots to full view when clicked
- Implemented close functionality via X button, clicking outside the image, or pressing the Escape key
- Enhanced user experience by providing better visualization of screenshot details
- Added TLP (Traffic Light Protocol) support for reports
- Implemented `query_tlp_level` to determine sensitivity of the query itself
- Added `default_tlp_level` to set classification for report content by default
- Added TLP level in report filenames for easier identification
- Report headers now display TLP classification with appropriate color coding
- Added command-line flag `--tlp` to override default TLP level when generating reports
- Fixed URL defanging to preserve filenames in their original form
- Added specialized domain defanging function to properly handle domains
- Improved security of IOC handling while maintaining readability
- Fixed issue with domains showing unexpected protocol prefix in reports

## April 19, 2025
- Added query metadata display in HTML reports
- Query reference, notes, frequency, priority, and tags are now shown in reports when available
- Improved report styling with metadata section and tag formatting
- Metadata section only appears when non-null metadata values exist
- Added URL and domain defanging for safer IOC handling
- Added customizable report username in configuration
- Updated report footer with GitHub project link and MalasadaTech branding
- Improved template to display the report generator's username
- Added dark mode support to HTML reports
- Implemented theme toggle with user preference memory
- Reports now automatically use system preferences for initial theme
- Added Base64 embedding of PNG screenshots in HTML reports
- Reports are now standalone files with no external dependencies
- Maintained backward compatibility with file references as fallback
- Added query metadata options: reference, notes, frequency, priority, and tags
- Enhanced query listing to display all metadata with improved formatting
- Updated documentation with explanation of hypothetical example queries
- Modified lookback logic to prioritize `last_run` timestamp before falling back to `default_days`
- Improved console output to show which lookback method is being used for each query
- Added automatic updating of `last_run` timestamp for each query after it is run
- Queries now track when they were last executed for better monitoring
- Added configurable default look-back period via `default_days` in config
- Query results now automatically use the default look-back period if `--days` flag is not specified

## April 18, 2025
- Added `-d/--days` flag to limit search results to a specific number of days
- Improved console output to show number of results found
- Initial release
- Support for urlscan.io API queries
- HTML report generation with screenshots
- Command-line interface for running queries