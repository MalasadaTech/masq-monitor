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
            # For all other data types, use the domainsearch template that supports table view
            template_path = 'platforms/silentpush_domainsearch.html'
    # Detect SilentPush domain search results by field structure
    elif 'host' in result and ('asn_diversity' in result or 'ip_diversity_all' in result or 'ip_diversity_groups' in result):
        template_path = 'platforms/silentpush_domainsearch.html'
            
    return template_path