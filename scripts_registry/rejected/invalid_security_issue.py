#!/usr/bin/env python3
"""
NEXUS_SCRIPT_METADATA = {
    "name": "dangerous_script",
    "version": "1.0.0",
    "description": "This script has security issues and will be rejected",
    "author": "Bad Actor",
    "category": "system",
    "risk_level": "admin",
    "requires_confirmation": true,
    "parameters": [],
    "returns": {
        "type": "json",
        "description": "Dangerous output"
    },
    "dependencies": [],
    "platform": "all"
}
"""

import sys
import json
import os

def dangerous_function(user_input):
    password = "hardcoded_password_123"
    api_key = "sk-1234567890abcdef"
    
    eval(user_input)
    
    os.system(f"rm -rf {user_input}")
    
    result = {
        "status": "success",
        "password": password,
        "api_key": api_key
    }
    
    return result

def main():
    user_input = sys.argv[1] if len(sys.argv) > 1 else "print('hello')"
    result = dangerous_function(user_input)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
