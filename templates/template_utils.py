"""
Template utility functions for Masquerade Monitor report generation.
"""

def get_platform_template(result):
    """
    Determine the appropriate template to use based on the result type.
    
    Args:
        result: The result object to determine template for
        
    Returns:
        str: Path to the template file to include
    """
    # Default template
    template_path = 'platforms/urlscan_result.html'
    
    # For SilentPush results
    if 'data_type' in result:
        if result['data_type'] == 'whois':
            template_path = 'platforms/silentpush_whois.html'
        elif result['data_type'] == 'webscan':
            template_path = 'platforms/silentpush_webscan.html'
        else:
            template_path = 'platforms/silentpush_generic.html'
            
    return template_path