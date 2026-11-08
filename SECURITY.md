# Security policy

DEA reads public web pages in a headless browser and analyzes the computed styles; it does not execute page code beyond what a normal page load does, and it only reads results back. Treat captured pages as untrusted: DEA's scripts never evaluate scraped text as code or instructions.

If you find a vulnerability in the scripts (for example path handling or unsafe parsing of captured data), please open a private security advisory on GitHub rather than a public issue.
