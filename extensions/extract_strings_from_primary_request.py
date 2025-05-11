#!/usr/bin/env python3
"""
Extension: Extract Strings from Primary Request
This extension takes scan IDs, fetches the corresponding URLScan results,
identifies the primary request, extracts its response, and looks for string matches.

Features:
- Extracts scan IDs from CSV files
- Identifies primary request in URLScan results 
- Fetches response data using the hash
- Matches configurable string patterns
- Saves results with defanged metadata to CSV
"""

import os
import csv
import re
import requests
import time
import json
import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('String_Extractor')

# By default, only show minimal logging in production
VERBOSE = False

def log_info(message):
    """Log info messages based on verbosity level"""
    if VERBOSE:
        logger.info(message)

def log_important(message):
    """Log important messages always"""
    logger.info(message)

def extract_scan_ids(run_dir):
    """
    Extract scan IDs from the iocs/scan_ids.csv file
    
    Args:
        run_dir: The output directory from the masq-monitor run
        
    Returns:
        List of scan IDs
    """
    iocs_dir = Path(run_dir) / "iocs"
    log_info(f"Looking for scan IDs in {iocs_dir}")
    
    if not iocs_dir.exists():
        logger.error(f"Error: Cannot find iocs directory in {run_dir}")
        return []
    
    # Look for any file ending with scan_ids.csv
    scan_ids_files = list(iocs_dir.glob("*scan_ids.csv"))
    
    if not scan_ids_files:
        logger.error(f"Error: Cannot find any scan_ids.csv files in {iocs_dir}")
        return []
    
    # Use the first scan_ids.csv file found
    scan_ids_file = scan_ids_files[0]
    log_info(f"Found scan IDs file: {scan_ids_file}")
        
    scan_ids = []
    try:
        with open(scan_ids_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            for row in reader:
                if row:  # Ensure row is not empty
                    scan_ids.append(row[0])
                    
        log_info(f"Found {len(scan_ids)} scan IDs to process")
        return scan_ids
    except Exception as e:
        logger.error(f"Error reading scan IDs: {e}")
        return []

def get_result_from_cache(scan_id, cache_dir):
    """
    Try to get the URLScan result data from the cache
    
    Args:
        scan_id: The URLScan scan ID
        cache_dir: Directory where results are cached
        
    Returns:
        The cached result data if available, or None if not found
    """
    result_cache_file = cache_dir / f"{scan_id}_results.json"
    if result_cache_file.exists():
        try:
            with open(result_cache_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            log_info(f"Using cached result data for scan {scan_id}")
            return content
        except Exception as e:
            logger.error(f"Error reading cached result for scan {scan_id}: {e}")
    return None

def save_result_to_cache(scan_id, result_data, cache_dir):
    """
    Save the result data to the cache
    
    Args:
        scan_id: The URLScan scan ID
        result_data: The result data to cache
        cache_dir: Directory where results should be cached
    """
    try:
        result_cache_file = cache_dir / f"{scan_id}_results.json"
        with open(result_cache_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f)
        log_info(f"Cached result data for scan {scan_id}")
    except Exception as e:
        logger.error(f"Error caching result data for scan {scan_id}: {e}")

def get_response_from_cache(hash_value, cache_dir):
    """
    Try to get the response data from the cache
    
    Args:
        hash_value: The hash of the request
        cache_dir: Directory where responses are cached
        
    Returns:
        The cached response data if available, or None if not found
    """
    response_cache_file = cache_dir / f"{hash_value}_response.json"
    if response_cache_file.exists():
        try:
            with open(response_cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
            log_info(f"Using cached response data for hash {hash_value}")
            return content
        except Exception as e:
            logger.error(f"Error reading cached response for hash {hash_value}: {e}")
    return None

def save_response_to_cache(hash_value, response_data, cache_dir):
    """
    Save the response data to the cache
    
    Args:
        hash_value: The hash of the request
        response_data: The response data to cache
        cache_dir: Directory where responses should be cached
    """
    try:
        response_cache_file = cache_dir / f"{hash_value}_response.json"
        with open(response_cache_file, 'w', encoding='utf-8') as f:
            f.write(response_data)
        log_info(f"Cached response data for hash {hash_value}")
    except Exception as e:
        logger.error(f"Error caching response data for hash {hash_value}: {e}")

def defang_url(url):
    """
    Defang a URL to make it safe for display/storage
    
    Args:
        url: The URL to defang
        
    Returns:
        Defanged URL
    """
    return url.replace('http', 'hxxp').replace('.', '[.]')

def defang_domain(domain):
    """
    Defang a domain to make it safe for display/storage
    
    Args:
        domain: The domain to defang
        
    Returns:
        Defanged domain
    """
    return domain.replace('.', '[.]')

def fetch_scan_result(scan_id, use_cache=True, cache_dir=None):
    """
    Fetch the scan result from URLScan.io API
    
    Args:
        scan_id: The URLScan scan ID
        use_cache: Whether to use caching
        cache_dir: Directory for cache
        
    Returns:
        The scan result data or None if failed
    """
    # Check cache first if using cache
    if use_cache and cache_dir:
        cached_result = get_result_from_cache(scan_id, cache_dir)
        if cached_result:
            return cached_result
    
    # Make API request if not found in cache
    api_url = f"https://urlscan.io/api/v1/result/{scan_id}/"
    
    try:
        # Introducing a small delay to avoid hitting rate limits
        time.sleep(1)
        
        log_info(f"Requesting result data for scan {scan_id} from urlscan.io")
        response = requests.get(api_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Error: Failed to retrieve results for scan {scan_id}, status code: {response.status_code}")
            return None
        
        result_data = response.json()
        
        # Cache the result if using cache
        if use_cache and cache_dir:
            save_result_to_cache(scan_id, result_data, cache_dir)
            
        return result_data
            
    except Exception as e:
        logger.error(f"Error fetching scan result for scan {scan_id}: {e}")
        return None

def find_primary_request(scan_result):
    """
    Find the primary request in the scan result
    
    Args:
        scan_result: The scan result data
        
    Returns:
        A tuple of (primary request data, request hash, task metadata) or (None, None, None) if not found
    """
    if not scan_result or 'data' not in scan_result:
        logger.error("Error: Invalid scan result data")
        return None, None, None
    
    try:
        # Extract the task metadata
        task_metadata = {
            'domain': scan_result.get('task', {}).get('domain', ''),
            'time': scan_result.get('task', {}).get('time', ''),
            'url': scan_result.get('task', {}).get('url', ''),
            'title': scan_result.get('page', {}).get('title', '')
        }
        
        # Find the primary request
        requests = scan_result.get('data', {}).get('requests', [])
        primary_request = None
        request_hash = None
        
        # First attempt: Look for primaryRequest: true
        for request in requests:
            if request.get('request', {}).get('primaryRequest', False) is True:
                primary_request = request
                request_hash = request.get('response', {}).get('hash')
                log_info(f"Found primary request with hash: {request_hash}")
                break
        
        # Second attempt: If not found, try other methods of determining the primary request
        if not primary_request or not request_hash:
            # Try the first Document type request
            for request in requests:
                if request.get('response', {}).get('type') == 'Document':
                    primary_request = request
                    request_hash = request.get('response', {}).get('hash')
                    log_info(f"Found primary request (Document type) with hash: {request_hash}")
                    break
        
        # Third attempt: If still not found, just use the first request
        if not primary_request or not request_hash:
            if requests:
                primary_request = requests[0]
                request_hash = primary_request.get('response', {}).get('hash')
                log_info(f"Using first request as primary with hash: {request_hash}")
        
        if not primary_request or not request_hash:
            logger.error("Error: Primary request not found in scan result")
            return None, None, None
            
        return primary_request, request_hash, task_metadata
        
    except Exception as e:
        logger.error(f"Error finding primary request: {e}")
        return None, None, None
    
    # # Hidden patterns ;-p
    # # Regular expression patterns for different variable declaration styles
    # # var style
    # default_patterns.append({
    #     "name": "var_token",
    #     "regex": r'var\s+token\s*=\s*["\']?([a-zA-Z0-9_]+:[a-zA-Z0-9_\-]+)["\']?'
    # })
    # default_patterns.append({
    #     "name": "var_chat_id",
    #     "regex": r'var\s+chat_id\s*=\s*["\']?([0-9]+)["\']?'
    # })
    
    # # const style - new patterns
    # default_patterns.append({
    #     "name": "const_bot_token",
    #     "regex": r'const\s+BOT_TOKEN\s*=\s*["\']([0-9]{8,10}:[a-zA-Z0-9_\-]{35,})["\']'
    # })
    # default_patterns.append({
    #     "name": "const_chat_id",
    #     "regex": r'const\s+CHAT_ID\s*=\s*["\']([0-9]+)["\']'
    # })

    # # Regular expression patterns for URL-encoded Telegram tokens
    # # Example: bot_token%20%3D%20%277815936282%3AAAFHQUk_PA-L1tK5rw8ogp7prGq3PjHs-Ck%27
    # # %20 = space, %3D = =, %27 = single quote, %3A = colon
    # default_patterns.append({
    #     "name": "url_encoded_bot_token",
    #     "regex": r'bot_token%20?%3D%20?%27?([0-9]{8,10}(?:%3A|:)[a-zA-Z0-9_\-]{35,})%27?'
    # })
    
    # # Example: chat_id%20%3D%20%277358717983%27
    # default_patterns.append({
    #     "name": "url_encoded_chat_id",
    #     "regex": r'chat_id%20?%3D%20?%27?([0-9]+)%27?'
    # })
    
    # # Non-URL encoded variants
    # default_patterns.append({
    #     "name": "bot_token",
    #     "regex": r'bot_token\s*=\s*["\']?([0-9]{8,10}:[a-zA-Z0-9_\-]{35,})["\']?'
    # })
    # default_patterns.append({
    #     "name": "chat_id",
    #     "regex": r'chat_id\s*=\s*["\']?([0-9]+)["\']?'
    # })
    
    # # Additional pattern for Telegram bot tokens alone (without var names)
    # default_patterns.append({
    #     "name": "telegram_bot_token",
    #     "regex": r'["\']?([0-9]{8,10}:[a-zA-Z0-9_\-]{35,})["\']?'
    # })
    
    # # URL-encoded Telegram bot token without the variable name
    # default_patterns.append({
    #     "name": "url_encoded_telegram_token",
    #     "regex": r'["\']?([0-9]{8,10}%3A[a-zA-Z0-9_\-]{35,})["\']?'
    # })
    
    # # Generic BOT_TOKEN and CHAT_ID patterns (case-insensitive)
    # default_patterns.append({
    #     "name": "generic_bot_token",
    #     "regex": r'(?:BOT_TOKEN|bot_token|Bot_Token)\s*[:=]\s*["\']?([0-9]{8,10}:[a-zA-Z0-9_\-]{35,})["\']?'
    # })
    # default_patterns.append({
    #     "name": "generic_chat_id",
    #     "regex": r'(?:CHAT_ID|chat_id|Chat_Id)\s*[:=]\s*["\']?([0-9]+)["\']?'
    # })
def fetch_request_response(request_hash, use_cache=True, cache_dir=None):
    """
    Fetch the response data for a request hash from URLScan.io
    
    Args:
        request_hash: The request hash
        use_cache: Whether to use caching
        cache_dir: Directory for cache
        
    Returns:
        The response data or None if failed
    """
    # Check cache first if using cache
    if use_cache and cache_dir:
        cached_response = get_response_from_cache(request_hash, cache_dir)
        if cached_response:
            return cached_response
    
    # Make API request if not found in cache
    response_url = f"https://urlscan.io/responses/{request_hash}"
    
    try:
        # Introducing a small delay to avoid hitting rate limits
        time.sleep(1)
        
        log_info(f"Requesting response data for hash {request_hash} from urlscan.io")
        response = requests.get(response_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Error: Failed to retrieve response for hash {request_hash}, status code: {response.status_code}")
            return None
        
        response_data = response.text
        
        # Cache the response if using cache
        if use_cache and cache_dir:
            save_response_to_cache(request_hash, response_data, cache_dir)
            
        return response_data
            
    except Exception as e:
        logger.error(f"Error fetching response data for hash {request_hash}: {e}")
        return None

def match_string_patterns(response_data, string_patterns):
    """
    Match string patterns in the response data
    
    Args:
        response_data: The response data to search in
        string_patterns: List of string patterns to match
        
    Returns:
        Dictionary of matched patterns and their matches
    """
    if not response_data:
        return {}
        
    matches = {}
    
    try:
        for pattern in string_patterns:
            pattern_name = pattern.get('name', 'unnamed')
            pattern_regex = pattern.get('regex')
            
            if not pattern_regex:
                logger.error(f"Error: Missing regex for pattern {pattern_name}")
                continue
                
            try:
                regex = re.compile(pattern_regex)
                found_matches = regex.findall(response_data)
                
                if found_matches:
                    matches[pattern_name] = found_matches
                    log_info(f"Found {len(found_matches)} matches for pattern {pattern_name}")
            except Exception as e:
                logger.error(f"Error matching pattern {pattern_name}: {e}")
        
        return matches
        
    except Exception as e:
        logger.error(f"Error matching string patterns: {e}")
        return {}

def save_matches(matches, scan_id, task_metadata, run_dir):
    """
    Save the matched strings to a CSV file
    
    Args:
        matches: Dictionary of matched patterns and their matches
        scan_id: The URLScan scan ID
        task_metadata: Metadata about the task
        run_dir: The output directory from the masq-monitor run
        
    Returns:
        Path to the output file
    """
    # Create extensions directory if it doesn't exist
    extensions_dir = Path(run_dir) / "extensions"
    extensions_dir.mkdir(exist_ok=True)
    
    # Path to output file
    output_file = extensions_dir / "string_matches_from_primary_request.csv"
    log_info(f"Saving string matches to {output_file}")
    
    # Defang the metadata
    defanged_metadata = {
        'domain': defang_domain(task_metadata.get('domain', '')),
        'url': defang_url(task_metadata.get('url', '')),
        'title': task_metadata.get('title', ''),
        'time': task_metadata.get('time', '')
    }
    
    try:
        # Check if the file exists to determine if we need to write the header
        file_exists = output_file.exists()
        
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header if file doesn't exist
            if not file_exists:
                writer.writerow([
                    "scan_id", "pattern_name", "matched_string", 
                    "domain", "url", "title", "time"
                ])
            
            # Write data
            rows_written = 0
            for pattern_name, pattern_matches in matches.items():
                for match in pattern_matches:
                    writer.writerow([
                        scan_id, 
                        pattern_name, 
                        match,
                        defanged_metadata['domain'],
                        defanged_metadata['url'],
                        defanged_metadata['title'],
                        defanged_metadata['time']
                    ])
                    rows_written += 1
            
            log_info(f"Wrote {rows_written} string matches to CSV")
                    
        return output_file
    except Exception as e:
        logger.error(f"Error saving string matches: {e}")
        return None

def load_string_patterns():
    """
    Load string patterns to match from configuration
    
    Returns:
        List of pattern objects with name and regex
    """
    # Define some default patterns
    default_patterns = [
        {
            "name": "email_address",
            "regex": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        },
        {
            "name": "api_key",
            "regex": r'(?:api|key|token|secret)(?:[\-_]?(?:key|token|secret))?[\-_]?[0-9a-zA-Z]{16,45}'
        },
        {
            "name": "aws_access_key",
            "regex": r'AKIA[0-9A-Z]{16}'
        },
        {
            "name": "jwt_token",
            "regex": r'eyJ[a-zA-Z0-9_-]{5,}\.eyJ[a-zA-Z0-9_-]{5,}\.[a-zA-Z0-9_-]{5,}'
        }
    ]
    


    # TODO: In the future, this could be loaded from a config file
    return default_patterns

def main(run_dir, use_cache=True, test_mode=False):
    """
    Main entry point for the extension
    
    Args:
        run_dir: The output directory from the masq-monitor run
        use_cache: Whether to use response caching
        test_mode: Whether to use test data instead of making real requests
    """
    log_important(f"Starting string extraction from primary requests for {run_dir}")
    
    # Convert string to Path if needed
    if isinstance(run_dir, str):
        run_dir = Path(run_dir)
    
    # Setup cache directory
    cache_dir = run_dir / "extensions" / "response_cache"
    if use_cache:
        cache_dir.mkdir(exist_ok=True, parents=True)
    
    # Load string patterns to match
    string_patterns = load_string_patterns()
    
    # Extract scan IDs from the iocs directory
    scan_ids = extract_scan_ids(run_dir)
    
    if not scan_ids and not test_mode:
        log_important("No scan IDs found, exiting")
        return
    
    # If no scan IDs found but in test mode, use a dummy scan ID
    if test_mode and not scan_ids:
        scan_ids = ["test_scan_id_1", "test_scan_id_2"]
        log_info(f"Using {len(scan_ids)} test scan IDs for test mode")
    
    # Process each scan ID
    total_matches = 0
    for scan_id in scan_ids:
        log_info(f"Processing scan ID: {scan_id}")
        
        if test_mode:
            # For test mode, create dummy data
            primary_request = {"primaryRequest": True}
            request_hash = "test_hash"
            task_metadata = {
                "domain": "example.com",
                "time": "2025-05-10T12:00:00.000Z",
                "url": "http://example.com/test",
                "title": "Test Page"
            }
            response_data = """
            This is a test response with some test data:
            Email: test@example.com
            API Key: api_key_1234567890abcdef
            JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
            """
        else:
            # Fetch scan result
            scan_result = fetch_scan_result(scan_id, use_cache, cache_dir)
            if not scan_result:
                continue
                
            # Find primary request
            primary_request, request_hash, task_metadata = find_primary_request(scan_result)
            if not primary_request or not request_hash:
                continue
                
            # Fetch response data
            response_data = fetch_request_response(request_hash, use_cache, cache_dir)
            if not response_data:
                continue
        
        # Match string patterns
        matches = match_string_patterns(response_data, string_patterns)
        
        # If matches found, save them
        match_count = sum(len(m) for m in matches.values())
        if match_count > 0:
            total_matches += match_count
            output_file = save_matches(matches, scan_id, task_metadata, run_dir)
            if output_file:
                log_info(f"Saved {match_count} matches for scan {scan_id}")
            else:
                logger.error(f"Failed to save matches for scan {scan_id}")
    
    # Final summary
    if total_matches > 0:
        log_important(f"Total matches found: {total_matches}")
    else:
        log_important("No matches found in any scans")
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract strings from primary requests in URLScan results")
    parser.add_argument("run_dir", nargs="?", help="Run directory containing scan results")
    parser.add_argument("--no-cache", action="store_true", help="Disable response caching")
    parser.add_argument("--test", action="store_true", help="Run in test mode using sample data")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        VERBOSE = True
        logger.debug("Debug logging enabled")
    
    if args.verbose:
        VERBOSE = True
        logger.info("Verbose logging enabled")
    
    if args.test:
        # In test mode, create a temporary directory if run_dir not provided
        if not args.run_dir:
            test_dir = Path("test_output")
            test_dir.mkdir(exist_ok=True)
            args.run_dir = test_dir
            
        # Create test iocs directory and scan_ids.csv for full testing
        iocs_dir = Path(args.run_dir) / "iocs"
        iocs_dir.mkdir(exist_ok=True, parents=True)
        
        # Create a test scan_ids.csv file
        test_scan_ids_file = iocs_dir / "scan_ids.csv"
        if not test_scan_ids_file.exists():
            with open(test_scan_ids_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["scan_id"])  # Header
                writer.writerow(["test_scan_id_1"])
                writer.writerow(["test_scan_id_2"])
        
        log_info(f"Created test environment in {args.run_dir}")
        
    if args.run_dir:
        try:
            main(args.run_dir, use_cache=not args.no_cache, test_mode=args.test)
        except Exception as e:
            logger.error(f"Unhandled exception: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        logger.error("Error: No run directory specified")
        logger.error("Usage: python extract_strings_from_primary_request.py <run_dir> [--no-cache] [--test] [--debug] [--verbose]")
        # 507f9beda6f4c92f844f522b36ec2774
