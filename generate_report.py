#!/usr/bin/env python3

import os
import json
import datetime
import importlib.util
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import jinja2
import re
from urllib.parse import urlparse

# Add debugging utilities
def debug_result_object(prefix, result_obj, max_depth=5):
    """Debug a result object by printing its structure.
    
    Args:
        prefix: A prefix to add to each debug line for context
        result_obj: The result object to debug
        max_depth: Maximum depth for nested objects
    """
    debug_file = Path("debug_output.log")
    with open(debug_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n{'='*80}\n")
        f.write(f"DEBUG {prefix} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*80}\n")
        f.write(f"Type: {type(result_obj)}\n")
        
        def print_obj(obj, curr_depth=0, max_len=100):
            if curr_depth >= max_depth:
                return "... (max depth reached)"
            
            if isinstance(obj, dict):
                result = "{\n"
                for k, v in obj.items():
                    if isinstance(v, (dict, list)) and curr_depth < max_depth - 1:
                        val_repr = print_obj(v, curr_depth + 1)
                    else:
                        try:
                            if isinstance(v, str) and len(v) > max_len:
                                val_repr = f"{v[:max_len]}... (truncated)"
                            else:
                                val_repr = repr(v)
                        except:
                            val_repr = "ERROR RENDERING VALUE"
                    
                    indent = "  " * (curr_depth + 1)
                    result += f"{indent}{repr(k)}: {val_repr},\n"
                result += "  " * curr_depth + "}"
                return result
            elif isinstance(obj, list):
                if not obj:
                    return "[]"
                result = "[\n"
                for item in obj[:10]:  # Limit to first 10 items
                    if isinstance(item, (dict, list)) and curr_depth < max_depth - 1:
                        item_repr = print_obj(item, curr_depth + 1)
                    else:
                        try:
                            if isinstance(item, str) and len(item) > max_len:
                                item_repr = f"{item[:max_len]}... (truncated)"
                            else:
                                item_repr = repr(item)
                        except:
                            item_repr = "ERROR RENDERING VALUE"
                    
                    indent = "  " * (curr_depth + 1)
                    result += f"{indent}{item_repr},\n"
                
                if len(obj) > 10:
                    indent = "  " * (curr_depth + 1)
                    result += f"{indent}... ({len(obj) - 10} more items)\n"
                result += "  " * curr_depth + "]"
                return result
            else:
                return repr(obj)
        
        f.write(print_obj(result_obj))
        f.write("\n")

def debug_template_context(template_name, context):
    """Debug the context passed to a template.
    
    Args:
        template_name: Name of the template being rendered
        context: The context dictionary passed to the template
    """
    debug_file = Path("debug_template.log")
    with open(debug_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n{'='*80}\n")
        f.write(f"TEMPLATE DEBUG - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*80}\n")
        f.write(f"Template: {template_name}\n")
        f.write(f"Context Keys:\n")
        
        # Print top-level context keys and types
        for key, value in context.items():
            if key == 'results':
                f.write(f"- {key}: {type(value)} with {len(value)} items\n")
                # Print the first result in detail
                if value and len(value) > 0:
                    f.write(f"  First result type: {type(value[0])}\n")
                    if isinstance(value[0], dict):
                        f.write("  First result keys:\n")
                        for result_key in value[0].keys():
                            f.write(f"    - {result_key}\n")
                    else:
                        f.write(f"  First result value: {repr(value[0])}\n")
            else:
                f.write(f"- {key}: {type(value)}\n")

def debug_html_output(html_content, output_path):
    """Debug the generated HTML output, focusing on table content.
    
    Args:
        html_content: The HTML content to analyze
        output_path: Path where the HTML was saved
    """
    debug_file = Path("debug_html.log")
    with open(debug_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n{'='*80}\n")
        f.write(f"HTML DEBUG - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*80}\n")
        f.write(f"Output path: {output_path}\n")
        
        # Check for table elements
        table_count = html_content.count('<table')
        f.write(f"Found {table_count} table elements\n")
        
        # Extract and show table content
        table_pattern = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL)
        tables = table_pattern.findall(html_content)
        
        for i, table_content in enumerate(tables[:3]):  # Limit to first 3 tables
            f.write(f"\nTable #{i+1} (truncated):\n")
            max_len = 500
            if len(table_content) > max_len:
                f.write(f"{table_content[:max_len]}... (truncated)\n")
            else:
                f.write(f"{table_content}\n")
        
        if len(tables) > 3:
            f.write(f"\n... ({len(tables) - 3} more tables)\n")
            
        # Also look specifically for result cards
        result_card_count = html_content.count('result-card')
        f.write(f"\nFound {result_card_count} result cards\n")
        
        # Count and extract platform-specific templates used
        platform_templates = re.findall(r'<!-- Begin template: (.*?) -->', html_content)
        f.write(f"\nPlatform templates used ({len(platform_templates)}):\n")
        for template in platform_templates:
            f.write(f"- {template}\n")

# Import template registry
def import_template_registry():
    """Import template registry module."""
    try:
        registry_path = "templates/template_registry.py"
        spec = importlib.util.spec_from_file_location("template_registry", registry_path)
        if spec and spec.loader:
            template_registry = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(template_registry)
            return template_registry
        else:
            print("Error: Failed to load template_registry.py specification")
            return None
    except Exception as e:
        print(f"Error importing template_registry.py: {e}")
        return None

class ReportGenerator:
    def __init__(self, config, output_dir):
        """Initialize the report generator with configuration.
        
        Args:
            config: Dictionary containing the configuration
            output_dir: Path to the output directory
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.tlp_levels = ["clear", "white", "green", "amber", "red"]
        self.debug_enabled = False
        
        # Import template registry
        self.template_registry = import_template_registry()
        
    def enable_debugging(self):
        """Enable debug logging."""
        self.debug_enabled = True
        print("Debug logging enabled - see debug_*.log files for details")
        
        # Clear out old debug files
        for debug_file in ["debug_output.log", "debug_template.log", "debug_html.log"]:
            with open(debug_file, 'w') as f:
                f.write(f"Debug log started at {datetime.datetime.now()}\n")

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

    def determine_tlp_level(self, query_name, requested_tlp=None):
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

    def _is_tlp_visible(self, item_tlp, report_tlp):
        """
        Determine if an item with a specific TLP level should be visible in a report with another TLP level.
        
        Args:
            item_tlp: TLP level of the item being checked
            report_tlp: TLP level of the report
        
        Returns:
            bool: True if the item should be visible, False otherwise
        """
        # Define TLP hierarchy
        tlp_order = {'clear': 1, 'white': 1, 'green': 2, 'amber': 3, 'red': 4}
        
        # Convert to lowercase for consistency
        item_tlp = item_tlp.lower() if item_tlp else 'clear'
        report_tlp = report_tlp.lower() if report_tlp else 'clear'
        
        # Get numeric values from the hierarchy
        item_level = tlp_order.get(item_tlp, 1)
        report_level = tlp_order.get(report_tlp, 4)
        
        # An item is visible if its TLP level is less than or equal to the report TLP level
        return item_level <= report_level

    def generate_html_report(self, results, query_name, output_dir, report_tlp="amber", timestamp=None):
        """Generate an HTML report from the results.
        
        Args:
            results: List of results from the query
            query_name: Name of the query
            output_dir: Directory to save the report
            report_tlp: TLP level for the report
            timestamp: Timestamp for the report
            
        Returns:
            Path to the generated report
        """
        # Define run_dir from output_dir to fix the undefined run_dir error
        run_dir = output_dir
        
        # Get query details
        query_config = self.config["queries"].get(query_name, {})
        query_string = query_config.get("query", "Unknown")
        
        # Process TLP levels for each component
        description = query_config.get("description", "")
        description_tlp = query_config.get("description_tlp_level", report_tlp)
        
        query_tlp = query_config.get("query_tlp_level", report_tlp)
        
        default_tlp = query_config.get("default_tlp_level", report_tlp)
        
        # Handle titles with TLP levels
        titles = query_config.get("titles", [{"title": f"Masquerade Monitor Report - {query_name}", "tlp_level": report_tlp}])
        filtered_titles = [item for item in titles if self._is_tlp_visible(item.get("tlp_level", default_tlp), report_tlp)]
        
        # Use the first visible title as the main title
        title = filtered_titles[0]["title"] if filtered_titles else f"Masquerade Monitor Report - {query_name}"
        
        # Filter notes based on TLP level
        all_notes = query_config.get("notes", [])
        if isinstance(all_notes, list):
            notes = [note["text"] for note in all_notes 
                    if self._is_tlp_visible(note.get("tlp_level", default_tlp), report_tlp)]
        else:
            # Handle legacy string format
            notes = [all_notes] if self._is_tlp_visible(default_tlp, report_tlp) else []
        
        # Filter references based on TLP level
        all_references = query_config.get("references", [])
        if isinstance(all_references, list):
            references = [ref["url"] for ref in all_references 
                        if self._is_tlp_visible(ref.get("tlp_level", default_tlp), report_tlp)]
        else:
            # Handle legacy string format
            references = [all_references] if self._is_tlp_visible(default_tlp, report_tlp) else []
        
        frequency = query_config.get("frequency", "N/A")
        frequency_tlp = query_config.get("frequency_tlp_level", default_tlp)
        
        priority = query_config.get("priority", "N/A")
        priority_tlp = query_config.get("priority_tlp_level", default_tlp)
        
        # Filter tags based on TLP level
        tags = query_config.get("tags", [])
        tags_tlp = query_config.get("tags_tlp_level", default_tlp)
        
        # Prepare template data
        template_loader = jinja2.FileSystemLoader(searchpath="./templates")
        template_env = jinja2.Environment(loader=template_loader)
        
        # Add template registry function to the template environment
        if self.template_registry and hasattr(self.template_registry, 'get_template_for_result'):
            template_env.globals['get_platform_template'] = self.template_registry.get_template_for_result
        
        # Use the base template instead of the full report template
        template = template_env.get_template("base_template.html")
        
        # Determine platform from query config
        platform = query_config.get("platform", "urlscan").lower()
        
        # Process results based on the platform type
        processed_results = []
        if platform == "silentpush":
            # For SilentPush responses, we need special handling
            # Check if this is a raw SilentPush API response with the standard structure
            if isinstance(results, dict) and "response" in results:
                response_obj = results["response"]
                
                # Check if this contains data in the nested structure
                if (isinstance(response_obj, dict) and 
                    "response" in response_obj and 
                    isinstance(response_obj["response"], dict) and 
                    "scandata_raw" in response_obj["response"]):
                    
                    # Extract records from the nested structure
                    sp_records = response_obj["response"]["scandata_raw"]
                    
                    if isinstance(sp_records, list):
                        # Process each record based on its data type
                        for record in sp_records:
                            if not isinstance(record, dict):
                                continue
                                
                            # Determine the data type based on the record fields
                            data_type = self._determine_silentpush_data_type(record)
                            
                            if data_type == "whois":
                                processed_result = self._process_silentpush_whois(record)
                            elif data_type == "webscan":
                                processed_result = self._process_silentpush_webscan(record)
                            else:
                                # Check if this is a domain search result
                                if "host" in record and ("asn_diversity" in record or "ip_diversity_all" in record):
                                    # For domain search, pass the raw record through without wrapping
                                    processed_result = record
                                else:
                                    # Generic fallback for unknown data types
                                    processed_result = {
                                        "data_type": "generic",
                                        "raw_data": record
                                    }
                                
                            processed_results.append(processed_result)
                        
                        if not processed_results:
                            # No valid records found in the expected structure
                            processed_results.append({
                                "data_type": "message",
                                "message": "No valid records found in the SilentPush response."
                            })
                    else:
                        # Couldn't find valid data list in the expected structure
                        processed_results.append({
                            "data_type": "message",
                            "message": "SilentPush response doesn't contain a valid list of records."
                        })
                else:
                    # This doesn't appear to be a standard response structure
                    processed_results.append({
                        "data_type": "message",
                        "message": "SilentPush response doesn't contain the expected data structure."
                    })
            elif isinstance(results, list):
                # Process individual SilentPush results (direct format)
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    
                    # DEBUG: Print the keys in the first result to understand what fields are available
                    if len(processed_results) == 0:
                        print(f"DEBUG: Keys in first result: {list(result.keys())}")
                    
                    # Check if this is a domain search result first
                    if "host" in result and ("asn_diversity" in result or "ip_diversity_all" in result):
                        # For domain search, pass the raw result through without wrapping
                        print(f"DEBUG: Found domain search result with host: {result.get('host')}")
                        processed_results.append(result)
                    else:
                        # Determine the data type based on the record fields for other types
                        data_type = self._determine_silentpush_data_type(result)
                        
                        if data_type == "whois":
                            processed_result = self._process_silentpush_whois(result)
                        elif data_type == "webscan":
                            processed_result = self._process_silentpush_webscan(result)
                        else:
                            # Generic fallback for unknown data types
                            processed_result = {
                                "data_type": "generic",
                                "raw_data": result
                            }
                            
                        processed_results.append(processed_result)
            else:
                # Unrecognized format
                processed_results.append({
                    "data_type": "message",
                    "message": "Unrecognized SilentPush data format."
                })
        else:
            # Process URLScan results (default)
            for result in results:
                # Defang URLs and domains if available
                if "page" in result and "url" in result["page"]:
                    result["defanged_url"] = self._defang_url(result["page"]["url"])
                if "page" in result and "domain" in result["page"]:
                    result["defanged_domain"] = self._defang_domain(result["page"]["domain"])
                    
                # Handle screenshots if available in the cached results
                if "task" in result and "uuid" in result["task"]:
                    uuid = result["task"]["uuid"]
                    result["local_screenshot"] = f"images/{uuid}.png"
                
                processed_results.append(result)

        # Use the provided timestamp or generate current time
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Debug processed results if debugging is enabled
        if self.debug_enabled:
            debug_result_object("Processed Results", processed_results)

        # Render the HTML report
        html_content = template.render(
            query_name=query_name,
            query_data=query_config,
            timestamp=current_timestamp,
            results=processed_results,
            username=self.config.get("report_username", ""),
            tlp_level=report_tlp,
            platform=platform,
            debug=False
        )
        
        # Debug template context if debugging is enabled
        if self.debug_enabled:
            debug_template_context("base_template.html", {
                "query_name": query_name,
                "query_data": query_config,
                "timestamp": current_timestamp,
                "results": processed_results,
                "username": self.config.get("report_username", ""),
                "tlp_level": report_tlp,
                "platform": platform,
                "debug": False
            })
        
        # Remove blank lines from HTML content
        html_content = "\n".join([line for line in html_content.split("\n") if line.strip()])
        
        # Extract the date/time group from the output directory
        dir_name = run_dir.name
        datetime_part = ""
        if "_" in dir_name:
            datetime_part = dir_name.split("_", 1)[1]
        
        # Include TLP level and datetime in the filename
        report_filename = f"report_{query_name}_{datetime_part}_TLP-{report_tlp}.html"
        report_path = run_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Debug HTML output if debugging is enabled
        if self.debug_enabled:
            debug_html_output(html_content, report_path)
        
        print(f"Report generated in {run_dir}")
        return report_path

    def test_report_generation(self, query_name, results, tlp_level=None):
        """Generate a test report using provided results without querying APIs.
        
        Args:
            query_name: Name of the query for metadata
            results: Platform results to use for the report
            tlp_level: Optional TLP level for the report
            
        Returns:
            Path to the generated report
        """
        print(f"Generating test report for '{query_name}'")
        
        # Enable debugging when using cached results
        if results:
            self.enable_debugging()
        
        # Determine the appropriate TLP level
        report_tlp = self.determine_tlp_level(query_name, tlp_level)
        print(f"Report TLP level: {report_tlp}")
        
        # Get query configuration and platform
        query_data = self.config["queries"].get(query_name, {})
        platform = query_data.get("platform", "urlscan")
        print(f"Using platform: {platform}")
        
        # Create a unique output directory for this test
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"{query_name}_{timestamp}_test"
        run_dir.mkdir(exist_ok=True)
        
        # Create images directory
        img_dir = run_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        # Handle Silent Push results specially to ensure proper table rendering
        if platform == "silentpush":
            # For all Silent Push results, we don't want to wrap them in a data_type container
            # Instead, pass them directly to the template so the template registry can identify the right template
            if isinstance(results, list):
                # The results are a list, we'll process them directly
                return self.generate_html_report(results, query_name, run_dir, report_tlp)
            else:
                # If it's not a list, wrap it in one for consistent handling
                return self.generate_html_report([results], query_name, run_dir, report_tlp)
        else:
            # For other platforms (like urlscan), use standard processing
            return self.generate_html_report(results, query_name, run_dir, report_tlp)

    def _determine_silentpush_data_type(self, record):
        """Determine the type of SilentPush data based on record fields.
        
        Args:
            record: A SilentPush record dictionary
            
        Returns:
            str: The identified data type (e.g., "whois", "webscan", etc.)
        """
        if not isinstance(record, dict):
            return "unknown"
            
        # Check for WHOIS data
        whois_indicators = ["registrar", "creation_date", "expiration_date", "registrant", "domain_status"]
        if any(indicator in record for indicator in whois_indicators) or record.get("datasource") == "whois":
            return "whois"
            
        # Check for WebScan data
        webscan_indicators = ["html_body_sha256", "favicon_md5", "htmltitle", "redirect"]
        if any(indicator in record for indicator in webscan_indicators) or record.get("datasource") == "webscan":
            return "webscan"
            
        # Check for domain search data
        if "host" in record and ("asn_diversity" in record or "ip_diversity_all" in record):
            return "domain_search"
            
        # Default unknown type
        return "unknown"
        
    def _process_silentpush_whois(self, record):
        """Process a SilentPush WHOIS record.
        
        Args:
            record: A SilentPush WHOIS record
            
        Returns:
            dict: A processed record with added metadata
        """
        # Create a copy to avoid modifying the original
        processed = dict(record)
        
        # Add the data type for template selection
        processed["data_type"] = "whois"
        
        # Extract and format relevant dates
        if "creation_date" in record and record["creation_date"]:
            try:
                # Handle Unix timestamp
                if isinstance(record["creation_date"], (int, float)):
                    processed["creation_date_formatted"] = datetime.datetime.fromtimestamp(
                        record["creation_date"]).strftime("%Y-%m-%d")
                else:
                    # Try to parse as ISO format
                    parsed_date = datetime.datetime.fromisoformat(record["creation_date"].replace('Z', '+00:00'))
                    processed["creation_date_formatted"] = parsed_date.strftime("%Y-%m-%d")
            except:
                processed["creation_date_formatted"] = str(record["creation_date"])
        
        # Process expiration date similarly
        if "expiration_date" in record and record["expiration_date"]:
            try:
                if isinstance(record["expiration_date"], (int, float)):
                    processed["expiration_date_formatted"] = datetime.datetime.fromtimestamp(
                        record["expiration_date"]).strftime("%Y-%m-%d")
                else:
                    parsed_date = datetime.datetime.fromisoformat(record["expiration_date"].replace('Z', '+00:00'))
                    processed["expiration_date_formatted"] = parsed_date.strftime("%Y-%m-%d")
            except:
                processed["expiration_date_formatted"] = str(record["expiration_date"])
        
        # Defang domains
        if "domain" in record:
            processed["defanged_domain"] = self._defang_domain(record["domain"])
            
        return processed
        
    def _process_silentpush_webscan(self, record):
        """Process a SilentPush WebScan record.
        
        Args:
            record: A SilentPush WebScan record
            
        Returns:
            dict: A processed record with added metadata
        """
        # Create a copy to avoid modifying the original
        processed = dict(record)
        
        # Add the data type for template selection
        processed["data_type"] = "webscan"
        
        # Store the original record as raw_record for template access
        processed["raw_record"] = record
        
        # Defang URLs and domains
        if "url" in record:
            processed["defanged_url"] = self._defang_url(record["url"])
            
        if "domain" in record:
            processed["defanged_domain"] = self._defang_domain(record["domain"])
            
        # Format scan date if present
        if "scan_date" in record and record["scan_date"]:
            try:
                # Handle Unix timestamp
                if isinstance(record["scan_date"], (int, float)):
                    processed["scan_date_formatted"] = datetime.datetime.fromtimestamp(
                        record["scan_date"]).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # Try to parse as ISO format
                    parsed_date = datetime.datetime.fromisoformat(record["scan_date"].replace('Z', '+00:00'))
                    processed["scan_date_formatted"] = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                processed["scan_date_formatted"] = str(record["scan_date"])
                
        return processed

    def generate_group_report(self, group_name, group_results, tlp_level=None):
        """Generate a combined HTML report for a group of queries.
        
        Args:
            group_name: Name of the query group
            group_results: Dictionary of results from each query in the group
            tlp_level: Optional TLP level for the report
            
        Returns:
            Path to the generated report
        """
        print(f"Generating combined report for query group '{group_name}'")
        
        # Get group configuration
        group_config = self.config["queries"].get(group_name, {})
        
        # Create a unique output directory for this group report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"{group_name}_{timestamp}"
        run_dir.mkdir(exist_ok=True)
        
        # Create images directory
        img_dir = run_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        # Determine the appropriate TLP level
        report_tlp = self.determine_tlp_level(group_name, tlp_level)
        print(f"Report TLP level: {report_tlp}")
        
        # Prepare template data
        template_loader = jinja2.FileSystemLoader(searchpath="./templates")
        template_env = jinja2.Environment(loader=template_loader)
        
        # Add template registry function to the template environment
        if self.template_registry and hasattr(self.template_registry, 'get_template_for_result'):
            template_env.globals['get_platform_template'] = self.template_registry.get_template_for_result
        
        # Use a group report template if it exists, otherwise create our own custom report
        try:
            template = template_env.get_template("group_report_template.html")
            print("Using group report template.")
        except jinja2.exceptions.TemplateNotFound:
            # We'll create a custom report using the base template components
            template = template_env.get_template("base_template.html")
            print("Group report template not found. Creating a custom group report.")
        
        # Process each query's results
        all_processed_results = {}
        result_counts = {}
        total_results = 0
        
        # Process each query's results and copy screenshots
        for query_name, query_results in group_results.items():
            # Skip nested query groups
            if isinstance(query_results, dict) and query_results.get("type") == "query_group":
                continue
                
            # Get query configuration
            query_config = self.config["queries"].get(query_name, {})
            platform = query_config.get("platform", "urlscan")
            
            # Process results based on platform
            processed_results = []
            
            if platform == "silentpush" and isinstance(query_results, list):
                # Process SilentPush results
                for result in query_results:
                    if not isinstance(result, dict):
                        continue
                        
                    # Determine data type
                    data_type = self._determine_silentpush_data_type(result)
                    
                    if data_type == "whois":
                        processed_result = self._process_silentpush_whois(result)
                    elif data_type == "webscan":
                        processed_result = self._process_silentpush_webscan(result)
                    elif data_type == "domain_search":
                        processed_result = result  # Pass through directly
                    else:
                        processed_result = {
                            "data_type": "generic",
                            "raw_data": result
                        }
                    
                    # Add query name for reference in combined report
                    processed_result["source_query"] = query_name
                    processed_results.append(processed_result)
            elif isinstance(query_results, list):
                # Process other platform results (URLScan etc.)
                for result in query_results:
                    # Add query name for reference in combined report
                    result["source_query"] = query_name
                    
                    # Defang URLs and domains if available
                    if "page" in result and "url" in result["page"]:
                        result["defanged_url"] = self._defang_url(result["page"]["url"])
                    if "page" in result and "domain" in result["page"]:
                        result["defanged_domain"] = self._defang_domain(result["page"]["domain"])
                        
                    # Handle screenshots if available
                    if "task" in result and "uuid" in result["task"]:
                        uuid = result["task"]["uuid"]
                        source_img_path = None
                        
                        # Look for screenshot in the individual query's output directory
                        for subdir in self.output_dir.glob(f"{query_name}_*"):
                            if subdir.is_dir():
                                potential_img = subdir / "images" / f"{uuid}.png"
                                if potential_img.exists():
                                    source_img_path = potential_img
                                    break
                        
                        # If found, copy it to this report's images directory
                        if source_img_path:
                            try:
                                import shutil
                                dest_img_path = img_dir / f"{uuid}.png"
                                shutil.copy2(source_img_path, dest_img_path)
                                result["local_screenshot"] = f"images/{uuid}.png"
                            except Exception as e:
                                print(f"Warning: Could not copy screenshot: {e}")
                        
                        # If not found or couldn't copy, still set the path for template rendering
                        if "local_screenshot" not in result:
                            result["local_screenshot"] = f"images/{uuid}.png"
                    
                    processed_results.append(result)
            
            all_processed_results[query_name] = processed_results
            result_count = len(processed_results)
            result_counts[query_name] = result_count
            total_results += result_count
        
        # Use the current timestamp
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a custom HTML report that properly sections results by query
        # Only do this if we're falling back to the base template
        html_content = ""
        if not hasattr(template, 'name') or template.name == "base_template.html":
            # Create a custom group report with sections for each query
            html_parts = []
            
            # Add HTML head with styles
            html_head = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Group Report: {group_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .query-section {{
            margin-bottom: 40px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
        }}
        .query-title {{
            background-color: #f5f5f5;
            padding: 10px;
            margin: -15px -15px 15px -15px;
            border-bottom: 1px solid #ddd;
            border-radius: 5px 5px 0 0;
        }}
        .result-card {{
            border: 1px solid #ddd;
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .screenshot {{
            max-width: 300px;
            border: 1px solid #ddd;
        }}
        .no-results {{
            font-style: italic;
            color: #777;
        }}
        .tlp-red {{
            background-color: #f9d2d2;
            border: 2px solid #e06666;
            color: #990000;
            padding: 5px;
            display: inline-block;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .tlp-amber {{
            background-color: #fce5cd;
            border: 2px solid #f6b26b;
            color: #b45f06;
            padding: 5px;
            display: inline-block;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .tlp-green {{
            background-color: #d9ead3;
            border: 2px solid #93c47d;
            color: #38761d;
            padding: 5px;
            display: inline-block;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .tlp-white, .tlp-clear {{
            background-color: #f3f3f3;
            border: 2px solid #cccccc;
            color: #666666;
            padding: 5px;
            display: inline-block;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .footer {{
            margin-top: 30px;
            border-top: 1px solid #ddd;
            padding-top: 10px;
            text-align: center;
            font-size: 0.8em;
            color: #777;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 15px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f5f5f5;
        }}
        .result-meta {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .query-info {{
            margin-bottom: 15px;
        }}
        .summary {{
            background-color: #f9f9f9;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
    </style>
</head>""".format(group_name=group_name)
            html_parts.append(html_head)
            
            # Add body opening and report header
            html_parts.append("<body>")
            
            # Create TLP class based on level
            tlp_class = f"tlp-{report_tlp.lower()}"
            
            # Get group titles based on TLP level
            group_titles = group_config.get("titles", [{"title": f"Group Report: {group_name}", "tlp_level": report_tlp}])
            filtered_titles = [item for item in group_titles if self._is_tlp_visible(item.get("tlp_level", report_tlp), report_tlp)]
            group_title = filtered_titles[0]["title"] if filtered_titles else f"Group Report: {group_name}"
            
            # Add header with group title
            html_parts.append(f"""
<div class="header">
    <h1>{group_title}</h1>
    <div class="{tlp_class}">TLP:{report_tlp.upper()}</div>
    <p>Generated on {current_timestamp} by {self.config.get('report_username', '')}</p>
</div>""")
            
            # Add group description if available
            description = group_config.get("description", "")
            if description:
                html_parts.append(f"""
<div class="summary">
    <h2>Group Description</h2>
    <p>{description}</p>
    <p><strong>Total Results:</strong> {total_results} across {len(all_processed_results)} queries</p>
</div>""")
            
            # Add sections for each query with its results
            for query_name, results in all_processed_results.items():
                query_config = self.config["queries"].get(query_name, {})
                query_description = query_config.get("description", "")
                query_platform = query_config.get("platform", "urlscan")
                
                # Add query section
                html_parts.append(f"""
<div class="query-section">
    <div class="query-title">
        <h2>{query_name}</h2>
        <p><strong>Platform:</strong> {query_platform}</p>
        <p><strong>Results:</strong> {len(results)}</p>
    </div>
    <div class="query-info">
        {f"<p>{query_description}</p>" if query_description else ""}
        <p><strong>Query:</strong> <code>{query_config.get('query', 'No query string defined')}</code></p>
    </div>""")
                
                # Add query results
                if results:
                    # If this is urlscan platform, add standard result cards
                    if query_platform == "urlscan":
                        for result in results:
                            # Get screenshot if available
                            screenshot_html = ""
                            if "local_screenshot" in result:
                                screenshot_html = f'<img class="screenshot" src="{result["local_screenshot"]}" alt="Screenshot" />'
                            
                            # Get URL and domain if available
                            page_url = result.get("page", {}).get("url", "")
                            page_domain = result.get("page", {}).get("domain", "")
                            page_title = result.get("page", {}).get("title", "")
                            
                            # Get task info
                            task_time = result.get("task", {}).get("time", "")
                            formatted_time = task_time
                            try:
                                if task_time:
                                    # Convert to more readable format
                                    task_datetime = datetime.datetime.fromisoformat(task_time.replace('Z', '+00:00'))
                                    formatted_time = task_datetime.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                pass
                            
                            # Add result card
                            html_parts.append(f"""
    <div class="result-card">
        <h3>{page_title or page_domain or "Untitled Page"}</h3>
        <div class="result-meta">
            <p><strong>URL:</strong> {result.get("defanged_url", page_url)}</p>
            <p><strong>Domain:</strong> {result.get("defanged_domain", page_domain)}</p>
            <p><strong>Scan Time:</strong> {formatted_time}</p>
            {f'<p><strong>Task ID:</strong> {result.get("task", {}).get("uuid", "")}</p>' if "task" in result and "uuid" in result["task"] else ""}
        </div>
        {screenshot_html}
    </div>""")
                    # If this is silentpush, handle different data types
                    elif query_platform == "silentpush":
                        for result in results:
                            data_type = result.get("data_type", "unknown")
                            
                            if data_type == "whois":
                                # Render whois data
                                html_parts.append(f"""
    <div class="result-card">
        <h3>WHOIS: {result.get("domain", "Unknown Domain")}</h3>
        <div class="result-meta">
            <p><strong>Domain:</strong> {result.get("defanged_domain", result.get("domain", ""))}</p>
            <p><strong>Registrar:</strong> {result.get("registrar", "Unknown")}</p>
            <p><strong>Creation Date:</strong> {result.get("creation_date_formatted", result.get("creation_date", "Unknown"))}</p>
            <p><strong>Expiration Date:</strong> {result.get("expiration_date_formatted", result.get("expiration_date", "Unknown"))}</p>
        </div>
    </div>""")
                            elif data_type == "webscan":
                                # Render webscan data
                                html_parts.append(f"""
    <div class="result-card">
        <h3>Web Scan: {result.get("domain", "Unknown Domain")}</h3>
        <div class="result-meta">
            <p><strong>URL:</strong> {result.get("defanged_url", result.get("url", ""))}</p>
            <p><strong>Domain:</strong> {result.get("defanged_domain", result.get("domain", ""))}</p>
            <p><strong>HTML Title:</strong> {result.get("htmltitle", "")}</p>
            <p><strong>Scan Date:</strong> {result.get("scan_date_formatted", result.get("scan_date", "Unknown"))}</p>
        </div>
    </div>""")
                            else:
                                # Generic rendering for other types
                                html_parts.append(f"""
    <div class="result-card">
        <h3>Result: {result.get("host", result.get("domain", "Unknown Item"))}</h3>
        <p>Data type: {data_type}</p>
        <pre>{str(result)[:300]}{'...' if len(str(result)) > 300 else ''}</pre>
    </div>""")
                else:
                    # No results for this query
                    html_parts.append("""
    <div class="no-results">
        <p>No results found for this query.</p>
    </div>""")
                
                # Close query section
                html_parts.append("</div>")
            
            # Add footer and closing tags
            html_parts.append(f"""
<div class="footer">
    <p>Generated by Masquerade Monitor on {current_timestamp}</p>
    <p>TLP:{report_tlp.upper()}</p>
</div>
</body>
</html>""")
            
            # Combine all HTML parts
            html_content = "\n".join(html_parts)
        else:
            # Using the group report template
            html_content = template.render(
                query_name=group_name,
                query_data=group_config,
                group_name=group_name,
                group_config=group_config,
                queries=self.config["queries"],
                all_results=all_processed_results,
                result_counts=result_counts,
                results=[],  # Empty list for compatibility with base template
                total_results=total_results,
                timestamp=current_timestamp,
                username=self.config.get("report_username", ""),
                tlp_level=report_tlp,
                platform="group",
                debug=False
            )
        
        # Debug template context if debugging is enabled
        if self.debug_enabled:
            debug_template_context("group_report", {
                "query_name": group_name,
                "query_data": group_config,
                "all_results": all_processed_results,
                "result_counts": result_counts,
                "total_results": total_results,
                "tlp_level": report_tlp
            })
        
        # Remove blank lines from HTML content
        html_content = "\n".join([line for line in html_content.split("\n") if line.strip()])
        
        # Extract date/time from run_dir name for the filename
        dir_name = run_dir.name
        datetime_part = ""
        if "_" in dir_name:
            datetime_part = dir_name.split("_", 1)[1]
        
        # Include TLP level and datetime in the filename
        report_filename = f"group_report_{group_name}_{datetime_part}_TLP-{report_tlp}.html"
        report_path = run_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Group report generated in {run_dir} with {total_results} total results")
        return report_path