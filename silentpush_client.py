#!/usr/bin/env python3

import requests
import base64
import json
import datetime
from pathlib import Path
from datetime import datetime

class SilentPushClient:
    """Client for interacting with the Silent Push API."""
    
    def __init__(self, api_key=None):
        """Initialize the Silent Push client with an API key.
        
        Args:
            api_key: Optional. The API key for Silent Push API
        """
        self.api_key = api_key
        self.base_url = "https://api.silentpush.com/api/v1/merge-api"
        # Set default timeout values (connect_timeout, read_timeout) in seconds
        self.connect_timeout = 30  # 30 seconds for connection
        self.read_timeout = 120    # 2 minutes to read data
        
        if not self.api_key:
            print("Warning: No SilentPush API key provided. API access will be limited.")
    
    def set_timeouts(self, connect_timeout=None, read_timeout=None):
        """Set custom timeout values for API requests.
        
        Args:
            connect_timeout: Timeout for establishing connection (in seconds)
            read_timeout: Timeout for reading data (in seconds)
        """
        if connect_timeout is not None:
            self.connect_timeout = connect_timeout
        
        if read_timeout is not None:
            self.read_timeout = read_timeout
            
        print(f"SilentPush timeouts set to: connect={self.connect_timeout}s, read={self.read_timeout}s")
    
    def prepare_query(self, query):
        """Prepare query string, handling special cases like dates.
        
        Args:
            query: Original query string
            
        Returns:
            Properly formatted query string
        """
        # Process the query to ensure proper date formatting
        # SilentPush format for date queries: scan_date >= "YYYY-MM-DDTHH:MM:SSZ"
        
        # Check for potential date formatting issues
        if "date:" in query:
            # This appears to be the wrong format - replace with proper scan_date syntax
            query = query.replace("date:", "scan_date ")
        
        import re
        
        # Convert regular date format (YYYY-MM-DD HH:MM:SS) to ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
        date_pattern = r'scan_date\s*(?:[<>=!]+)\s*"?([0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2}:[0-9]{2})?)(?:"|\s|$)'
        
        def format_date_iso8601(match):
            date_str = match.group(1)
            operator = match.group(0)[9:match.start(1) - match.start(0)].strip()
            
            # If this is just a date without time, add time component
            if len(date_str) == 10:  # YYYY-MM-DD format
                date_str = f"{date_str}T00:00:00Z"
            else:
                # Convert 'YYYY-MM-DD HH:MM:SS' to 'YYYY-MM-DDTHH:MM:SSZ'
                date_str = date_str.replace(" ", "T") + "Z"
            
            # Return with proper quoting
            return f'scan_date {operator} "{date_str}"'
        
        query = re.sub(date_pattern, format_date_iso8601, query)
        
        return query
    
    def save_raw_response(self, query, response_data, error=None):
        """Save the raw API response to a file for troubleshooting.
        
        Args:
            query: The original query string
            response_data: The raw response data from the API
            error: Optional error message or exception
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache_dir = Path("cached_results")
        cache_dir.mkdir(exist_ok=True)
        
        # Create a timestamped filename for the raw response
        filename = f"silentpush_raw_response_{timestamp}.json"
        filepath = cache_dir / filename
        
        # Create a data structure with query and response information
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response_data
        }
        
        if error:
            debug_data["error"] = str(error)
        
        # Save the data to a JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2)
        
        print(f"Raw API response saved to {filepath}")
        return filepath
        
    def execute_query(self, query, endpoint=None):
        """Execute a query against the Silent Push API.
        
        Args:
            query: The query string to search for
            endpoint: Optional API endpoint to use (should start with a leading slash)
                    (defaults to /explore/scandata/search/raw)
            
        Returns:
            List of results from the query
        """
        if not self.api_key:
            print("Error: SilentPush API key is required to execute queries.")
            return []
        
        # Use the provided endpoint or default to scandata/search/raw
        if endpoint is None:
            endpoint = "/explore/scandata/search/raw"
        
        # Ensure endpoint starts with a slash (as shown in the documentation)
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"
        
        # Set up the API endpoint - remove any trailing slash from base_url
        base_url = self.base_url.rstrip('/')
        api_endpoint = f"{base_url}{endpoint}"
        
        # Set up the headers with API key authentication
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Determine if this is a domain search endpoint that uses GET with query parameters
        is_get_request = False
        if '/explore/domain/search' in endpoint or '/explore/padns/search' in endpoint:
            is_get_request = True
            print("Using GET request method with query parameters")
        else:
            # For scandata and other endpoints that use POST with query in body
            formatted_query = self.prepare_query(query)
            if formatted_query != query:
                print(f"Query reformatted for SilentPush compatibility: {formatted_query}")
            query = formatted_query
        
        # Parse parameters for GET requests
        params = {}
        if is_get_request:
            # Parse query string into parameters for GET request
            if query:
                # Split by & to get individual parameters
                param_pairs = query.split('&')
                for pair in param_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)  # Split only on first =
                        params[key.strip()] = value.strip()
                    else:
                        # Handle cases where there's a key without a value
                        params[pair.strip()] = ''
            
            # Add common parameters
            params["limit"] = 1000
            params["with_metadata"] = 1
        else:
            # Set up the request payload for POST requests
            params = {
                "limit": 1000,
                "skip": 0,
                "with_metadata": 1
            }
        
        try:
            if is_get_request:
                print(f"Executing SilentPush GET query on endpoint: {endpoint}")
                print(f"Parameters: {params}")
            else:
                print(f"Executing SilentPush POST query: {query}")
                print(f"Using endpoint: {endpoint}")
            
            print(f"Using timeouts: connect={self.connect_timeout}s, read={self.read_timeout}s")
            
            # Include explicit timeout values
            timeout = (self.connect_timeout, self.read_timeout)  # (connect_timeout, read_timeout)
            
            response = None
            
            if is_get_request:
                # Create a prepared request for GET to inspect before sending
                prepared_request = requests.Request(
                    'GET', 
                    api_endpoint,
                    headers=headers,
                    params=params
                ).prepare()
                
                # Print the request details for debugging
                print("\n=== PREPARED REQUEST DETAILS ===")
                print(f"URL: {prepared_request.url}")
                print("Headers:")
                for header, value in prepared_request.headers.items():
                    # Hide the actual API key for security
                    if header.lower() == 'x-api-key':
                        print(f"  {header}: {'*' * 10}")
                    else:
                        print(f"  {header}: {value}")
                
                print("GET Parameters:")
                print(params)
                print("=== END OF REQUEST DETAILS ===\n")
                
                # Send the actual GET request
                response = requests.get(
                    api_endpoint, 
                    headers=headers, 
                    params=params,
                    timeout=timeout
                )
            else:
                # Set up the request payload for POST according to the API documentation format
                payload = {
                    "query": query,  # The SPQL query as a single string in JSON format
                    # Uncomment and customize if you want specific fields
                    # "fields": ["domain", "scan_date", "registrar", "name", "email", "organization"],
                    "sort": ["scan_date/desc"]  # Sort by scan_date in descending order
                }
                
                # Create a prepared request for POST to inspect before sending
                prepared_request = requests.Request(
                    'POST', 
                    api_endpoint,
                    headers=headers,
                    json=payload,
                    params=params
                ).prepare()
                
                # Print the request details for debugging
                print("\n=== PREPARED REQUEST DETAILS ===")
                print(f"URL: {prepared_request.url}")
                print("Headers:")
                for header, value in prepared_request.headers.items():
                    # Hide the actual API key for security
                    if header.lower() == 'x-api-key':
                        print(f"  {header}: {'*' * 10}")
                    else:
                        print(f"  {header}: {value}")
                
                # Parse body back to JSON for pretty printing
                print("Body:")
                try:
                    body_json = json.loads(prepared_request.body.decode('utf-8'))
                    print(json.dumps(body_json, indent=2))
                except:
                    print(f"  {prepared_request.body}")
                print("=== END OF REQUEST DETAILS ===\n")
                
                # Send the actual POST request
                response = requests.post(
                    api_endpoint, 
                    headers=headers, 
                    json=payload, 
                    params=params,
                    timeout=timeout
                )
            
            # Always save the raw response for debugging
            try:
                response_data = response.json() if response.text else {"empty_response": True}
                print("\n=== RESPONSE DETAILS ===")
                print(f"Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print("Response Body (truncated):")
                print(f"{json.dumps(response_data)[:1000]}..." if len(json.dumps(response_data)) > 1000 else json.dumps(response_data))
                print("=== END OF RESPONSE DETAILS ===\n")
            except json.JSONDecodeError:
                response_data = {"text": response.text, "not_json": True}
                print("\n=== RESPONSE DETAILS ===")
                print(f"Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print("Response Body (non-JSON, truncated):")
                print(f"{response.text[:1000]}..." if len(response.text) > 1000 else response.text)
                print("=== END OF RESPONSE DETAILS ===\n")
                
            self.save_raw_response(query, response_data)
            
            if response.status_code == 200:
                # Special handling for the nested response structure
                if "response" in response_data and isinstance(response_data["response"], dict):
                    response_obj = response_data["response"]
                    
                    # Check for scandata_raw in the response object
                    if "scandata_raw" in response_obj:
                        results = response_obj["scandata_raw"]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    elif "records" in response_obj:
                        # Handle domain search results
                        results = response_obj["records"]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    # Check for domain certificates
                    elif "domain_certificates" in response_obj:
                        results = response_obj["domain_certificates"]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    # Check for domain information
                    elif "domaininfo" in response_obj:
                        # Handle direct domaininfo object and array cases
                        domaininfo = response_obj["domaininfo"]
                        if isinstance(domaininfo, list):
                            results = domaininfo
                        else:
                            results = [domaininfo]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    # Handle other potential response types
                    elif "whois" in response_obj:
                        results = response_obj["whois"]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    # Check for nschanges
                    elif "nschanges" in response_obj:
                        results = [response_obj["nschanges"]]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    # Check for domain infratag
                    elif "infratag" in response_obj:
                        results = [response_obj["infratag"]]
                        print(f"Query executed successfully. Retrieved {len(results)} results.")
                        return results
                    # Check for error in the response object
                    elif "error" in response_obj:
                        error_msg = response_obj.get("error", "Unknown error")
                        print(f"API returned an error: {error_msg}")
                        return []
                    else:
                        # Generic handler for other response types
                        print(f"Query executed successfully but response format not specifically handled.")
                        print(f"Response structure: {self._describe_structure(response_obj)}")
                        # Try to return any array or object we find
                        for key, value in response_obj.items():
                            if isinstance(value, list) and value:
                                print(f"Returning array from key: {key}")
                                return value
                            elif isinstance(value, dict):
                                print(f"Returning dict from key: {key} as a list")
                                return [value]
                        # If we didn't find any arrays, return the whole response object as a list
                        print("Returning whole response object as a list")
                        return [response_obj]
                        
                # For non-nested or direct response arrays
                if "results" in response_data:
                    results = response_data["results"]
                    print(f"Query executed successfully. Retrieved {len(results)} results.")
                    return results
                else:
                    print(f"Query executed successfully but couldn't find results in the expected format.")
                    print(f"Response data structure: {self._describe_structure(response_data)}")
                    # Try to return the response data itself if it contains useful information
                    if isinstance(response_data, dict) and response_data:
                        return [response_data]
                    return []
            else:
                # For non-200 responses, still save what we can
                self.save_raw_response(query, response_data, 
                                     f"HTTP Error: {response.status_code}")
                print(f"Error executing query: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout as e:
            # Handle timeout specifically
            self.save_raw_response(query, 
                                  {"exception_occurred": True, "timeout_error": True},
                                  f"Timeout error: {str(e)} - Consider increasing timeout values.")
            print(f"Timeout when executing SilentPush query: {str(e)}")
            print("Consider increasing the timeout values with set_timeouts() method.")
            return []
        except requests.exceptions.ConnectionError as e:
            # Handle connection errors specifically
            self.save_raw_response(query, 
                                  {"exception_occurred": True, "connection_error": True},
                                  f"Connection error: {str(e)} - Check network connectivity.")
            print(f"Connection error when executing SilentPush query: {str(e)}")
            print("Check network connectivity and ensure you can reach api.silentpush.com")
            return []
        except Exception as e:
            # Save information about the exception
            self.save_raw_response(query, {"exception_occurred": True}, str(e))
            print(f"Exception when executing SilentPush query: {str(e)}")
            return []
            
    def _describe_structure(self, data, max_depth=3, current_depth=0):
        """Describe the structure of a complex JSON response to help with debugging.
        
        Args:
            data: The data structure to describe
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
            
        Returns:
            String description of the data structure
        """
        if current_depth >= max_depth:
            return "... (max depth reached)"
            
        if isinstance(data, dict):
            result = "{"
            items = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    items.append(f'"{key}": {self._describe_structure(value, max_depth, current_depth + 1)}')
                else:
                    items.append(f'"{key}": {type(value).__name__}')
            result += ", ".join(items)
            result += "}"
            return result
        elif isinstance(data, list):
            if len(data) == 0:
                return "[]"
            else:
                first_item = data[0]
                if isinstance(first_item, (dict, list)):
                    return f"[{self._describe_structure(first_item, max_depth, current_depth + 1)}, ...]"
                else:
                    return f"[{type(first_item).__name__}, ...]"
        else:
            return type(data).__name__
    
    def download_screenshot(self, uuid, output_path):
        """Download the screenshot for a specific scan if available.
        
        Args:
            uuid: UUID of the task
            output_path: Path to save the screenshot
            
        Returns:
            Boolean indicating success or failure
        """
        if not self.api_key:
            print("Error: SilentPush API key is required to download screenshots.")
            return False
        
        # For WHOIS queries, screenshots are not applicable
        # This is a placeholder for when we implement other query types
        print(f"SilentPush screenshot download not applicable for UUID: {uuid} (WHOIS data doesn't have screenshots)")
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
        """Extract Indicators of Compromise (IOCs) from Silent Push results.
        
        Args:
            results: List of Silent Push result objects
            
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
            "server_details": set(),
            "emails": set(),
            "registrars": set(),
            "nameservers": set(),
            "organizations": set()
        }
        
        for result in results:
            # For all Silent Push results, try to extract a scan ID/reference
            if "request_id" in result:
                iocs["scan_ids"].add(result["request_id"])
            elif "uuid" in result:
                iocs["scan_ids"].add(result["uuid"])
                
            # Try to extract scan dates from any date fields
            if "scan_date" in result:
                iocs["scan_dates"].add(result["scan_date"])
            elif "created_at" in result:
                iocs["scan_dates"].add(result["created_at"])
                
            # Extract different IOCs based on the type of Silent Push result
            
            # General domain extraction (present in most Silent Push results)
            if "domain" in result:
                if isinstance(result["domain"], str):
                    iocs["domains"].add(result["domain"])
            
            # Handle "host" field which is used in some Silent Push results (e.g. domain search)
            if "host" in result:
                if isinstance(result["host"], str):
                    iocs["domains"].add(result["host"])
                    
            # Extract domain details from whois results
            if "whois" in result:
                whois_data = result["whois"]
                if isinstance(whois_data, dict):
                    # Extract registrar information
                    if "registrar" in whois_data:
                        iocs["registrars"].add(whois_data["registrar"])
                    
                    # Extract nameservers
                    if "nameservers" in whois_data and isinstance(whois_data["nameservers"], list):
                        for ns in whois_data["nameservers"]:
                            if isinstance(ns, str):
                                iocs["nameservers"].add(ns)
                    
                    # Extract emails
                    if "emails" in whois_data and isinstance(whois_data["emails"], list):
                        for email in whois_data["emails"]:
                            if isinstance(email, str):
                                iocs["emails"].add(email)
            
            # Extract data from domain search results
            if "records" in result and isinstance(result["records"], list):
                for record in result["records"]:
                    if isinstance(record, dict):
                        if "name" in record and isinstance(record["name"], str):
                            iocs["domains"].add(record["name"])
                        if "email" in record and isinstance(record["email"], str):
                            iocs["emails"].add(record["email"])
                        if "organization" in record and isinstance(record["organization"], str):
                            iocs["organizations"].add(record["organization"])
            
            # Extract data from webscan results
            if "webscan" in result:
                webscan = result["webscan"]
                if isinstance(webscan, dict):
                    # Extract title
                    if "title" in webscan and isinstance(webscan["title"], str):
                        iocs["page_titles"].add(webscan["title"])
                    
                    # Extract server information
                    if "server" in webscan and isinstance(webscan["server"], str):
                        iocs["server_details"].add(webscan["server"])
                    
                    # Extract URLs
                    if "url" in webscan and isinstance(webscan["url"], str):
                        iocs["urls"].add(webscan["url"])
                        
            # Extract IP addresses from various locations
            if "ip" in result:
                if isinstance(result["ip"], str):
                    iocs["ips"].add(result["ip"])
            
            if "ips" in result and isinstance(result["ips"], list):
                for ip in result["ips"]:
                    if isinstance(ip, str):
                        iocs["ips"].add(ip)
                        
            # Extract DNS resolution data
            if "dns" in result and isinstance(result["dns"], dict):
                dns_data = result["dns"]
                
                # A records usually contain IP addresses
                if "a" in dns_data and isinstance(dns_data["a"], list):
                    for ip in dns_data["a"]:
                        if isinstance(ip, str):
                            iocs["ips"].add(ip)
                
                # NS records contain nameservers
                if "ns" in dns_data and isinstance(dns_data["ns"], list):
                    for ns in dns_data["ns"]:
                        if isinstance(ns, str):
                            iocs["nameservers"].add(ns)
                            
            # Extract URL from any URL field
            if "url" in result and isinstance(result["url"], str):
                iocs["urls"].add(result["url"])
                
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
            import csv
            
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
                    
                # Write emails with their scan IDs
                for email in iocs.get("emails", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'email', 'value': email, 'scan_id': scan_ids})
                
                # Write registrars with their scan IDs
                for registrar in iocs.get("registrars", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'registrar', 'value': registrar, 'scan_id': scan_ids})
                
                # Write nameservers with their scan IDs
                for nameserver in iocs.get("nameservers", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'nameserver', 'value': nameserver, 'scan_id': scan_ids})
                
                # Write organizations with their scan IDs
                for org in iocs.get("organizations", []):
                    scan_ids = ",".join(iocs.get("scan_ids", ["unknown"]))
                    writer.writerow({'ioc_type': 'organization', 'value': org, 'scan_id': scan_ids})
            
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
            import json
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