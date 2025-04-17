# masq-monitor
This will be a python application to automate monitoring for masquerades.

The basic idea:
It will take a list of monitoring pivots, and it will perform API calls to check if there is anything new since the last check.

It will most likely start with urlscan.io requests, and then expand from there. urlscan.io will be used because they allow free API searches that should suffice.

Example:

To monitor for USAA masquerades:
Method 1: Monitoring for scan tasks that have "USAA" in the page.title.
Method 2: Monitoring for scan tasks that have "usaa" in the domain.
Method 3: Monitoring for scan tasks that use the official USAA favicon hash (or anyother official USAA hashes).

The monitoring TTPs will need to be periodically updated as needed.
