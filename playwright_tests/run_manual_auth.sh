#!/bin/bash

# Make sure you're in the venv
source venv/bin/activate

# Run the manual login test (opens browser for you to login)
# This will save auth cookies to .auth/axiom_auth.json
echo "Running manual login test..."
echo "You will need to login in the browser that opens."
echo ""

pytest playwright_tests/axiom_basic_tests.py -v -s
