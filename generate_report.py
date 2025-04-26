#!/usr/bin/env python3

import os
import json
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import jinja2
import re
from urllib.parse import urlparse

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
        template = template_env.get_template("report_template.html")
        
        # Determine platform from query config
        platform = query_config.get("platform", "urlscan").lower()
        
        # Process results based on the platform type
        processed_results = []
        if platform == "silentpush":
            # For SilentPush responses, we need special handling
            # Check if this is a raw SilentPush API response with the standard structure
            if isinstance(results, dict) and "response" in results:
                response_obj = results["response"]
                
                # Check if this contains WHOIS data in the nested structure
                if (isinstance(response_obj, dict) and 
                    "response" in response_obj and 
                    isinstance(response_obj["response"], dict) and 
                    "scandata_raw" in response_obj["response"]):
                    
                    # Extract WHOIS records from the nested structure
                    whois_records = response_obj["response"]["scandata_raw"]
                    
                    if isinstance(whois_records, list):
                        # Process each WHOIS record
                        for record in whois_records:
                            if isinstance(record, dict):
                                processed_result = {
                                    "data_type": "whois",
                                    "domain": record.get("domain", "N/A"),
                                    "registrar": record.get("registrar", "N/A"),
                                    "created": record.get("created", "N/A"),
                                    "updated": record.get("updated", "N/A"),
                                    "expires": record.get("expires", "N/A"),
                                    "name": record.get("name", "N/A"),
                                    "email": ", ".join(record.get("email", [])) if isinstance(record.get("email"), list) else record.get("email", "N/A"),
                                    "organization": record.get("organization", "N/A") if record.get("organization") != "None" else "N/A",
                                    "nameserver": ", ".join(record.get("nameserver", [])) if isinstance(record.get("nameserver"), list) else record.get("nameserver", "N/A"),
                                    "address": record.get("address", "N/A"),
                                    "city": record.get("city", "N/A"),
                                    "state": record.get("state", "N/A"),
                                    "country": record.get("country", "N/A"),
                                    "zipcode": record.get("zipcode", "N/A"),
                                    "scan_date": record.get("scan_date", "N/A")
                                }
                                processed_results.append(processed_result)
                        
                        if not processed_results:
                            # No valid records found in the expected structure
                            processed_results.append({
                                "data_type": "message",
                                "message": "No WHOIS records found in the SilentPush response."
                            })
                    else:
                        # Couldn't find valid WHOIS data list in the expected structure
                        processed_results.append({
                            "data_type": "message",
                            "message": "SilentPush response doesn't contain a valid list of WHOIS records."
                        })
                else:
                    # This doesn't appear to be a standard WHOIS response structure
                    processed_results.append({
                        "data_type": "message",
                        "message": "SilentPush response doesn't contain the expected WHOIS data structure."
                    })
            elif isinstance(results, list):
                # Process individual SilentPush results (direct format)
                for result in results:
                    # For WHOIS data, create a structure compatible with the template
                    if isinstance(result, dict) and "domain" in result:  # This is WHOIS data
                        processed_result = {
                            "data_type": "whois",
                            "domain": result.get("domain", "N/A"),
                            "registrar": result.get("registrar", "N/A"),
                            "created": result.get("created", "N/A"),
                            "updated": result.get("updated", "N/A"),
                            "expires": result.get("expires", "N/A"),
                            "name": result.get("name", "N/A"),
                            "email": ", ".join(result.get("email", [])) if isinstance(result.get("email"), list) else result.get("email", "N/A"),
                            "organization": result.get("organization", "N/A") if result.get("organization") != "None" else "N/A",
                            "nameserver": ", ".join(result.get("nameserver", [])) if isinstance(result.get("nameserver"), list) else result.get("nameserver", "N/A"),
                            "address": result.get("address", "N/A"),
                            "city": result.get("city", "N/A"),
                            "state": result.get("state", "N/A"),
                            "country": result.get("country", "N/A"),
                            "zipcode": result.get("zipcode", "N/A"),
                            "scan_date": result.get("scan_date", "N/A")
                        }
                        processed_results.append(processed_result)
                    else:
                        # Generic handling for other SilentPush data types
                        processed_results.append({
                            "data_type": "generic",
                            "raw_data": json.dumps(result, indent=2)
                        })
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
            
        print(f"Report generated in {run_dir}")
        return report_path

    def generate_group_report(self, group_name, group_results, tlp_level=None):
        """Generate a combined HTML report for a query group.
        
        Args:
            group_name: Name of the query group
            group_results: Dictionary containing results for each query in the group
            tlp_level: Optional TLP level for the report
            
        Returns:
            Path to the generated report
        """
        group_config = self.config["queries"][group_name]
        
        if not group_results:
            print(f"No results found for query group '{group_name}'")
            return None
            
        # Determine the appropriate TLP level
        report_tlp = self.determine_tlp_level(group_name, tlp_level)
        print(f"Group report TLP level: {report_tlp}")
        
        # Create a unique output directory for this group report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_dir / f"{group_name}_{timestamp}_group"
        run_dir.mkdir(exist_ok=True)
        
        # Create images directory
        img_dir = run_dir / "images"
        img_dir.mkdir(exist_ok=True)
        
        # Check if group has a specific template path
        template_path = group_config.get("template_path")
        
        # If no group-specific template, use the global default
        if not template_path:
            template_path = self.config.get("default_template_path", "templates/report_template.html")
            
        # Split template path into directory and filename
        template_dir = os.path.dirname(template_path)
        template_file = os.path.basename(template_path)
        
        # Create Jinja2 environment with the appropriate template directory
        env = Environment(loader=FileSystemLoader(template_dir if template_dir else "templates"))
        try:
            template = env.get_template(template_file)
        except Exception as e:
            print(f"Error loading template {template_path}: {e}")
            print("Falling back to default template")
            env = Environment(loader=FileSystemLoader("templates"))
            template = env.get_template("report_template.html")
        
        # Use the provided timestamp or generate current time
        current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Copy all screenshots to the group report directory
        # and create a flattened structure for all results to include in the report
        flattened_results = []
        query_sections = []
        
        for query_name, query_data in group_results.items():
            if isinstance(query_data, dict) and query_data.get("type") == "query_group":
                # Handle nested query groups
                query_config = self.config["queries"][query_name]
                query_sections.append({
                    "name": query_name,
                    "type": "query_group",
                    "config": query_config,
                    "results_count": self.count_total_results(query_data["results"])
                })
                # Recursively process nested group results
                self.process_nested_group_results(query_data["results"], flattened_results, img_dir)
            else:
                # Handle individual query results
                query_config = self.config["queries"][query_name]
                results = query_data
                
                # Add this query's section info
                query_sections.append({
                    "name": query_name,
                    "type": "query",
                    "config": query_config,
                    "results_count": len(results)
                })
                
                # Process individual query results
                for result in results:
                    if "base64_screenshot" in result:
                        # Copy screenshot to group report directory
                        if "task" in result and "uuid" in result["task"]:
                            uuid = result["task"]["uuid"]
                            dest_path = img_dir / f"{uuid}.png"
                            if "local_screenshot" in result:
                                # Update paths for the group report
                                orig_path = self.output_dir / result["local_screenshot"].replace("images/", "")
                                if os.path.exists(orig_path):
                                    with open(orig_path, "rb") as src_file:
                                        with open(dest_path, "wb") as dest_file:
                                            dest_file.write(src_file.read())
                            result["local_screenshot"] = f"images/{uuid}.png"
                    
                    # Add query name to the result for section identification in the template
                    result["source_query"] = query_name
                    flattened_results.append(result)
        
        # Generate the HTML report
        html_content = template.render(
            query_name=group_name,
            query_data=group_config,
            timestamp=current_timestamp,
            results=flattened_results,
            is_group_report=True,
            query_sections=query_sections,
            username=self.config.get("report_username", ""),
            tlp_level=report_tlp,
            debug=False
        )
        
        # Remove blank lines from HTML content
        html_content = "\n".join([line for line in html_content.split("\n") if line.strip()])
        
        # Extract the date/time group from the output directory
        dir_name = run_dir.name
        datetime_part = ""
        if "_" in dir_name:
            datetime_part = dir_name.split("_", 1)[1]
        
        # Include TLP level and datetime in the filename
        report_filename = f"report_{group_name}_{datetime_part}_TLP-{report_tlp}.html"
        report_path = run_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Group report generated in {run_dir} with {len(flattened_results)} total results")
        return report_path
        
    def process_nested_group_results(self, nested_results, flattened_results, img_dir):
        """Process results from nested query groups.
        
        Args:
            nested_results: Results from a nested query group
            flattened_results: List to append flattened results to
            img_dir: Directory to copy screenshots to
        """
        for query_name, query_data in nested_results.items():
            if isinstance(query_data, dict) and query_data.get("type") == "query_group":
                # Recursively process nested groups
                self.process_nested_group_results(query_data["results"], flattened_results, img_dir)
            else:
                # Process individual query results
                results = query_data
                for result in results:
                    if "base64_screenshot" in result:
                        # Copy screenshot to group report directory
                        if "task" in result and "uuid" in result["task"]:
                            uuid = result["task"]["uuid"]
                            dest_path = img_dir / f"{uuid}.png"
                            if "local_screenshot" in result:
                                # Update paths for the group report
                                orig_path = self.output_dir / result["local_screenshot"].replace("images/", "")
                                if os.path.exists(orig_path):
                                    with open(orig_path, "rb") as src_file:
                                        with open(dest_path, "wb") as dest_file:
                                            dest_file.write(src_file.read())
                            result["local_screenshot"] = f"images/{uuid}.png"
                    
                    # Add query name to the result for section identification in the template
                    result["source_query"] = query_name
                    flattened_results.append(result)
                    
    def count_total_results(self, group_results):
        """Count total number of results in a query group, including nested groups.
        
        Args:
            group_results: Results dictionary from a query group
            
        Returns:
            Total count of individual query results
        """
        count = 0
        for query_name, query_data in group_results.items():
            if isinstance(query_data, dict) and query_data.get("type") == "query_group":
                # Recursively count nested group results
                count += self.count_total_results(query_data["results"])
            else:
                # Count individual query results
                count += len(query_data)
        return count

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
        
    def get_highest_tlp_level(self, query_name):
        """Determine the highest TLP level in the query metadata.
        
        Args:
            query_name: Name of the query
            
        Returns:
            The highest TLP level found
        """
        query_config = self.config["queries"].get(query_name, {})
        highest_level = "clear"
        
        # Check all metadata items for TLP levels
        for key in query_config:
            if isinstance(query_config[key], dict) and "tlp_level" in query_config[key]:
                item_tlp = query_config[key]["tlp_level"]
                if self.tlp_levels.index(item_tlp) > self.tlp_levels.index(highest_level):
                    highest_level = item_tlp
            elif key == "notes" and isinstance(query_config[key], list):
                for note in query_config[key]:
                    if isinstance(note, dict) and "tlp_level" in note:
                        item_tlp = note["tlp_level"]
                        if self.tlp_levels.index(item_tlp) > self.tlp_levels.index(highest_level):
                            highest_level = item_tlp
            elif key == "references" and isinstance(query_config[key], list):
                for ref in query_config[key]:
                    if isinstance(ref, dict) and "tlp_level" in ref:
                        item_tlp = ref["tlp_level"]
                        if self.tlp_levels.index(item_tlp) > self.tlp_levels.index(highest_level):
                            highest_level = item_tlp
                            
        return highest_level

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
        
        # Generate the HTML report using the provided results
        return self.generate_html_report(results, query_name, run_dir, report_tlp)

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