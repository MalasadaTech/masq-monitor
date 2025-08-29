#!/usr/bin/env python3
"""
Extension: Extract Mega.nz URLs and Passwords from URLScan Results
This extension takes scan results and extracts Mega.nz download links and passwords

Features:
- Extracts Mega.nz URLs from primary request responses
- Extracts associated passwords from the same responses
- Supports caching responses to avoid repeated requests
- Saves results to CSV format with defanged URLs for safety
"""

import os
import csv
import re
import requests
import time
import json
import argparse
import logging
import random
from pathlib import Path
from urllib.parse import urlparse, urldefrag

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MegaNZ_Extractor')

# By default, only show minimal logging in production
VERBOSE = False

# API rate limiting settings
BASE_DELAY = 2.0  # Base delay between API calls in seconds
MAX_RETRIES = 3   # Maximum number of retries for rate-limited requests
BACKOFF_FACTOR = 2.0  # Exponential backoff multiplier

def wait_for_api_call():
    """Add a delay before making API calls to respect rate limits"""
    # Add some jitter to avoid thundering herd
    delay = BASE_DELAY + random.uniform(0, 1.0)
    log_info(f"Waiting {delay:.1f} seconds before API call...")
    time.sleep(delay)

def handle_rate_limit_retry(func, *args, **kwargs):
    """
    Handle API calls with exponential backoff for rate limits
    
    Args:
        func: Function to call
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Result of the function call, or None if all retries failed
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                # Exponential backoff with jitter
                wait_time = (BACKOFF_FACTOR ** attempt) * BASE_DELAY + random.uniform(0, 2.0)
                log_important(f"Rate limited, retrying in {wait_time:.1f} seconds (attempt {attempt + 1}/{MAX_RETRIES + 1})...")
                time.sleep(wait_time)
            else:
                # Always wait before the first attempt
                wait_for_api_call()
            
            result = func(*args, **kwargs)
            if result is not None:
                return result
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                if attempt < MAX_RETRIES:
                    log_important(f"Rate limited (429), will retry...")
                    continue
                else:
                    log_important(f"Rate limited after {MAX_RETRIES} retries, giving up")
                    return None
            else:
                # Other HTTP errors, don't retry
                log_important(f"HTTP error {e.response.status_code}: {e}")
                return None
        except Exception as e:
            log_important(f"Unexpected error: {e}")
            return None
    
    return None

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
    scan_ids = []
    
    if not iocs_dir.exists():
        log_important(f"IOCs directory not found: {iocs_dir}")
        return scan_ids
    
    # Look for scan_ids.csv files with dynamic naming
    scan_ids_files = list(iocs_dir.glob("*scan_ids.csv"))
    
    if not scan_ids_files:
        log_important(f"No scan_ids.csv files found in {iocs_dir}")
        return scan_ids
    
    # Use the first scan_ids file found
    scan_ids_file = scan_ids_files[0]
    
    try:
        with open(scan_ids_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'scan_ids' in row and row['scan_ids']:
                    scan_ids.append(row['scan_ids'])
        log_info(f"Extracted {len(scan_ids)} scan IDs from {scan_ids_file}")
    except Exception as e:
        log_important(f"Error reading scan IDs file: {e}")
    
    return scan_ids

def get_urlscan_result(scan_id, cache_dir=None):
    """
    Get URLScan result data for a scan ID, with optional caching
    
    Args:
        scan_id: The URLScan scan ID
        cache_dir: Optional directory for caching results
        
    Returns:
        Dict containing the URLScan result data, or None if error
    """
    if cache_dir:
        cache_file = Path(cache_dir) / f"result_{scan_id}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    log_info(f"Using cached result for scan {scan_id}")
                    return json.load(f)
            except Exception as e:
                log_info(f"Error reading cached result: {e}")
    
    # Use retry mechanism for API call
    def _fetch_result():
        url = f"https://urlscan.io/api/v1/result/{scan_id}"
        log_info(f"Fetching URLScan result for scan {scan_id}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        result_data = response.json()
        
        # Cache the result if cache_dir is provided
        if cache_dir:
            Path(cache_dir).mkdir(exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2)
            log_info(f"Cached result for scan {scan_id}")
        
        return result_data
    
    return handle_rate_limit_retry(_fetch_result)

def find_primary_request_hash(result_data):
    """
    Find the hash of the primary request from URLScan result data
    
    Args:
        result_data: URLScan result data dict
        
    Returns:
        String hash of primary request, or None if not found
    """
    try:
        requests_data = result_data.get('data', {}).get('requests', [])
        for request_item in requests_data:
            request_info = request_item.get('request', {})
            if request_info.get('primaryRequest', False):
                # The hash is inside the response object
                response_info = request_item.get('response', {})
                response_hash = response_info.get('hash')
                if response_hash:
                    log_info(f"Found primary request hash: {response_hash}")
                    return response_hash
        
        log_info("No primary request found in result data")
        return None
        
    except Exception as e:
        log_important(f"Error finding primary request hash: {e}")
        return None

def get_response_content(response_hash, cache_dir=None):
    """
    Get response content for a given hash, with optional caching
    
    Args:
        response_hash: The response hash
        cache_dir: Optional directory for caching responses
        
    Returns:
        String containing response content, or None if error
    """
    if cache_dir:
        cache_file = Path(cache_dir) / f"response_{response_hash}.txt"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    log_info(f"Using cached response for hash {response_hash}")
                    return f.read()
            except Exception as e:
                log_info(f"Error reading cached response: {e}")
    
    # Use retry mechanism for API call
    def _fetch_response():
        url = f"https://urlscan.io/responses/{response_hash}/"
        log_info(f"Fetching response content for hash {response_hash}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
        
        # Cache the response if cache_dir is provided
        if cache_dir:
            Path(cache_dir).mkdir(exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
            log_info(f"Cached response for hash {response_hash}")
        
        return content
    
    return handle_rate_limit_retry(_fetch_response)

def extract_mega_nz_data(html_content):
    """
    Extract Mega.nz URLs and passwords from HTML content
    
    Args:
        html_content: HTML content as string
        
    Returns:
        List of dicts containing extracted data
    """
    results = []
    
    # Pattern to extract Mega.nz URL from input field with id="txtfile"
    mega_url_pattern = r'id=["\']txtfile["\'][^>]*value=["\']([^"\']*mega\.nz[^"\']*)["\']'
    mega_urls = re.findall(mega_url_pattern, html_content, re.IGNORECASE)
    
    # Pattern to extract password from text like "Password is : 2025"
    password_pattern = r'Password\s+is\s*:\s*([^\s<]+)'
    passwords = re.findall(password_pattern, html_content, re.IGNORECASE)
    
    # Combine URLs and passwords
    for i, url in enumerate(mega_urls):
        password = passwords[i] if i < len(passwords) else ""
        
        # Parse URL to get components
        parsed_url = urlparse(url)
        defanged_url = defang_url(url)
        
        result = {
            'mega_url': url,
            'defanged_mega_url': defanged_url,
            'password': password,
            'domain': parsed_url.netloc,
            'path': parsed_url.path,
            'fragment': parsed_url.fragment
        }
        results.append(result)
        log_info(f"Extracted Mega.nz data: URL={defanged_url}, Password={password}")
    
    return results

def defang_url(url):
    """
    Defang a URL to make it safe for sharing
    
    Args:
        url: URL to defang
        
    Returns:
        Defanged URL string
    """
    if not url:
        return url
    
    # Replace http with hxxp and dots with [.]
    defanged = url.replace('http://', 'hxxp://').replace('https://', 'hxxps://')
    defanged = defanged.replace('.', '[.]')
    
    return defanged

def process_scan_results(run_dir, cache_responses=True, test_mode=False):
    """
    Process scan results to extract Mega.nz URLs and passwords
    
    Args:
        run_dir: The output directory from the masq-monitor run
        cache_responses: Whether to cache API responses
        test_mode: Whether to use test data instead of API calls
        
    Returns:
        List of extracted Mega.nz data
    """
    all_results = []
    
    if test_mode:
        log_important("Running in test mode with sample data")
        # Use the provided sample response
        sample_html = '''
        <input type="text" class="form-control" id="txtfile" value="https://mega.nz/file/EXAMPLE" style="font-size:18px;background: #D6DCE2;width: 90%;margin: 0 auto" />
        <p style="color: rgb(144 62 189);font-size: 30px;"> Password is : 2025</p>
        '''
        results = extract_mega_nz_data(sample_html)
        all_results.extend(results)
        return all_results
    
    # Extract scan IDs from the run directory
    scan_ids = extract_scan_ids(run_dir)
    if not scan_ids:
        log_important("No scan IDs found to process")
        return all_results
    
    log_important(f"Processing {len(scan_ids)} scan IDs with enhanced rate limiting (base delay: {BASE_DELAY}s)")
    
    # Set up cache directory if caching is enabled
    cache_dir = Path(run_dir) / "cache" if cache_responses else None
    
    for i, scan_id in enumerate(scan_ids, 1):
        log_important(f"Processing scan ID {i}/{len(scan_ids)}: {scan_id}")
        
        # Get URLScan result data
        result_data = get_urlscan_result(scan_id, cache_dir)
        if not result_data:
            log_important(f"Failed to get result data for scan {scan_id}, skipping")
            continue
        
        # Find primary request hash
        primary_hash = find_primary_request_hash(result_data)
        if not primary_hash:
            log_info(f"No primary request hash found for scan {scan_id}, skipping")
            continue
        
        # Get response content
        response_content = get_response_content(primary_hash, cache_dir)
        if not response_content:
            log_important(f"Failed to get response content for hash {primary_hash}, skipping")
            continue
        
        # Extract Mega.nz data
        results = extract_mega_nz_data(response_content)
        for result in results:
            result['scan_id'] = scan_id
            result['response_hash'] = primary_hash
        
        all_results.extend(results)
    
    return all_results

def save_results_to_csv(results, output_file):
    """
    Save extracted results to CSV file
    
    Args:
        results: List of result dictionaries
        output_file: Path to output CSV file
    """
    if not results:
        log_important("No results to save")
        return
    
    fieldnames = [
        'scan_id', 'response_hash', 'password', 'defanged_mega_url'
    ]
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                # Only write the requested fields
                filtered_result = {
                    'scan_id': result.get('scan_id', ''),
                    'response_hash': result.get('response_hash', ''),
                    'password': result.get('password', ''),
                    'defanged_mega_url': result.get('defanged_mega_url', '')
                }
                writer.writerow(filtered_result)
        
        log_important(f"Saved {len(results)} Mega.nz extractions to {output_file}")
        
    except Exception as e:
        log_important(f"Error saving results to CSV: {e}")

def main(run_dir_arg=None):
    """Main function for the extension
    
    Args:
        run_dir_arg: Optional run directory passed by masq-monitor framework
    """
    global VERBOSE
    
    if run_dir_arg is not None:
        # Called by masq-monitor framework
        VERBOSE = False  # Disable verbose logging when called by framework
        
        run_dir = Path(run_dir_arg)
        if not run_dir.exists():
            log_important(f"Run directory does not exist: {run_dir}")
            return
        
        # Process scan results
        results = process_scan_results(
            run_dir=run_dir,
            cache_responses=True,  # Enable caching by default
            test_mode=False
        )
        
        # Save results to CSV in the extensions subdirectory
        extensions_dir = run_dir / "extensions"
        extensions_dir.mkdir(exist_ok=True)
        output_file = extensions_dir / "mega_nz_extractions.csv"
        save_results_to_csv(results, output_file)
        
        log_important(f"Mega.nz extraction completed. Found {len(results)} items.")
    else:
        # Called from command line
        parser = argparse.ArgumentParser(description='Extract Mega.nz URLs and passwords from URLScan results')
        parser.add_argument('run_dir', help='Path to the masq-monitor run directory')
        parser.add_argument('--no-cache', action='store_true', help='Disable response caching')
        parser.add_argument('--test', action='store_true', help='Run in test mode with sample data')
        parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
        
        args = parser.parse_args()
        
        VERBOSE = args.verbose
        
        run_dir = Path(args.run_dir)
        if not run_dir.exists():
            log_important(f"Run directory does not exist: {run_dir}")
            return
        
        # Process scan results
        results = process_scan_results(
            run_dir=run_dir,
            cache_responses=not args.no_cache,
            test_mode=args.test
        )
        
        # Save results to CSV
        output_file = run_dir / "mega_nz_extractions.csv"
        save_results_to_csv(results, output_file)
        
        log_important(f"Mega.nz extraction completed. Found {len(results)} items.")

if __name__ == "__main__":
    main()