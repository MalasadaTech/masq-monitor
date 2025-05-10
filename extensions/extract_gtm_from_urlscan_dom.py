#!/usr/bin/env python3
"""
Extension: Extract Google Tag Manager IDs from URLScan DOM
This extension takes scan results and extracts Google Tag Manager IDs from the DOM

Features:
- Extracts GTM IDs from urlscan.io DOMs
- Supports caching DOMs to avoid repeated requests
- Includes test mode with hard-coded sample DOM
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

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('GTM_Extractor')

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


def get_dom_from_cache(scan_id, cache_dir):
    """
    Try to get the DOM from the cache
    
    Args:
        scan_id: The URLScan scan ID
        cache_dir: Directory where DOMs are cached
        
    Returns:
        The cached DOM content if available, or None if not found
    """
    dom_cache_file = cache_dir / f"{scan_id}_dom.html"
    if dom_cache_file.exists():
        try:
            with open(dom_cache_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            log_info(f"Using cached DOM for scan {scan_id}")
            return content
        except Exception as e:
            logger.error(f"Error reading cached DOM for scan {scan_id}: {e}")
    return None


def save_dom_to_cache(scan_id, dom_content, cache_dir):
    """
    Save the DOM content to the cache
    
    Args:
        scan_id: The URLScan scan ID
        dom_content: The DOM content to cache
        cache_dir: Directory where DOMs should be cached
    """
    try:
        dom_cache_file = cache_dir / f"{scan_id}_dom.html"
        with open(dom_cache_file, 'w', encoding='utf-8', errors='replace') as f:
            f.write(dom_content)
        log_info(f"Cached DOM for scan {scan_id}")
    except Exception as e:
        logger.error(f"Error caching DOM for scan {scan_id}: {e}")


def extract_gtm_ids_from_dom(scan_id, use_cache=True, cache_dir=None, test_mode=False):
    """
    Extract Google Tag Manager IDs from the DOM of a URLScan result
    
    Args:
        scan_id: The URLScan scan ID
        use_cache: Whether to use/save DOM cache
        cache_dir: Directory for DOM cache
        test_mode: If True, use a test DOM instead of making a real request
        
    Returns:
        List of Google Tag Manager IDs found
    """
    # Test mode with a sample DOM containing GTM IDs
    if test_mode:
        log_info(f"Using test mode for scan {scan_id}")
        # Sample DOM with a couple of GTM tags for testing
        test_dom = """
        <html>
        <body>
            <!-- Google Tag Manager (noscript) -->
            <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-ABC123"
            height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
            <!-- End Google Tag Manager (noscript) -->
            
            <h1>Test Page</h1>
            <p>This is a test page with GTM tags.</p>
            
            <!-- Another GTM tag for testing -->
            <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XYZ789"
            height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
        </body>
        </html>
        """
        pattern = r'https://www\.googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)'
        matches = re.findall(pattern, test_dom)
        
        if matches:
            unique_matches = list(set(matches))
            log_info(f"Found {len(unique_matches)} GTM ID(s) in test DOM for scan {scan_id}")
            return unique_matches
        else:
            log_info(f"No GTM IDs found in test DOM for scan {scan_id}")
            return []
    
    # Set up cache directory if using cache
    if use_cache and cache_dir is None:
        cache_dir = Path("extensions") / "dom_cache"
    
    if use_cache:
        cache_dir.mkdir(exist_ok=True, parents=True)
        # Try to get from cache first
        cached_content = get_dom_from_cache(scan_id, cache_dir)
        if cached_content:
            # Extract from cached content
            pattern = r'https://www\.googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)'
            matches = re.findall(pattern, cached_content)
            
            # Try alternative patterns if main pattern fails
            if not matches:
                alt_patterns = [
                    r"https://www\.googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)",
                    r'https://www.googletagmanager.com/ns.html\?id=(GTM-[A-Z0-9]+)',
                    r"GTM-[A-Z0-9]+"
                ]
                
                for pattern in alt_patterns:
                    matches = re.findall(pattern, cached_content)
                    if matches:
                        break
            
            if matches:
                unique_matches = list(set(matches))
                log_info(f"Found {len(unique_matches)} GTM ID(s) in cached DOM for scan {scan_id}")
                return unique_matches
            else:
                log_info(f"No GTM IDs found in cached DOM for scan {scan_id}")
                return []
    
    # If not using cache or not found in cache, make the request
    dom_url = f"https://urlscan.io/dom/{scan_id}/"
    
    try:
        # Introducing a small delay to avoid hitting rate limits
        time.sleep(1)
        
        # Request the DOM
        log_info(f"Requesting DOM for scan {scan_id} from urlscan.io")
        response = requests.get(dom_url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Error: Failed to retrieve DOM for scan {scan_id}, status code: {response.status_code}")
            return []
        
        # Cache the content if using cache
        if use_cache:
            save_dom_to_cache(scan_id, response.text, cache_dir)
            
        # Extract GTM IDs using regex pattern
        pattern = r'https://www\.googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)'
        matches = re.findall(pattern, response.text)
        
        # Try alternative patterns if main pattern fails
        if not matches:
            alt_patterns = [
                r"https://www\.googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)",
                r'https://www.googletagmanager.com/ns.html\?id=(GTM-[A-Z0-9]+)',
                r"GTM-[A-Z0-9]+"
            ]
            
            for pattern in alt_patterns:
                matches = re.findall(pattern, response.text)
                if matches:
                    break
        
        if matches:
            # Remove duplicates
            unique_matches = list(set(matches))
            log_info(f"Found {len(unique_matches)} GTM ID(s) in scan {scan_id}")
            return unique_matches
        else:
            log_info(f"No GTM IDs found in scan {scan_id}")
            return []
            
    except Exception as e:
        logger.error(f"Error extracting GTM IDs from scan {scan_id}: {e}")
        return []


def save_gtm_ids(gtm_ids, run_dir):
    """
    Save the extracted GTM IDs to a CSV file
    
    Args:
        gtm_ids: Dictionary mapping scan IDs to lists of GTM IDs
        run_dir: The output directory from the masq-monitor run
    """
    # Create extensions directory if it doesn't exist
    extensions_dir = Path(run_dir) / "extensions"
    extensions_dir.mkdir(exist_ok=True)
    
    # Path to output file
    output_file = extensions_dir / "gtm_ids_extracted_from_urlscan_dom.csv"
    log_info(f"Saving GTM IDs to {output_file}")
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(["scan_id", "gtm_id"])
            
            # Write data
            rows_written = 0
            for scan_id, ids in gtm_ids.items():
                for gtm_id in ids:
                    writer.writerow([scan_id, gtm_id])
                    rows_written += 1
            
            log_info(f"Wrote {rows_written} GTM IDs to CSV")
                    
        return output_file
    except Exception as e:
        logger.error(f"Error saving GTM IDs: {e}")
        return None


def main(run_dir, use_cache=True, test_mode=False):
    """
    Main entry point for the extension
    
    Args:
        run_dir: The output directory from the masq-monitor run
        use_cache: Whether to use DOM caching
        test_mode: Whether to use test DOM instead of making real requests
    """
    log_important(f"Starting GTM ID extraction for {run_dir}")
    
    # Convert string to Path if needed
    if isinstance(run_dir, str):
        run_dir = Path(run_dir)
    
    # Setup cache directory
    cache_dir = run_dir / "extensions" / "dom_cache"
    if use_cache:
        cache_dir.mkdir(exist_ok=True, parents=True)
    
    # Extract scan IDs from the iocs directory
    scan_ids = extract_scan_ids(run_dir)
    
    if not scan_ids and not test_mode:
        log_important("No scan IDs found, exiting")
        return
    
    # If no scan IDs found but in test mode, use a dummy scan ID
    if test_mode and not scan_ids:
        scan_ids = ["test_scan_id_1", "test_scan_id_2"]
        log_info(f"Using {len(scan_ids)} test scan IDs")
    
    # Extract GTM IDs for each scan
    gtm_ids = {}
    for scan_id in scan_ids:
        log_info(f"Processing scan ID: {scan_id}")
        ids = extract_gtm_ids_from_dom(scan_id, use_cache, cache_dir, test_mode)
        if ids:
            gtm_ids[scan_id] = ids
    
    # Save the results
    if gtm_ids:
        total_gtm_ids = sum(len(ids) for ids in gtm_ids.values())
        output_file = save_gtm_ids(gtm_ids, run_dir)
        if output_file:
            log_important(f"Extracted {total_gtm_ids} GTM ID(s) and saved to: {output_file}")
        else:
            log_important(f"Found {total_gtm_ids} GTM ID(s) but failed to save the results")
    else:
        log_important("No GTM IDs found in any scans")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract Google Tag Manager IDs from URLScan DOM")
    parser.add_argument("run_dir", nargs="?", help="Run directory containing scan results")
    parser.add_argument("--no-cache", action="store_true", help="Disable DOM caching")
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
        logger.error("Usage: python extract_gtm_from_urlscan_dom.py <run_dir> [--no-cache] [--test] [--debug] [--verbose]")