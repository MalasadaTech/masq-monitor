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

class MasqMonitor:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.output_dir = Path(self.config.get("output_directory", "output"))
        self.output_dir.mkdir(exist_ok=True)

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

    def _save_config(self):
        """Save the updated configuration to the config file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving the config file: {e}")

    def _defang_url(self, url):
        """Defang a URL to make it safe for sharing."""
        if not url:
            return ""
        # Replace http:// with hxxp:// and https:// with hxxps://
        defanged = re.sub(r'http://', 'hxxp://', url)
        defanged = re.sub(r'https://', 'hxxps://', defanged)
        # Replace dots with [.]
        defanged = re.sub(r'\.', '[.]', defanged)
        return defanged

    def run_query(self, query_name, days=None):
        """Run a specific query from the configuration.
        
        Args:
            query_name: Name of the query to run from config
            days: Optional. Number of days to limit the search to (from today)
                 If not provided, uses last_run timestamp or falls back to default_days
        """
        if query_name not in self.config["queries"]:
            print(f"Query '{query_name}' not found in configuration.")
            return
        
        query_config = self.config["queries"][query_name]
        api_key = self.config.get("api_key", "")
        
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
        
        # Execute the query
        results = self._execute_urlscan_query(query_string, api_key)
        
        if results:
            # Download thumbnails for each result
            for i, result in enumerate(results):
                if "task" in result and "uuid" in result["task"]:
                    uuid = result["task"]["uuid"]
                    self._download_screenshot(uuid, img_dir / f"{uuid}.png", api_key)
                    result["local_screenshot"] = f"images/{uuid}.png"
                    result["base64_screenshot"] = self._encode_image_to_base64(img_dir / f"{uuid}.png")
                
                # Defang all URLs and domains in the result
                if "page" in result and "url" in result["page"]:
                    result["defanged_url"] = self._defang_url(result["page"]["url"])
                if "page" in result and "domain" in result["page"]:
                    result["defanged_domain"] = self._defang_url(result["page"]["domain"])
            
            # Generate the HTML report
            self._generate_html_report(results, query_name, run_dir)
            print(f"Report generated in {run_dir} with {len(results)} results")
        else:
            print(f"No results found for query '{query_name}'")
        
        # Update the last_run timestamp
        current_time = datetime.datetime.now().isoformat()
        self.config["queries"][query_name]["last_run"] = current_time
        self._save_config()

    def _execute_urlscan_query(self, query, api_key):
        """Execute a query against the urlscan.io API."""
        headers = {"API-Key": api_key} if api_key else {}
        
        url = f"https://urlscan.io/api/v1/search/?q={query}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except requests.RequestException as e:
            print(f"Error executing query: {e}")
            return []

    def _download_screenshot(self, uuid, output_path, api_key):
        """Download the screenshot for a specific scan."""
        headers = {"API-Key": api_key} if api_key else {}
        
        url = f"https://urlscan.io/screenshots/{uuid}.png"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            return True
        except requests.RequestException as e:
            print(f"Error downloading screenshot for {uuid}: {e}")
            return False

    def _encode_image_to_base64(self, image_path):
        """Encode an image file to Base64."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            print(f"Error encoding image {image_path} to Base64: {e}")
            return None

    def _generate_html_report(self, results, query_name, output_dir):
        """Generate an HTML report from the results."""
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("report_template.html")
        
        # Get query data including metadata
        query_data = self.config["queries"].get(query_name, {})
        
        html_content = template.render(
            query_name=query_name,
            query_data=query_data,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results=results,
            username=self.config.get("report_username", "")
        )
        
        with open(output_dir / "report.html", 'w', encoding='utf-8') as f:
            f.write(html_content)

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
            tags = ", ".join(details.get('tags', [])) or "None"
            
            print(f"\n{name}:")
            print(f"  Description: {description}")
            print(f"  Query: {details['query']}")
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

def main():
    parser = argparse.ArgumentParser(description="Monitor for masquerades using urlscan.io")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--list", action="store_true", help="List available queries")
    parser.add_argument("--query", help="Run a specific query")
    parser.add_argument("--all", action="store_true", help="Run all queries")
    parser.add_argument("-d", "--days", type=int, help="Limit results to the specified number of days")
    
    args = parser.parse_args()
    
    monitor = MasqMonitor(config_path=args.config)
    
    # Use default_days from config if --days not specified
    days = args.days if args.days is not None else monitor.config.get("default_days")
    
    if args.list:
        monitor.list_queries()
    elif args.query:
        monitor.run_query(args.query, days=days)
    elif args.all:
        for query_name in monitor.config.get("queries", {}):
            monitor.run_query(query_name, days=days)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()