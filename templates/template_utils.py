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
    
    # For SilentPush results - use silentpush_domainsearch.html for all query types
    if 'platform' in result and result['platform'] == 'silentpush':
        template_path = 'platforms/silentpush_domainsearch.html'
    # Alternative detection for SilentPush results that don't have the platform field
    elif 'data_type' in result:
        template_path = 'platforms/silentpush_domainsearch.html'
    # Detect SilentPush domain search results by field structure
    elif 'host' in result and ('asn_diversity' in result or 'ip_diversity_all' in result or 'ip_diversity_groups' in result):
        template_path = 'platforms/silentpush_domainsearch.html'
            
    return template_path