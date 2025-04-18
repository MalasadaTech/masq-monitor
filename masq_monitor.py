#!/usr/bin/env python3

import os
import json
import time
import argparse
import datetime
import requests
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

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

    def run_query(self, query_name, days=None):
        """Run a specific query from the configuration.
        
        Args:
            query_name: Name of the query to run from config
            days: Optional. Number of days to limit the search to (from today)
        """
        if query_name not in self.config["queries"]:
            print(f"Query '{query_name}' not found in configuration.")
            return
        
        query_config = self.config["queries"][query_name]
        api_key = self.config.get("api_key", "")
        
        # Create the query string, adding date filter if days is specified
        query_string = query_config["query"]
        if days is not None:
            # Calculate the date from N days ago
            date_from = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            query_string = f"{query_string} AND date:>={date_from}"
            print(f"Running query: {query_name} (limited to {days} days from {date_from})")
        else:
            print(f"Running query: {query_name}")
        
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
            
            # Generate the HTML report
            self._generate_html_report(results, query_name, run_dir)
            print(f"Report generated in {run_dir} with {len(results)} results")
        else:
            print(f"No results found for query '{query_name}'")

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

    def _generate_html_report(self, results, query_name, output_dir):
        """Generate an HTML report from the results."""
        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("report_template.html")
        
        html_content = template.render(
            query_name=query_name,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            results=results
        )
        
        with open(output_dir / "report.html", 'w') as f:
            f.write(html_content)

    def list_queries(self):
        """List all available queries from the configuration."""
        if "queries" not in self.config:
            print("No queries defined in the configuration.")
            return
        
        print("Available queries:")
        for name, details in self.config["queries"].items():
            print(f" - {name}: {details.get('description', 'No description')}")

def main():
    parser = argparse.ArgumentParser(description="Monitor for masquerades using urlscan.io")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--list", action="store_true", help="List available queries")
    parser.add_argument("--query", help="Run a specific query")
    parser.add_argument("--all", action="store_true", help="Run all queries")
    parser.add_argument("-d", "--days", type=int, help="Limit results to the specified number of days")
    
    args = parser.parse_args()
    
    monitor = MasqMonitor(config_path=args.config)
    
    if args.list:
        monitor.list_queries()
    elif args.query:
        monitor.run_query(args.query, days=args.days)
    elif args.all:
        for query_name in monitor.config.get("queries", {}):
            monitor.run_query(query_name, days=args.days)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()