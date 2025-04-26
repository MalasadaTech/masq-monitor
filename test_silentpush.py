#!/usr/bin/env python3

import os
import json
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv
from silentpush_client import SilentPushClient
from masq_monitor import MasqMonitor

def prepare_request_only(api_key, query):
    """Prepare a request without sending it, for debugging purposes.
    
    Args:
        api_key: SilentPush API key
        query: The query string
        
    Returns:
        PreparedRequest object
    """
    base_url = "https://api.silentpush.com/api/v1"
    endpoint = f"{base_url}/merge-api/explore/scandata/search/raw"
    
    # Set up the headers with API key authentication
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Set up the request payload according to the API documentation format
    # {"query": "<query>", "fields":["<field1>","<field2>",...,"<fieldn>"], "sort": ["<field1>/<order>","<field2>/<order>",...,"<fieldn>/<order>"]}
    payload = {
        "query": query,  # The SPQL query as a single string in JSON format
        # Sort by scan_date in descending order
        "sort": ["scan_date/desc"]
    }
    
    # Define parameters for the API request
    params = {
        "limit": 1000,  # Maximum number of results to return
        "skip": 0,
        "with_metadata": 1  # Return metadata about the search
    }
    
    # Create a prepared request to inspect before sending
    prepared_request = requests.Request(
        'POST', 
        endpoint,
        headers=headers,
        json=payload,
        params=params
    ).prepare()
    
    return prepared_request

def main():
    """Test the SilentPush client with a WHOIS query."""
    
    # Load the API key from .env
    load_dotenv()
    silentpush_api_key = os.getenv("SILENTPUSH_API_KEY")
    
    if not silentpush_api_key:
        print("Error: SILENTPUSH_API_KEY not found in .env file.")
        print("Please add your SilentPush API key to the .env file.")
        return
    
    print("Testing SilentPush client with malasadatech-whois-test query...")
    
    # Initialize the MasqMonitor to access config and functions
    monitor = MasqMonitor(config_path="config.json")
    
    # Get the query from the config
    query_name = "malasadatech-whois-test"
    if query_name not in monitor.config["queries"]:
        print(f"Query '{query_name}' not found in configuration.")
        return
    
    query_config = monitor.config["queries"][query_name]
    query_string = query_config.get("query")
    
    if not query_string:
        print(f"No query string defined for '{query_name}'.")
        return
    
    print(f"Preparing request for query: {query_string}")
    
    # Demo adding date filtering - get WHOIS records from the last 90 days
    # Format: YYYY-MM-DD HH:MM:SS
    ninety_days_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
    date_filtered_query = f"{query_string} AND scan_date >= \"{ninety_days_ago}\""
    print(f"Adding date filter: records from last 90 days ({ninety_days_ago})")
    
    # Prepare requests for both regular query and date-filtered query
    prepared_request = prepare_request_only(silentpush_api_key, query_string)
    prepared_request_with_date = prepare_request_only(silentpush_api_key, date_filtered_query)
    
    # Create a directory for debug info if it doesn't exist
    debug_dir = Path("cached_results")
    debug_dir.mkdir(exist_ok=True)
    
    # Save the prepared request details to files
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = debug_dir / f"prepared_request_{timestamp}.json"
    debug_file_with_date = debug_dir / f"prepared_request_with_date_{timestamp}.json"
    
    # Print the regular query details to console
    print("\n=== PREPARED REQUEST DETAILS (Regular Query) ===")
    print(f"URL: {prepared_request.url}")
    print("Headers:")
    for header, value in prepared_request.headers.items():
        if header.lower() == 'x-api-key':
            print(f"  {header}: {'*' * 10}")
        else:
            print(f"  {header}: {value}")
    
    print("Body:")
    try:
        body_text = prepared_request.body.decode('utf-8')
        body_json = json.loads(body_text)
        pretty_json = json.dumps(body_json, indent=2)
        print(pretty_json)
        
        # Save the details to a file
        debug_info = {
            "url": prepared_request.url,
            "headers": {k: (v if k.lower() != 'x-api-key' else '*****') for k, v in prepared_request.headers.items()},
            "body": body_json,
            "body_raw": body_text,
            "query_name": query_name,
            "query_string": query_string
        }
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, indent=2)
        
    except Exception as e:
        print(f"  Error parsing request body: {e}")
        print(f"  Raw body: {prepared_request.body}")
    
    # Print the date-filtered query details
    print("\n=== PREPARED REQUEST DETAILS (With Date Filter) ===")
    print(f"URL: {prepared_request_with_date.url}")
    print("Body:")
    try:
        body_text = prepared_request_with_date.body.decode('utf-8')
        body_json = json.loads(body_text)
        pretty_json = json.dumps(body_json, indent=2)
        print(pretty_json)
        
        # Save the details to a file
        debug_info = {
            "url": prepared_request_with_date.url,
            "headers": {k: (v if k.lower() != 'x-api-key' else '*****') for k, v in prepared_request_with_date.headers.items()},
            "body": body_json,
            "body_raw": body_text,
            "query_name": query_name,
            "query_string": date_filtered_query
        }
        
        with open(debug_file_with_date, 'w', encoding='utf-8') as f:
            json.dump(debug_info, f, indent=2)
        
    except Exception as e:
        print(f"  Error parsing request body: {e}")
        print(f"  Raw body: {prepared_request_with_date.body}")
    
    print("=== END OF REQUEST DETAILS ===\n")
    
    # Ask user which query to execute
    choice = input("Execute query? [1] Regular, [2] With date filter, [any other key] Cancel: ")
    
    if choice == "1":
        print("\n=== EXECUTING REGULAR QUERY ===")
        query_to_execute = query_string
    elif choice == "2":
        print("\n=== EXECUTING DATE-FILTERED QUERY ===")
        query_to_execute = date_filtered_query
    else:
        print("Query execution cancelled.")
        return
    
    # Now execute the selected query using the SilentPushClient
    client = SilentPushClient(api_key=silentpush_api_key)
    
    # Set longer timeouts if needed
    client.set_timeouts(connect_timeout=60, read_timeout=180)  # 1 min connect, 3 min read
    
    results = client.execute_query(query_to_execute)
    
    if results:
        print(f"\nReceived {len(results)} results.")
        
        # Save the results
        results_file = debug_dir / f"{query_name}_{timestamp}_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"Saved results to {results_file}")
        
        # Print the first result to see the structure
        print("\nSample result structure:")
        print(json.dumps(results[0], indent=2)[:1000] + "..." if len(json.dumps(results[0], indent=2)) > 1000 else json.dumps(results[0], indent=2))
    else:
        print("No results received or an error occurred.")
        print("Check the saved response files in cached_results directory for more details.")

if __name__ == "__main__":
    main()