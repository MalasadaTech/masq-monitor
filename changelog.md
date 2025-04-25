# Changelog

## April 24, 2025
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