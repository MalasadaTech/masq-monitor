#!/usr/bin/env python3

import os
import json
import yaml
import time
import argparse
import datetime
import requests
import base64
import subprocess
import threading
import importlib.util
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
        
        # Create extensions directory if it doesn't exist
        self.extensions_dir = Path("extensions")
        self.extensions_dir.mkdir(exist_ok=True)

    def _load_config(self):
        """Load configuration from the config file (JSON or YAML)."""
        try:
            file_extension = Path(self.config_path).suffix.lower()
            with open(self.config_path, 'r') as f:
                if file_extension == '.yaml' or file_extension == '.yml':
                    return yaml.safe_load(f)
                else:  # Default to JSON
                    return json.load(f)
        except FileNotFoundError:
            print(f"Config file not found at {self.config_path}.")
            print("Please create a config file based on the example files.")
            exit(1)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            print(f"Error parsing the config file at {self.config_path}: {e}")
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
        """Save the updated configuration to the config file (JSON or YAML)."""
        try:
            file_extension = Path(self.config_path).suffix.lower()
            with open(self.config_path, 'w') as f:
                if file_extension == '.yaml' or file_extension == '.yml':
                    yaml.dump(self.config, f, default_flow_style=False)
                else:  # Default to JSON
                    json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving the config file: {e}")

    def _defang_domain(self, domain):
        """Defang a domain to make it safe for sharing."""
        return self.report_generator._defang_domain(domain)

    def _defang_url(self, url):
        """Defang a URL to make it safe for sharing."""
        return self.report_generator._defang_url(url)

    def run_query(self, query_name, days=None, tlp_level=None, save_iocs=False):
        """Run a specific query from the configuration.
        
        Args:
            query_name: Name of the query to run from config
            days: Optional. Number of days to limit the search to (from today)
                 If not provided, uses last_run timestamp or falls back to default_days
            tlp_level: Optional. TLP level to apply to this report
                      If not provided, uses query default or global default
            save_iocs: Optional. Whether to save IOCs to CSV files
                      
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
            
            # If save_iocs is enabled, extract IOCs and save to CSV based on the platform
            if save_iocs:
                iocs_dir = run_dir / "iocs"
                iocs_dir.mkdir(exist_ok=True)
                
                if platform == "urlscan":
                    iocs = self.urlscan_client.extract_iocs(results)
                    # For normal runs, don't use verbose output (testing_mode=False)
                    csv_paths = self.urlscan_client.save_iocs_to_csv(iocs, output_path=iocs_dir, query_name=query_name, testing_mode=False)
                    print(f"URLScan IOCs saved to CSV in {iocs_dir}")
                elif platform == "silentpush":
                    iocs = self.silentpush_client.extract_iocs(results)
                    # For normal runs, don't use verbose output (testing_mode=False)
                    csv_paths = self.silentpush_client.save_iocs_to_csv(iocs, output_path=iocs_dir, query_name=query_name, testing_mode=False)
                    print(f"Silent Push IOCs saved to CSV in {iocs_dir}")
            
            # Run extensions for post-processing
            self.run_extensions(run_dir, query_name)
        
        else:
            print(f"No results found for query '{query_name}'")
        
        # Update the last_run timestamp
        current_time = datetime.datetime.now().isoformat()
        self.config["queries"][query_name]["last_run"] = current_time
        self._save_config()
        
        return results

    def run_extensions(self, run_dir, query_name=None):
        """Run extensions for post-processing of query results.
        
        Args:
            run_dir: Path to the output directory for this run
            query_name: Optional name of the query that triggered the extensions
            
        This method will run extensions in parallel using threads.
        Extensions are run in the order they are defined in the config.
        """
        # Create extensions directory in run_dir
        extensions_output_dir = run_dir / "extensions"
        extensions_output_dir.mkdir(exist_ok=True)
        
        # Check if extensions are configured globally
        global_extensions = self.config.get("extensions", [])
        
        # Check if there are query-specific extensions
        query_extensions = []
        if query_name and query_name in self.config.get("queries", {}):
            query_extensions = self.config["queries"][query_name].get("extensions", [])
        
        # Combine the lists, query extensions take precedence
        all_extensions = global_extensions + query_extensions
        
        if not all_extensions:
            return
        
        print(f"Running {len(all_extensions)} extension(s)")
        
        # Run extensions in separate threads
        threads = []
        for extension in all_extensions:
            extension_path = self.extensions_dir / extension
            
            # Check if the extension exists
            if not extension_path.exists():
                print(f"Extension '{extension}' not found in extensions directory")
                continue
                
            # Create a thread to run the extension
            print(f"Running extension: {extension}")
            thread = threading.Thread(
                target=self._run_extension,
                args=(extension_path, run_dir, extensions_output_dir, query_name)
            )
            thread.start()
            threads.append(thread)
            
        # Wait for all extensions to complete
        for thread in threads:
            thread.join()

    def _run_extension(self, extension_path, run_dir, output_dir, query_name=None):
        """Run a single extension script.
        
        Args:
            extension_path: Path to the extension script
            run_dir: Path to the output directory for this run
            output_dir: Path to the directory where extension should output results
            query_name: Optional name of the query that triggered the extension
        """
        try:
            print(f"Starting extension execution: {extension_path}")
            
            # Create a debug log for all extension executions
            with open("extension_execution_debug.log", "a") as debug_log:
                debug_log.write(f"\n\n===== EXTENSION EXECUTION =====\n")
                debug_log.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                debug_log.write(f"Extension: {extension_path}\n")
                debug_log.write(f"Run Dir: {run_dir}\n")
                debug_log.write(f"Output Dir: {output_dir}\n")
                debug_log.write(f"Query Name: {query_name}\n")
                debug_log.write(f"Current Working Dir: {os.getcwd()}\n")
            
            # Two options to run extensions:
            # 1. As a Python module
            # 2. As a subprocess (for non-Python scripts)
            
            # Check file extension to determine how to run it
            if extension_path.suffix.lower() == ".py":
                # Run as a Python module
                try:
                    print(f"Importing Python module: {extension_path}")
                    with open("extension_execution_debug.log", "a") as debug_log:
                        debug_log.write(f"Running as Python module\n")
                    
                    # Import the module dynamically
                    spec = importlib.util.spec_from_file_location(extension_path.stem, extension_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Check if the module has a main function
                    if hasattr(module, "main"):
                        print(f"Extension has main() function, calling it with: {run_dir}")
                        with open("extension_execution_debug.log", "a") as debug_log:
                            debug_log.write(f"Module has main function, calling main({run_dir})\n")
                        
                        # Call the main function with the run_dir argument
                        module.main(str(run_dir))
                        print(f"Extension {extension_path.name} main() function completed")
                    else:
                        print(f"Warning: Extension '{extension_path.name}' does not have a main function")
                        with open("extension_execution_debug.log", "a") as debug_log:
                            debug_log.write(f"ERROR: Module does not have main function\n")
                except Exception as e:
                    print(f"Error running Python extension '{extension_path.name}': {e}")
                    import traceback
                    print(f"Extension error traceback: {traceback.format_exc()}")
                    with open("extension_execution_debug.log", "a") as debug_log:
                        debug_log.write(f"ERROR running Python extension: {e}\n")
                        debug_log.write(traceback.format_exc())
            else:
                # Run as a subprocess
                try:
                    print(f"Running as subprocess: {extension_path}")
                    with open("extension_execution_debug.log", "a") as debug_log:
                        debug_log.write(f"Running as subprocess\n")
                        debug_log.write(f"Command: {[str(extension_path), str(run_dir)]}\n")
                    
                    # Pass the run_dir as an argument
                    process = subprocess.Popen(
                        [str(extension_path), str(run_dir)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate()
                    
                    with open("extension_execution_debug.log", "a") as debug_log:
                        debug_log.write(f"Subprocess exit code: {process.returncode}\n")
                        debug_log.write(f"Subprocess stdout: {stdout[:1000]}\n")
                        debug_log.write(f"Subprocess stderr: {stderr[:1000]}\n")
                    
                    if process.returncode != 0:
                        print(f"Error running extension '{extension_path.name}': {stderr}")
                except Exception as e:
                    print(f"Error running extension '{extension_path.name}' as subprocess: {e}")
                    import traceback
                    print(f"Extension subprocess error traceback: {traceback.format_exc()}")
                    with open("extension_execution_debug.log", "a") as debug_log:
                        debug_log.write(f"ERROR running subprocess: {e}\n")
                        debug_log.write(traceback.format_exc())
                    
        except Exception as e:
            print(f"Unexpected error running extension '{extension_path.name}': {e}")
            import traceback
            print(f"Extension unexpected error traceback: {traceback.format_exc()}")
            with open("extension_execution_debug.log", "a") as debug_log:
                debug_log.write(f"UNEXPECTED ERROR: {e}\n")
                debug_log.write(traceback.format_exc())

    def run_query_group(self, group_name, days=None, tlp_level=None, save_iocs=False):
        """Run a group of queries and generate a combined report.
        
        Args:
            group_name: Name of the query group to run
            days: Optional. Number of days to limit the search to
            tlp_level: Optional. TLP level to apply to this report
            save_iocs: Optional. Whether to save IOCs to CSV files for each query
            
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
        
        # Create a timestamp for the group
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Storage for combined IOCs
        group_iocs = {
            "domains": set(),
            "ips": set(),
            "urls": set(),
            "scan_ids": set(),
            "scan_dates": set(),
            "page_titles": set(),
            "server_details": set()
        }
        
        # Flag to track if any IOCs were extracted
        extracted_iocs = False
        
        # Run each query in the group
        for query_name in query_names:
            # Check if this is a nested query group
            if query_name in self.config["queries"] and self.config["queries"][query_name].get("type") == "query_group":
                print(f"Running nested query group '{query_name}'")
                # Run the nested query group
                nested_results = self.run_query_group(query_name, days=days, tlp_level=tlp_level, save_iocs=save_iocs)
                self.group_results[group_name][query_name] = {
                    "type": "query_group",
                    "results": nested_results
                }
            else:
                # Run individual query
                print(f"Running query '{query_name}' as part of group '{group_name}'")
                results = self.run_query(query_name, days=days, tlp_level=tlp_level, save_iocs=save_iocs)
                self.group_results[group_name][query_name] = results
                
                # Extract IOCs from urlscan results and combine them for the group
                if save_iocs and results:
                    platform = "urlscan"
                    if query_name in self.config["queries"]:
                        platform = self.config["queries"][query_name].get("platform", "urlscan")
                    
                    if platform == "urlscan":
                        # Extract IOCs from the results
                        query_iocs = self.urlscan_client.extract_iocs(results)
                        extracted_iocs = True
                        
                        # Combine with group IOCs
                        for ioc_type, values in query_iocs.items():
                            if isinstance(values, list):
                                group_iocs[ioc_type].update(values)
                
        # Generate a combined report after all queries have run
        self.report_generator.generate_group_report(group_name, self.group_results[group_name], tlp_level)
        
        # If save_iocs is enabled and any IOCs were extracted, save the combined group IOCs
        if save_iocs and extracted_iocs:
            # Create an output directory for the group
            run_dir = self.output_dir / f"{group_name}_{timestamp}"
            run_dir.mkdir(exist_ok=True)
            
            # Create an IOCs directory
            iocs_dir = run_dir / "iocs"
            iocs_dir.mkdir(exist_ok=True)
            
            # Convert sets to lists for JSON serialization
            group_iocs_dict = {k: list(v) for k, v in group_iocs.items()}
            
            # Save the combined group IOCs with testing_mode=False to avoid excessive output
            csv_paths = self.urlscan_client.save_iocs_to_csv(
                group_iocs_dict, 
                output_path=iocs_dir, 
                query_name=f"{group_name}_combined",
                testing_mode=False
            )
            # Simple message about combined IOCs being saved
            print(f"Combined group IOCs saved to {iocs_dir}")
        
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

    def test_report_generation(self, query_name, cached_results_path, tlp_level=None, save_iocs=False):
        """Generate a test report using saved results without querying APIs.
        
        Args:
            query_name: Name of the query for metadata
            cached_results_path: Path to JSON file with saved platform results
            tlp_level: Optional TLP level for the report
            save_iocs: Optional. Whether to save IOCs to CSV files
            
        Returns:
            Path to the generated report
        """
        print(f"Generating test report for '{query_name}' using cached results")
        
        # Load the saved results using the platform-agnostic method
        results = self.load_results(cached_results_path)
        if not results:
            print("No results loaded, cannot generate report")
            return None
        
        # If save_iocs is enabled, extract and save IOCs
        if save_iocs:
            # Determine the platform from the query config
            platform = "urlscan"
            if query_name in self.config["queries"]:
                platform = self.config["queries"][query_name].get("platform", "urlscan")
            
            # Create a unique output directory for this run
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = self.output_dir / f"{query_name}_{timestamp}_test"
            run_dir.mkdir(exist_ok=True)
            
            # Create iocs directory
            iocs_dir = run_dir / "iocs"
            iocs_dir.mkdir(exist_ok=True)
            
            # Extract and save IOCs based on platform
            if platform == "urlscan":
                iocs = self.urlscan_client.extract_iocs(results)
                csv_paths = self.urlscan_client.save_iocs_to_csv(iocs, output_path=iocs_dir, query_name=query_name, testing_mode=True)
                print(f"URLScan IOCs saved to CSV in {iocs_dir}")
            elif platform == "silentpush":
                iocs = self.silentpush_client.extract_iocs(results)
                csv_paths = self.silentpush_client.save_iocs_to_csv(iocs, output_path=iocs_dir, query_name=query_name, testing_mode=True)
                print(f"Silent Push IOCs saved to CSV in {iocs_dir}")
        
        # Generate the test report using the report generator
        return self.report_generator.test_report_generation(query_name, results, tlp_level)

def main():
    parser = argparse.ArgumentParser(description="Monitor for masquerades using multiple platforms")
    parser.add_argument("--config", default="config.json", 
                        help="Path to configuration file (supports both JSON and YAML formats with .json, .yaml, or .yml extensions)")
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
    parser.add_argument("--no-iocs", action="store_true", 
                        help="Disable saving IOCs to CSV files (IOCs are saved by default)")
    
    args = parser.parse_args()
    
    # Check if config.yaml exists when using default config.json
    if args.config == "config.json" and not os.path.exists(args.config):
        yaml_config = "config.yaml"
        yml_config = "config.yml"
        if os.path.exists(yaml_config):
            print(f"No {args.config} found but {yaml_config} exists. Using {yaml_config} instead.")
            args.config = yaml_config
        elif os.path.exists(yml_config):
            print(f"No {args.config} found but {yml_config} exists. Using {yml_config} instead.")
            args.config = yml_config
    
    monitor = MasqMonitor(config_path=args.config)
    
    # Use default_days from config if --days not specified
    days = args.days if args.days is not None else monitor.config.get("default_days")
    
    # IOCs are saved by default unless --no-iocs is specified
    save_iocs = not args.no_iocs
    
    if args.list:
        monitor.list_queries()
    elif args.query and args.cached_results:
        # Generate test report using cached results
        monitor.test_report_generation(args.query, args.cached_results, tlp_level=args.tlp, save_iocs=save_iocs)
    elif args.query:
        # Run query and optionally save the results
        results = monitor.run_query(args.query, days=days, tlp_level=args.tlp, save_iocs=save_iocs)
        if args.save_results and results:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            monitor.save_results(args.query, results, timestamp)
    elif args.query_group:
        # Run a query group
        group_results = monitor.run_query_group(args.query_group, days=days, tlp_level=args.tlp, save_iocs=save_iocs)
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
                results = monitor.run_query(query_name, days=days, tlp_level=args.tlp, save_iocs=save_iocs)
                if args.save_results and results:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    monitor.save_results(query_name, results, timestamp)
    elif args.all_groups:
        # Run all query groups
        for query_name, query_data in monitor.config.get("queries", {}).items():
            if query_data.get("type") == "query_group":
                group_results = monitor.run_query_group(query_name, days=days, tlp_level=args.tlp, save_iocs=save_iocs)
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