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
import re
from urllib.parse import urlparse
from dotenv import load_dotenv
from urlscan_client import UrlscanClient
from silentpush_client import SilentPushClient

class MasqMonitor:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        # Load environment variables from .env file
        load_dotenv()
        self.config = self._load_config()
        self.urlscan_api_key = self._load_api_key()
        
        # Initialize API clients
        self.urlscan_client = UrlscanClient(api_key=self.urlscan_api_key)
        # NOTE: Silent Push API key handling will need to be implemented in the future
        self.silentpush_client = SilentPushClient(api_key=None)
        
        self.output_dir = Path(self.config.get("output_directory", "output"))
        self.output_dir.mkdir(exist_ok=True)
        self.tlp_levels = ["clear", "white", "green", "amber", "red"]
        # Initialize combined results storage for query groups
        self.group_results = {}

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

    def _load_api_key(self):
        """Load API key from environment variables."""
        # Get the API key from environment variables
        api_key = os.getenv('URLSCAN_API_KEY')
        if not api_key:
            # Check if API key exists in config for backward compatibility
            legacy_api_key = self.config.get("api_key", "")
            if legacy_api_key:
                print("Using API key from config.json.")
                print("Consider moving your API key to a .env file for better security and sharing capabilities.")
                return legacy_api_key
            else:
                print("No API key found in environment variables.")
                print("Please create a .env file with URLSCAN_API_KEY.")
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
        if not domain:
            return ""
        
        # Replace dots with [.] in the domain
        defanged_domain = re.sub(r'\.', '[.]', domain)
        return defanged_domain

    def _defang_url(self, url):
        """Defang a URL to make it safe for sharing."""
        if not url:
            return ""
        
        # Parse the URL to separate domain from path
        parsed_url = urlparse(url)
        
        # Replace http:// with hxxp:// and https:// with hxxps://
        defanged_scheme = re.sub(r'http', 'hxxp', parsed_url.scheme)
        
        # Replace dots with [.] only in the netloc (domain) part
        defanged_netloc = re.sub(r'\.', '[.]', parsed_url.netloc)
        
        # Reconstruct the URL with defanged parts but keep the path intact
        defanged_url = f"{defanged_scheme}://{defanged_netloc}{parsed_url.path}"
        if parsed_url.query:
            defanged_url += f"?{parsed_url.query}"
        if parsed_url.fragment:
            defanged_url += f"#{parsed_url.fragment}"
            
        return defanged_url

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
        report_tlp = self._determine_tlp_level(query_name, tlp_level)
        print(f"Report TLP level: {report_tlp}")
        
        # Check the platform for this query
        platform = query_config.get("platform", "urlscan")
        if platform not in ["urlscan", "silentpush"]:
            print(f"Warning: Invalid platform '{platform}' for query '{query_name}'. Defaulting to 'urlscan'.")
            platform = "urlscan"
        
        print(f"Using platform: {platform}")
        
        # Create the query string, adding date filter based on last_run or days parameter
        query_string = query_config["query"]
        
        # Determine the lookback period
        if days is not None:
            # Explicit days parameter takes precedence
            date_from = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            query_string = f"{query_string} AND date:>={date_from}"
            print(f"Running query: {query_name} (limited to {days} days from {date_from})")
        elif "last_run" in query_config and query_config["last_run"]:
            # Use last run time if available
            try:
                last_run = datetime.datetime.fromisoformat(query_config["last_run"])
                # Format as YYYY-MM-DD for the urlscan.io date filter
                date_from = last_run.strftime("%Y-%m-%d")
                query_string = f"{query_string} AND date:>={date_from}"
                print(f"Running query: {query_name} (from last run on {date_from})")
            except (ValueError, TypeError):
                # Fall back to default_days if last_run is invalid
                default_days = self.config.get("default_days")
                if default_days is not None:
                    date_from = (datetime.datetime.now() - datetime.timedelta(days=default_days)).strftime("%Y-%m-%d")
                    query_string = f"{query_string} AND date:>={date_from}"
                    print(f"Running query: {query_name} (limited to default {default_days} days from {date_from})")
                else:
                    print(f"Running query: {query_name} (no date filter)")
        else:
            # If no last_run and no days specified, try using default_days
            default_days = self.config.get("default_days")
            if default_days is not None:
                date_from = (datetime.datetime.now() - datetime.timedelta(days=default_days)).strftime("%Y-%m-%d")
                query_string = f"{query_string} AND date:>={date_from}"
                print(f"Running query: {query_name} (limited to default {default_days} days from {date_from})")
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
        else:  # Default to urlscan
            client = self.urlscan_client
        
        # Execute the query using the selected client
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
            self._generate_html_report(results, query_name, run_dir, report_tlp, timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
        self._generate_group_report(group_name, tlp_level)
        
        # Update the last_run timestamp for the group
        current_time = datetime.datetime.now().isoformat()
        self.config["queries"][group_name]["last_run"] = current_time
        self._save_config()
        
        return self.group_results[group_name]
        
    def _generate_group_report(self, group_name, tlp_level=None):
        """Generate a combined HTML report for a query group.
        
        Args:
            group_name: Name of the query group
            tlp_level: Optional TLP level for the report
        """
        group_config = self.config["queries"][group_name]
        group_results = self.group_results.get(group_name, {})
        
        if not group_results:
            print(f"No results found for query group '{group_name}'")
            return
            
        # Determine the appropriate TLP level
        report_tlp = self._determine_tlp_level(group_name, tlp_level)
        print(f"Group report TLP level: {report_tlp}")
        
        # Create a unique output directory for this group report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"{group_name}_{timestamp}_group"
        run_dir.mkdir(exist_ok=True)
        
        # Create images directory
        img_dir = run_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        # Check if group has a specific template path
        template_path = group_config.get("template_path")
        
        # If no group-specific template, use the global default
        if not template_path:
            template_path = self.config.get("default_template_path", "templates/report_template.html")
            
        # Split template path into directory and filename
        template_dir = os.path.dirname(template_path)
        template_file = os.path.basename(template_path)
        
        # Create Jinja2 environment with the appropriate template directory
        env = Environment(loader=FileSystemLoader(template_dir if template_dir else "templates"))
        try:
            template = env.get_template(template_file)
        except Exception as e:
            print(f"Error loading template {template_path}: {e}")
            print("Falling back to default template")
            env = Environment(loader=FileSystemLoader("templates"))
            template = env.get_template("report_template.html")
        
        # Use the provided timestamp or generate current time
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Copy all screenshots to the group report directory
        # and create a flattened structure for all results to include in the report
        flattened_results = []
        query_sections = []
        
        for query_name, query_data in group_results.items():
            if isinstance(query_data, dict) and query_data.get("type") == "query_group":
                # Handle nested query groups
                query_config = self.config["queries"][query_name]
                query_sections.append({
                    "name": query_name,
                    "type": "query_group",
                    "config": query_config,
                    "results_count": self._count_total_results(query_data["results"])
                })
                # Recursively process nested group results
                self._process_nested_group_results(query_data["results"], flattened_results, img_dir)
            else:
                # Handle individual query results
                query_config = self.config["queries"][query_name]
                results = query_data
                
                # Add this query's section info
                query_sections.append({
                    "name": query_name,
                    "type": "query",
                    "config": query_config,
                    "results_count": len(results)
                })
                
                # Process individual query results
                for result in results:
                    if "base64_screenshot" in result:
                        # Copy screenshot to group report directory
                        if "task" in result and "uuid" in result["task"]:
                            uuid = result["task"]["uuid"]
                            dest_path = img_dir / f"{uuid}.png"
                            if "local_screenshot" in result:
                                # Update paths for the group report
                                orig_path = self.output_dir / result["local_screenshot"].replace("images/", "")
                                if os.path.exists(orig_path):
                                    with open(orig_path, "rb") as src_file:
                                        with open(dest_path, "wb") as dest_file:
                                            dest_file.write(src_file.read())
                            result["local_screenshot"] = f"images/{uuid}.png"
                    
                    # Add query name to the result for section identification in the template
                    result["source_query"] = query_name
                    flattened_results.append(result)
        
        # Generate the HTML report
        html_content = template.render(
            query_name=group_name,
            query_data=group_config,
            timestamp=current_timestamp,
            results=flattened_results,
            is_group_report=True,
            query_sections=query_sections,
            username=self.config.get("report_username", ""),
            tlp_level=report_tlp,
            debug=False
        )
        
        # Remove blank lines from HTML content
        html_content = "\n".join([line for line in html_content.split("\n") if line.strip()])
        
        # Extract the date/time group from the output directory
        dir_name = run_dir.name
        datetime_part = ""
        if "_" in dir_name:
            datetime_part = dir_name.split("_", 1)[1]
        
        # Include TLP level and datetime in the filename
        report_filename = f"report_{group_name}_{datetime_part}_TLP-{report_tlp}.html"
        with open(run_dir / report_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Group report generated in {run_dir} with {len(flattened_results)} total results")
        
    def _process_nested_group_results(self, nested_results, flattened_results, img_dir):
        """Process results from nested query groups.
        
        Args:
            nested_results: Results from a nested query group
            flattened_results: List to append flattened results to
            img_dir: Directory to copy screenshots to
        """
        for query_name, query_data in nested_results.items():
            if isinstance(query_data, dict) and query_data.get("type") == "query_group":
                # Recursively process nested groups
                self._process_nested_group_results(query_data["results"], flattened_results, img_dir)
            else:
                # Process individual query results
                results = query_data
                for result in results:
                    if "base64_screenshot" in result:
                        # Copy screenshot to group report directory
                        if "task" in result and "uuid" in result["task"]:
                            uuid = result["task"]["uuid"]
                            dest_path = img_dir / f"{uuid}.png"
                            if "local_screenshot" in result:
                                # Update paths for the group report
                                orig_path = self.output_dir / result["local_screenshot"].replace("images/", "")
                                if os.path.exists(orig_path):
                                    with open(orig_path, "rb") as src_file:
                                        with open(dest_path, "wb") as dest_file:
                                            dest_file.write(src_file.read())
                            result["local_screenshot"] = f"images/{uuid}.png"
                    
                    # Add query name to the result for section identification in the template
                    result["source_query"] = query_name
                    flattened_results.append(result)
                    
    def _count_total_results(self, group_results):
        """Count total number of results in a query group, including nested groups.
        
        Args:
            group_results: Results dictionary from a query group
            
        Returns:
            Total count of individual query results
        """
        count = 0
        for query_name, query_data in group_results.items():
            if isinstance(query_data, dict) and query_data.get("type") == "query_group":
                # Recursively count nested group results
                count += self._count_total_results(query_data["results"])
            else:
                # Count individual query results
                count += len(query_data)
        return count

    def _determine_tlp_level(self, query_name, requested_tlp=None):
        """Determine the appropriate TLP level for the report.
        
        Args:
            query_name: Name of the query
            requested_tlp: Optional TLP level requested by the user
            
        Returns:
            The appropriate TLP level to use
        """
        # If user explicitly requested a TLP level, use that
        if requested_tlp and requested_tlp in self.tlp_levels:
            return requested_tlp
            
        # Otherwise check query default
        query_config = self.config["queries"].get(query_name, {})
        query_default = query_config.get("default_tlp_level")
        if query_default and query_default in self.tlp_levels:
            return query_default
            
        # Fall back to global default
        global_default = self.config.get("default_tlp_level", "clear")
        if global_default in self.tlp_levels:
            return global_default
            
        # Ultimate fallback
        return "clear"
        
    def _get_highest_tlp_level(self, query_name):
        """Determine the highest TLP level in the query metadata.
        
        Args:
            query_name: Name of the query
            
        Returns:
            The highest TLP level found
        """
        query_config = self.config["queries"].get(query_name, {})
        highest_level = "clear"
        
        # Check all metadata items for TLP levels
        for key in query_config:
            if isinstance(query_config[key], dict) and "tlp_level" in query_config[key]:
                item_tlp = query_config[key]["tlp_level"]
                if self.tlp_levels.index(item_tlp) > self.tlp_levels.index(highest_level):
                    highest_level = item_tlp
            elif key == "notes" and isinstance(query_config[key], list):
                for note in query_config[key]:
                    if isinstance(note, dict) and "tlp_level" in note:
                        item_tlp = note["tlp_level"]
                        if self.tlp_levels.index(item_tlp) > self.tlp_levels.index(highest_level):
                            highest_level = item_tlp
            elif key == "references" and isinstance(query_config[key], list):
                for ref in query_config[key]:
                    if isinstance(ref, dict) and "tlp_level" in ref:
                        item_tlp = ref["tlp_level"]
                        if self.tlp_levels.index(item_tlp) > self.tlp_levels.index(highest_level):
                            highest_level = item_tlp
                            
        return highest_level

    def _generate_html_report(self, results, query_name, output_dir, tlp_level="clear", timestamp=None, debug=False):
        """Generate an HTML report from the results."""
        # Get query data including metadata
        query_data = self.config["queries"].get(query_name, {})
        
        # Check if query has a specific template path
        template_path = query_data.get("template_path")
        
        # If no query-specific template, use the global default
        if not template_path:
            template_path = self.config.get("default_template_path", "templates/report_template.html")
            
        # Split template path into directory and filename
        template_dir = os.path.dirname(template_path)
        template_file = os.path.basename(template_path)
        
        # Create Jinja2 environment with the appropriate template directory
        env = Environment(loader=FileSystemLoader(template_dir if template_dir else "templates"))
        try:
            template = env.get_template(template_file)
        except Exception as e:
            print(f"Error loading template {template_path}: {e}")
            print("Falling back to default template")
            env = Environment(loader=FileSystemLoader("templates"))
            template = env.get_template("report_template.html")
        
        # Use the provided timestamp or generate current time
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = template.render(
            query_name=query_name,
            query_data=query_data,
            timestamp=timestamp,
            results=results,
            username=self.config.get("report_username", ""),
            tlp_level=tlp_level,
            debug=debug
        )
        
        # Remove blank lines from HTML content
        html_content = "\n".join([line for line in html_content.split("\n") if line.strip()])
        
        # Extract the date/time group from the output directory
        dir_name = output_dir.name
        datetime_part = ""
        if "_" in dir_name:
            datetime_part = dir_name.split("_", 1)[1]
        
        # Include TLP level and datetime in the filename
        report_filename = f"report_{query_name}_{datetime_part}_TLP-{tlp_level}.html"
        with open(output_dir / report_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def save_urlscan_results(self, query_name, results, timestamp=None):
        """Save urlscan results to a JSON file for testing.
        
        Args:
            query_name: Name of the query
            results: List of urlscan result objects
            timestamp: Optional timestamp to use in the filename
        
        Returns:
            Path to the saved results file
        """
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Create a directory for saved results if it doesn't exist
        cache_dir = Path("cached_results")
        cache_dir.mkdir(exist_ok=True)
        
        # Create a filename with the query name and timestamp
        cache_file = cache_dir / f"{query_name}_{timestamp}_results.json"
        
        # Save the results to a JSON file
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
            
        print(f"Saved urlscan results to {cache_file}")
        return cache_file
        
    def load_urlscan_results(self, file_path):
        """Load saved urlscan results from a JSON file.
        
        Args:
            file_path: Path to the JSON file containing saved results
        
        Returns:
            List of urlscan result objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
                
            print(f"Loaded {len(results)} results from {file_path}")
            return results
        except Exception as e:
            print(f"Error loading saved results: {e}")
            return []

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

    def test_report_generation(self, query_name, cached_results_path, tlp_level=None, debug=False):
        """Generate a test report using saved results without querying urlscan.
        
        Args:
            query_name: Name of the query for metadata
            cached_results_path: Path to JSON file with saved urlscan results
            tlp_level: Optional TLP level for the report
            debug: Whether to include debug information in the report
            
        Returns:
            Path to the generated report
        """
        print(f"Generating test report for '{query_name}' using cached results")
        
        # Load the saved results
        results = self.load_urlscan_results(cached_results_path)
        if not results:
            print("No results loaded, cannot generate report")
            return None
        
        # Determine the appropriate TLP level
        report_tlp = self._determine_tlp_level(query_name, tlp_level)
        print(f"Report TLP level: {report_tlp}")
        
        # Get query configuration and platform
        query_data = self.config["queries"].get(query_name, {})
        platform = query_data.get("platform", "urlscan")
        print(f"Using platform: {platform}")
        
        # Create a unique output directory for this test
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"{query_name}_{timestamp}_test"
        run_dir.mkdir(exist_ok=True)
        
        # Save the images directory
        img_dir = run_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        # Process the results for display
        for i, result in enumerate(results):
            # Defang URLs and domains
            if "page" in result and "url" in result["page"]:
                result["defanged_url"] = self._defang_url(result["page"]["url"])
            if "page" in result and "domain" in result["page"]:
                result["defanged_domain"] = self._defang_domain(result["page"]["domain"])
                
            # Handle screenshots if available in the cached results
            if "task" in result and "uuid" in result["task"]:
                uuid = result["task"]["uuid"]
                result["local_screenshot"] = f"images/{uuid}.png"

        # Add debug information if requested
        if debug:
            print("Adding debug information to the report...")
            # Add a debug section to show JSON representations of key data
            debug_info = {
                "query_data": query_data,
                "tlp_level": report_tlp,
                "platform": platform,
                "references": query_data.get("references", []),
                "tlp_order": {"clear": 1, "white": 1, "green": 2, "amber": 3, "red": 4}
            }
            
            for result in results:
                result["debug_info"] = json.dumps(debug_info, indent=2)
        
        # Generate the HTML report
        report_path = self._generate_html_report(
            results, 
            query_name, 
            run_dir, 
            report_tlp, 
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            debug=debug
        )
        
        print(f"Test report generated in {run_dir}")
        return report_path

def main():
    parser = argparse.ArgumentParser(description="Monitor for masquerades using urlscan.io")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--list", action="store_true", help="List available queries")
    parser.add_argument("--query", help="Run a specific query")
    parser.add_argument("--query-group", help="Run a specific query group")
    parser.add_argument("--all", action="store_true", help="Run all queries")
    parser.add_argument("--all-groups", action="store_true", help="Run all query groups")
    parser.add_argument("-d", "--days", type=int, help="Limit results to the specified number of days")
    parser.add_argument("--tlp", choices=["clear", "white", "green", "amber", "red"], 
                        help="Set the TLP level for the report")
    
    # Add new testing options
    parser.add_argument("--save-results", action="store_true", 
                        help="Save urlscan.io results to a JSON file for testing")
    parser.add_argument("--cached-results", 
                        help="Path to a JSON file with saved urlscan.io results")
    parser.add_argument("--debug", action="store_true", 
                        help="Include debug information in reports")
    
    args = parser.parse_args()
    
    monitor = MasqMonitor(config_path=args.config)
    
    # Use default_days from config if --days not specified
    days = args.days if args.days is not None else monitor.config.get("default_days")
    
    if args.list:
        monitor.list_queries()
    elif args.query and args.cached_results:
        # Generate test report using cached results
        monitor.test_report_generation(args.query, args.cached_results, tlp_level=args.tlp, debug=args.debug)
    elif args.query:
        # Run query and optionally save the results
        results = monitor.run_query(args.query, days=days, tlp_level=args.tlp)
        if args.save_results and results:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            monitor.save_urlscan_results(args.query, results, timestamp)
    elif args.query_group:
        # Run a query group
        group_results = monitor.run_query_group(args.query_group, days=days, tlp_level=args.tlp)
        # Save results from each query if requested
        if args.save_results and group_results:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            for query_name, query_results in group_results.items():
                if isinstance(query_results, list) and query_results:  # Only save actual query results, not nested groups
                    monitor.save_urlscan_results(query_name, query_results, timestamp)
    elif args.all:
        # Run all individual queries (not query groups)
        for query_name, query_data in monitor.config.get("queries", {}).items():
            if query_data.get("type") != "query_group":
                results = monitor.run_query(query_name, days=days, tlp_level=args.tlp)
                if args.save_results and results:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    monitor.save_urlscan_results(query_name, results, timestamp)
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
                            monitor.save_urlscan_results(sub_query_name, query_results, timestamp)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()