"""
Helper functions for Jinja2 templates in Masquerade Monitor.

These functions are registered with the Jinja2 environment
to provide additional functionality within templates.
"""

def select_template_for_result(result):
    """
    Select the appropriate template for a given result based on its type.
    
    Args:
        result (dict): The result object to analyze.
        
    Returns:
        str: The template path to use for this result type.
    """
    # Default template (for URLScan.io results)
    if not isinstance(result, dict):
        return 'platforms/urlscan_result.html'
        
    # For SilentPush results
    if 'data_type' in result:
        data_type = result['data_type']
        
        if data_type == 'whois':
            return 'platforms/silentpush_whois.html'
        elif data_type == 'webscan':
            return 'platforms/silentpush_webscan.html'
        elif data_type == 'generic':
            return 'platforms/silentpush_generic.html'
        # You can add more conditions here for new data types
            
    # Default to URLScan for anything else
    return 'platforms/urlscan_result.html'