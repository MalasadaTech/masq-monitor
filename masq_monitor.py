#!/usr/bin/env python3

import os
import json
import time
import argparse
import datetime
import requests
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import jinja2
import re
from urllib.parse import urlparse
from dotenv import load_dotenv
from urlscan_client import UrlscanClient
from silentpush_client import SilentPushClient
from generate_report import ReportGenerator

class MasqMonitor:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        # Load environment variables from .env file
        load_dotenv()
        self.config = self._load_config()
        self.urlscan_api_key = self._load_api_key("URLSCAN_API_KEY")
        self.silentpush_api_key = self._load_api_key("SILENTPUSH_API_KEY")
        
        # Initialize API clients
        self.urlscan_client = UrlscanClient(api_key=self.urlscan_api_key)
        self.silentpush_client = SilentPushClient(api_key=self.silentpush_api_key)
        
        self.output_dir = Path(self.config.get("output_directory", "output"))
        self.output_dir.mkdir(exist_ok=True)
        self.tlp_levels = ["clear", "white", "green", "amber", "red"]
        # Initialize combined results storage for query groups
        self.group_results = {}
        
        # Initialize the report generator
        self.report_generator = ReportGenerator(self.config, self.output_dir)

    def _load_config(self):
        """Load configuration from the config file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file not found at {self.config_path}.")
            print("Please create it based on config.example.json.")
            exit(1)
        except json.JSONDecodeError:
            print(f"Error parsing the config file at {self.config_path}.")
            exit(1)

    def _load_api_key(self, key_name):
        """Load API key from environment variables."""
        # Get the API key from environment variables
        api_key = os.getenv(key_name)
        if not api_key:
            print(f"No API key found in environment variables for {key_name}.")
            print(f"Please create a .env file with {key_name}.")
            print("You can continue without an API key, but some features may be limited.")
            return ""
        return api_key

    def _save_config(self):
        """Save the updated configuration to the config file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving the config file: {e}")

    def _defang_domain(self, domain):
        """Defang a domain to make it safe for sharing."""
        return self.report_generator._defang_domain(domain)

    def _defang_url(self, url):
        """Defang a URL to make it safe for sharing."""
        return self.report_generator._defang_url(url)

    def run_query(self, query_name, days=None, tlp_level=None):
        """Run a specific query from the configuration.
        
        Args:
            query_name: Name of the query to run from config
            days: Optional. Number of days to limit the search to (from today)
                 If not provided, uses last_run timestamp or falls back to default_days
            tlp_level: Optional. TLP level to apply to this report
                      If not provided, uses query default or global default
                      
        Returns:
            List of results from the query
        """
        if query_name not in self.config["queries"]:
            print(f"Query '{query_name}' not found in configuration.")
            return []
        
        query_config = self.config["queries"][query_name]
        
        # Determine the appropriate TLP level
        report_tlp = self.report_generator.determine_tlp_level(query_name, tlp_level)
        print(f"Report TLP level: {report_tlp}")
        
        # Check the platform for this query
        platform = query_config.get("platform", "urlscan")
        if platform not in ["urlscan", "silentpush"]:
            print(f"Warning: Invalid platform '{platform}' for query '{query_name}'. Defaulting to 'urlscan'.")
            platform = "urlscan"
        
        print(f"Using platform: {platform}")
        
        # Get the endpoint for Silent Push queries
        endpoint = None
        is_scandata_query = True  # Default assumption for backward compatibility
        if platform == "silentpush":
            endpoint = query_config.get("endpoint")
            # Check if this is a scandata query (either using default endpoint or explicitly set to scandata endpoint)
            if endpoint:
                is_scandata_query = "scandata" in endpoint
            else:
                # Using default endpoint which is scandata
                is_scandata_query = True
                endpoint = "/explore/scandata/search/raw"
            print(f"Using endpoint: {endpoint}")
            print(f"Is scandata query: {is_scandata_query}")
        
        # Create the query string, adding date filter based on last_run or days parameter
        query_string = query_config["query"]
        
        # Determine the lookback period
        if days is not None:
            # Explicit days parameter takes precedence
            date_from = datetime.datetime.now() - datetime.timedelta(days=days)
            if platform == "silentpush" and is_scandata_query:
                # Format as YYYY-MM-DDTHH:MM:SSZ for Silent Push scandata queries
                date_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
                query_string = f"{query_string} AND scan_date >= \"{date_from_str}\""
                print(f"Running query: {query_name} (limited to {days} days from {date_from_str})")
            elif platform == "silentpush":
                # For non-scandata Silent Push queries, don't add date filter
                print(f"Running query: {query_name} (date filtering not applicable for this endpoint)")
            else:
                # Format as YYYY-MM-DD for urlscan.io
                date_from_str = date_from.strftime("%Y-%m-%d")
                query_string = f"{query_string} AND date:>={date_from_str}"
                print(f"Running query: {query_name} (limited to {days} days from {date_from_str})")
        elif "last_run" in query_config and query_config["last_run"]:
            # Use last run time if available
            try:
                last_run = datetime.datetime.fromisoformat(query_config["last_run"])
                if platform == "silentpush" and is_scandata_query:
                    # Format as YYYY-MM-DDTHH:MM:SSZ for Silent Push scandata queries
                    date_from_str = last_run.strftime("%Y-%m-%dT%H:%M:%SZ")
                    query_string = f"{query_string} AND scan_date >= \"{date_from_str}\""
                    print(f"Running query: {query_name} (from last run on {date_from_str})")
                elif platform == "silentpush":
                    # For non-scandata Silent Push queries, don't add date filter
                    print(f"Running query: {query_name} (date filtering not applicable for this endpoint)")
                else:
                    # Format as YYYY-MM-DD for urlscan.io
                    date_from_str = last_run.strftime("%Y-%m-%d")
                    query_string = f"{query_string} AND date:>={date_from_str}"
                    print(f"Running query: {query_name} (from last run on {date_from_str})")
            except (ValueError, TypeError):
                # Fall back to default_days if last_run is invalid
                default_days = self.config.get("default_days")
                if default_days is not None:
                    date_from = datetime.datetime.now() - datetime.timedelta(days=default_days)
                    if platform == "silentpush" and is_scandata_query:
                        # Format as YYYY-MM-DDTHH:MM:SSZ for Silent Push scandata queries
                        date_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
                        query_string = f"{query_string} AND scan_date >= \"{date_from_str}\""
                        print(f"Running query: {query_name} (limited to default {default_days} days from {date_from_str})")
                    elif platform == "silentpush":
                        # For non-scandata Silent Push queries, don't add date filter
                        print(f"Running query: {query_name} (date filtering not applicable for this endpoint)")
                    else:
                        # Format as YYYY-MM-DD for urlscan.io
                        date_from_str = date_from.strftime("%Y-%m-%d")
                        query_string = f"{query_string} AND date:>={date_from_str}"
                        print(f"Running query: {query_name} (limited to default {default_days} days from {date_from_str})")
                else:
                    print(f"Running query: {query_name} (no date filter)")
        else:
            # If no last_run and no days specified, try using default_days
            default_days = self.config.get("default_days")
            if default_days is not None:
                date_from = datetime.datetime.now() - datetime.timedelta(days=default_days)
                if platform == "silentpush" and is_scandata_query:
                    # Format as YYYY-MM-DDTHH:MM:SSZ for Silent Push scandata queries
                    date_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
                    query_string = f"{query_string} AND scan_date >= \"{date_from_str}\""
                    print(f"Running query: {query_name} (limited to default {default_days} days from {date_from_str})")
                elif platform == "silentpush":
                    # For non-scandata Silent Push queries, don't add date filter
                    print(f"Running query: {query_name} (date filtering not applicable for this endpoint)")
                else:
                    # Format as YYYY-MM-DD for urlscan.io
                    date_from_str = date_from.strftime("%Y-%m-%d")
                    query_string = f"{query_string} AND date:>={date_from_str}"
                    print(f"Running query: {query_name} (limited to default {default_days} days from {date_from_str})")
            else:
                print(f"Running query: {query_name} (no date filter)")
        
        # Create a unique output directory for this run
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"{query_name}_{timestamp}"
        run_dir.mkdir(exist_ok=True)
        
        # Save the images directory
        img_dir = run_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        # Select the appropriate client based on platform
        client = None
        if platform == "silentpush":
            client = self.silentpush_client
            # Execute the Silent Push query with the endpoint parameter
            results = client.execute_query(query_string, endpoint=endpoint)
        else:  # Default to urlscan
            client = self.urlscan_client
            # Execute the urlscan query (no endpoint parameter needed)
            results = client.execute_query(query_string)
        
        if results:
            # Download thumbnails for each result
            for i, result in enumerate(results):
                if "task" in result and "uuid" in result["task"]:
                    uuid = result["task"]["uuid"]
                    screenshot_path = img_dir / f"{uuid}.png"
                    client.download_screenshot(uuid, screenshot_path)
                    result["local_screenshot"] = f"images/{uuid}.png"
                    result["base64_screenshot"] = client.encode_image_to_base64(screenshot_path)
                
                # Defang all URLs and domains in the result
                if "page" in result and "url" in result["page"]:
                    result["defanged_url"] = self._defang_url(result["page"]["url"])
                if "page" in result and "domain" in result["page"]:
                    result["defanged_domain"] = self._defang_domain(result["page"]["domain"])
            
            # Generate the HTML report with the timestamp
            self.report_generator.generate_html_report(results, query_name, run_dir, report_tlp, timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print(f"Report generated in {run_dir} with {len(results)} results")
        else:
            print(f"No results found for query '{query_name}'")
        
        # Update the last_run timestamp
        current_time = datetime.datetime.now().isoformat()
        self.config["queries"][query_name]["last_run"] = current_time
        self._save_config()
        
        return results

    def run_query_group(self, group_name, days=None, tlp_level=None):
        """Run a group of queries and generate a combined report.
        
        Args:
            group_name: Name of the query group to run
            days: Optional. Number of days to limit the search to
            tlp_level: Optional. TLP level to apply to this report
            
        Returns:
            Dictionary with results from each query in the group
        """
        if group_name not in self.config["queries"]:
            print(f"Query group '{group_name}' not found in configuration.")
            return {}
            
        group_config = self.config["queries"][group_name]
        
        # Verify this is actually a query group
        if not group_config.get("type") == "query_group":
            print(f"'{group_name}' is not a query group. Use run_query instead.")
            return {}
            
        # Get the list of queries in this group
        query_names = group_config.get("queries", [])
        if not query_names:
            print(f"Query group '{group_name}' does not contain any queries.")
            return {}
            
        print(f"Running query group '{group_name}' with {len(query_names)} queries")
        
        # Initialize results dictionary
        self.group_results[group_name] = {}
        
        # Run each query in the group
        for query_name in query_names:
            # Check if this is a nested query group
            if query_name in self.config["queries"] and self.config["queries"][query_name].get("type") == "query_group":
                print(f"Running nested query group '{query_name}'")
                # Run the nested query group
                nested_results = self.run_query_group(query_name, days=days, tlp_level=tlp_level)
                self.group_results[group_name][query_name] = {
                    "type": "query_group",
                    "results": nested_results
                }
            else:
                # Run individual query
                print(f"Running query '{query_name}' as part of group '{group_name}'")
                results = self.run_query(query_name, days=days, tlp_level=tlp_level)
                self.group_results[group_name][query_name] = results
                
        # Generate a combined report after all queries have run
        self.report_generator.generate_group_report(group_name, self.group_results[group_name], tlp_level)
        
        # Update the last_run timestamp for the group
        current_time = datetime.datetime.now().isoformat()
        self.config["queries"][group_name]["last_run"] = current_time
        self._save_config()
        
        return self.group_results[group_name]

    def save_results(self, query_name, results, timestamp=None, platform=None):
        """Save platform results to a JSON file for testing and caching.
        
        Args:
            query_name: Name of the query
            results: List of result objects from the platform
            timestamp: Optional timestamp to use in the filename
            platform: Optional platform name for the filename (defaults to using query config)
        
        Returns:
            Path to the saved results file
        """
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # If platform is not specified, try to get it from the query config
        if platform is None and query_name in self.config["queries"]:
            platform = self.config["queries"][query_name].get("platform", "urlscan")
            
        # Create a directory for saved results if it doesn't exist
        cache_dir = Path("cached_results")
        cache_dir.mkdir(exist_ok=True)
        
        # Create a filename with the query name and timestamp
        cache_file = cache_dir / f"{query_name}_{timestamp}_results.json"
        
        # Save the results to a JSON file
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        print(f"Saved {platform} results to {cache_file}")
        return cache_file
        
    def load_results(self, file_path):
        """Load saved platform results from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing saved results
        
        Returns:
            List of result objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
                
            print(f"Loaded {len(results)} results from {file_path}")
            return results
        except Exception as e:
            print(f"Error loading saved results: {e}")
            return []

    # Legacy method for backward compatibility
    def save_urlscan_results(self, query_name, results, timestamp=None):
        """Legacy method - use save_results instead.
        
        Args:
            query_name: Name of the query
            results: List of urlscan result objects
            timestamp: Optional timestamp to use in the filename
        
        Returns:
            Path to the saved results file
        """
        return self.save_results(query_name, results, timestamp, platform="urlscan")
        
    # Legacy method for backward compatibility
    def load_urlscan_results(self, file_path):
        """Legacy method - use load_results instead.
        
        Args:
            file_path: Path to the JSON file containing saved results
        
        Returns:
            List of urlscan result objects
        """
        return self.load_results(file_path)

    def list_queries(self):
        """List all available queries from the configuration."""
        if "queries" not in self.config:
            print("No queries defined in the configuration.")
            return
        
        print("\nAvailable queries:")
        print("==================")
        for name, details in self.config["queries"].items():
            description = details.get('description', 'No description')
            frequency = details.get('frequency', 'Not specified')
            priority = details.get('priority', 'Not specified')
            platform = details.get('platform', 'urlscan')
            tags = ", ".join(details.get('tags', [])) or "None"
            
            # Determine if this is a query or query group
            is_query_group = details.get('type') == 'query_group'
            query_type = "Query Group" if is_query_group else "Query"
            
            print(f"\n{name}:")
            print(f"  Type: {query_type}")
            print(f"  Description: {description}")
            
            if is_query_group:
                # For query groups, display the list of queries
                queries_list = details.get('queries', [])
                if queries_list:
                    print(f"  Queries: {', '.join(queries_list)}")
                else:
                    print("  Queries: None")
            else:
                # For regular queries, display the query string and platform
                query_string = details.get('query', 'No query string defined')
                print(f"  Query: {query_string}")
                print(f"  Platform: {platform}")
            
            print(f"  Suggested Frequency: {frequency}")
            print(f"  Priority: {priority}")
            print(f"  Tags: {tags}")
            
            if "reference" in details:
                print(f"  Reference: {details['reference']}")
            
            if "notes" in details:
                print(f"  Notes: {details['notes']}")
            
            last_run = details.get("last_run")
            if last_run:
                print(f"  Last Run: {last_run}")
            else:
                print("  Last Run: Never")

    def test_report_generation(self, query_name, cached_results_path, tlp_level=None):
        """Generate a test report using saved results without querying APIs.
        
        Args:
            query_name: Name of the query for metadata
            cached_results_path: Path to JSON file with saved platform results
            tlp_level: Optional TLP level for the report
            
        Returns:
            Path to the generated report
        """
        print(f"Generating test report for '{query_name}' using cached results")
        
        # Load the saved results using the platform-agnostic method
        results = self.load_results(cached_results_path)
        if not results:
            print("No results loaded, cannot generate report")
            return None
            
        # Generate the test report using the report generator
        return self.report_generator.test_report_generation(query_name, results, tlp_level)

def main():
    parser = argparse.ArgumentParser(description="Monitor for masquerades using multiple platforms")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--list", action="store_true", help="List available queries")
    parser.add_argument("--query", help="Run a specific query")
    parser.add_argument("--query-group", help="Run a specific query group")
    parser.add_argument("--all", action="store_true", help="Run all queries")
    parser.add_argument("--all-groups", action="store_true", help="Run all query groups")
    parser.add_argument("-d", "--days", type=int, help="Limit results to the specified number of days")
    parser.add_argument("--tlp", choices=["clear", "white", "green", "amber", "red"], 
                        help="Set the TLP level for the report")
    
    # Add testing options
    parser.add_argument("--save-results", action="store_true", 
                        help="Save results to a JSON file for testing")
    parser.add_argument("--cached-results", 
                        help="Path to a JSON file with saved results")
    
    args = parser.parse_args()
    
    monitor = MasqMonitor(config_path=args.config)
    
    # Use default_days from config if --days not specified
    days = args.days if args.days is not None else monitor.config.get("default_days")
    
    if args.list:
        monitor.list_queries()
    elif args.query and args.cached_results:
        # Generate test report using cached results
        monitor.test_report_generation(args.query, args.cached_results, tlp_level=args.tlp)
    elif args.query:
        # Run query and optionally save the results
        results = monitor.run_query(args.query, days=days, tlp_level=args.tlp)
        if args.save_results and results:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            monitor.save_results(args.query, results, timestamp)
    elif args.query_group:
        # Run a query group
        group_results = monitor.run_query_group(args.query_group, days=days, tlp_level=args.tlp)
        # Save results from each query if requested
        if args.save_results and group_results:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            for query_name, query_results in group_results.items():
                if isinstance(query_results, list) and query_results:  # Only save actual query results, not nested groups
                    monitor.save_results(query_name, query_results, timestamp)
    elif args.all:
        # Run all individual queries (not query groups)
        for query_name, query_data in monitor.config.get("queries", {}).items():
            if query_data.get("type") != "query_group":
                results = monitor.run_query(query_name, days=days, tlp_level=args.tlp)
                if args.save_results and results:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    monitor.save_results(query_name, results, timestamp)
    elif args.all_groups:
        # Run all query groups
        for query_name, query_data in monitor.config.get("queries", {}).items():
            if query_data.get("type") == "query_group":
                group_results = monitor.run_query_group(query_name, days=days, tlp_level=args.tlp)
                # Save results from each query if requested
                if args.save_results and group_results:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    for sub_query_name, query_results in group_results.items():
                        if isinstance(query_results, list) and query_results:  # Only save actual query results, not nested groups
                            monitor.save_results(sub_query_name, query_results, timestamp)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()