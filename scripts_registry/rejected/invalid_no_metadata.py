#!/usr/bin/env python3
"""
This script is missing the required NEXUS_SCRIPT_METADATA
It will be rejected by the validator
"""

import sys
import json

def do_something():
    print(json.dumps({"status": "success", "data": "This script has no metadata"}))

if __name__ == "__main__":
    do_something()
