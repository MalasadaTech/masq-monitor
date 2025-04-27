"""
Template registry for Masquerade Monitor.

This module maintains a registry of templates for different result types,
making it easy to add support for new types of results.
"""

class TemplateRegistry:
    """Registry for managing templates for different result types."""

    def __init__(self):
        """Initialize the template registry with default mappings."""
        # Default templates by platform
        self.platform_defaults = {
            'urlscan': 'platforms/urlscan_result.html',
            'silentpush': 'platforms/silentpush_generic.html',
            'default': 'platforms/urlscan_result.html'
        }
        
        # Templates by data type
        self.data_type_templates = {
            'whois': 'platforms/silentpush_whois.html',
            'webscan': 'platforms/silentpush_webscan.html',
            'generic': 'platforms/silentpush_generic.html'
        }
    
    def get_template_for_result(self, result):
        """
        Determine the appropriate template for a result.
        
        Args:
            result (dict): The result object to analyze
            
        Returns:
            str: Template path to use for this result
        """
        # Default template (for URLScan.io results)
        if not isinstance(result, dict):
            return self.platform_defaults['default']
            
        # For SilentPush results with a data_type
        if 'data_type' in result:
            data_type = result['data_type']
            # Check if we have a specific template for this data type
            if data_type in self.data_type_templates:
                return self.data_type_templates[data_type]
        
        # Determine platform if possible
        platform = 'default'
        # URLScan results typically have page and task attributes
        if 'page' in result and 'task' in result and 'uuid' in result.get('task', {}):
            platform = 'urlscan'
        # For other result types, we'd need specific detection logic
        
        # Return the default template for this platform
        return self.platform_defaults.get(platform, self.platform_defaults['default'])
    
    def register_template(self, data_type, template_path):
        """
        Register a template for a specific data type.
        
        Args:
            data_type (str): The data type identifier
            template_path (str): Path to the template file
            
        Returns:
            None
        """
        self.data_type_templates[data_type] = template_path
    
    def register_platform_default(self, platform, template_path):
        """
        Register a default template for a platform.
        
        Args:
            platform (str): The platform identifier
            template_path (str): Path to the template file
            
        Returns:
            None
        """
        self.platform_defaults[platform] = template_path

# Create a singleton instance
template_registry = TemplateRegistry()

def get_template_for_result(result):
    """
    Get the appropriate template for a result (convenience function).
    
    Args:
        result (dict): The result object
        
    Returns:
        str: Template path
    """
    return template_registry.get_template_for_result(result)