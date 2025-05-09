#!/usr/bin/env python3

import requests
import base64
import csv
import json
from pathlib import Path
from datetime import datetime

class UrlscanClient:
    """Client for interacting with the urlscan.io API."""
    
    def __init__(self, api_key=None):
        """Initialize the urlscan client with an API key.
        
        Args:
            api_key: Optional. The API key for urlscan.io
        """
        self.api_key = api_key
        
    def execute_query(self, query):
        """Execute a query against the urlscan.io API.
        
        Args:
            query: The query string to search for
            
        Returns:
            List of results from the query
        """
        # Set up headers with API key if available
        headers = {"API-Key": self.api_key} if self.api_key else {}
        
        url = f"https://urlscan.io/api/v1/search/?q={query}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except requests.RequestException as e:
            print(f"Error executing urlscan query: {e}")
            return []

    def download_screenshot(self, uuid, output_path):
        """Download the screenshot for a specific scan.
        
        Args:
            uuid: UUID of the urlscan task
            output_path: Path to save the screenshot
            
        Returns:
            Boolean indicating success or failure
        """
        # Set up headers with API key if available
        headers = {"API-Key": self.api_key} if self.api_key else {}
        
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
            
    def encode_image_to_base64(self, image_path):
        """Encode an image file to Base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64-encoded string or None if an error occurs
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            print(f"Error encoding image {image_path} to Base64: {e}")
            return None
    
    def extract_iocs(self, results):
        """Extract Indicators of Compromise (IOCs) from urlscan results.
        
        Args:
            results: List of urlscan result objects
            
        Returns:
            Dictionary of extracted IOCs
        """
        iocs = {
            "domains": set(),
            "ips": set(),
            "urls": set(),
            "scan_ids": set(),
            "scan_dates": set(),
            "page_titles": set(),
            "server_details": set()
        }
        
        for result in results:
            # Extract domains
            if "page" in result and "domain" in result["page"]:
                iocs["domains"].add(result["page"]["domain"])
            
            # Extract IPs
            if "page" in result and "ip" in result["page"]:
                iocs["ips"].add(result["page"]["ip"])
            
            # Extract URLs
            if "page" in result and "url" in result["page"]:
                iocs["urls"].add(result["page"]["url"])
            
            # Extract scan IDs
            if "task" in result and "uuid" in result["task"]:
                iocs["scan_ids"].add(result["task"]["uuid"])
            
            # Extract scan dates
            if "task" in result and "time" in result["task"]:
                iocs["scan_dates"].add(result["task"]["time"])
            
            # Extract page titles
            if "page" in result and "title" in result["page"]:
                iocs["page_titles"].add(result["page"]["title"])
            
            # Extract server information
            if "page" in result and "server" in result["page"]:
                iocs["server_details"].add(result["page"]["server"])
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in iocs.items()}

    def save_iocs_to_csv(self, iocs, output_path=None, query_name=None, testing_mode=False):
        """Save extracted IOCs to CSV files.
        
        Args:
            iocs: Dictionary of extracted IOCs
            output_path: Optional. Path to save the CSV files
            query_name: Optional. Name of the query for the filename
            testing_mode: Optional. Whether to print verbose output (default: False)
            
        Returns:
            Dictionary with paths of saved CSV files
        """
        # Set default output path if not provided
        if not output_path:
            output_path = Path("output/iocs")
        
        # Create output directory if it doesn't exist
        output_dir = Path(output_path)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate a timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{query_name}_{timestamp}" if query_name else timestamp
        
        # Save all IOCs to a single CSV file
        combined_csv_path = output_dir / f"{prefix}_all_iocs.csv"
        
        csv_paths = {"combined": str(combined_csv_path)}
        
        try:
            # Create the combined CSV file
            with open(combined_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['ioc_type', 'value', 'scan_id']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write domains with their scan IDs
                for domain in iocs.get("domains", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'domain', 'value': domain, 'scan_id': scan_ids})
                
                # Write IPs with their scan IDs
                for ip in iocs.get("ips", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'ip', 'value': ip, 'scan_id': scan_ids})
                
                # Write URLs with their scan IDs
                for url in iocs.get("urls", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'url', 'value': url, 'scan_id': scan_ids})
                
                # Write page titles with their scan IDs
                for title in iocs.get("page_titles", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'title', 'value': title, 'scan_id': scan_ids})
                
                # Write server details with their scan IDs
                for server in iocs.get("server_details", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'server', 'value': server, 'scan_id': scan_ids})
            
            # Only print detailed output in testing mode
            if testing_mode:
                print(f"Saved all IOCs to {combined_csv_path}")
            
            # Optionally save individual IOC types to separate files
            for ioc_type, values in iocs.items():
                if values:  # Only create files for IOC types that have values
                    ioc_csv_path = output_dir / f"{prefix}_{ioc_type}.csv"
                    csv_paths[ioc_type] = str(ioc_csv_path)
                    
                    with open(ioc_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([ioc_type])  # Header
                        for value in values:
                            writer.writerow([value])
                    
                    # Only print detailed output in testing mode
                    if testing_mode:
                        print(f"Saved {len(values)} {ioc_type} to {ioc_csv_path}")
            
            # Also save the full IOCs dictionary as JSON for reference
            json_path = output_dir / f"{prefix}_iocs.json"
            with open(json_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(iocs, jsonfile, indent=2)
            
            csv_paths["json"] = str(json_path)
            
            # Only print detailed output in testing mode
            if testing_mode:
                print(f"Saved IOCs JSON to {json_path}")
            else:
                print(f"IOCs saved to {output_dir}")
            
            return csv_paths
        
        except Exception as e:
            print(f"Error saving IOCs to CSV: {e}")
            return {}