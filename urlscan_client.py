#!/usr/bin/env python3

import requests
import base64
from pathlib import Path

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