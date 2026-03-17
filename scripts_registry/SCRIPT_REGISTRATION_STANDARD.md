# Script Registration Standard for Nexus Intelligent Chatbot System

## Overview

This document defines the standard for registering external scripts in the Nexus Scripts Registry. All scripts must conform to this standard to be accepted and executed by the Task Executor component.

## Script Metadata Requirements

Every script submitted for registration MUST include a metadata header in the following format:

### For Python Scripts (.py)

```python
"""
NEXUS_SCRIPT_METADATA = {
    "name": "script_name",
    "version": "1.0.0",
    "description": "Brief description of what the script does",
    "author": "Author Name",
    "category": "system|data|integration|utility",
    "risk_level": "read|write|admin",
    "requires_confirmation": true|false,
    "parameters": [
        {
            "name": "param_name",
            "type": "string|int|float|bool",
            "required": true|false,
            "description": "Parameter description"
        }
    ],
    "returns": {
        "type": "json|text|boolean",
        "description": "Return value description"
    },
    "dependencies": ["package1", "package2"],
    "platform": "linux|windows|macos|all"
}
"""
```

### For Bash Scripts (.sh)

```bash
# NEXUS_SCRIPT_METADATA_START
# name: script_name
# version: 1.0.0
# description: Brief description of what the script does
# author: Author Name
# category: system|data|integration|utility
# risk_level: read|write|admin
# requires_confirmation: true|false
# parameters: param1:string:required, param2:int:optional
# returns: json|text|boolean
# dependencies: curl, jq
# platform: linux|windows|macos|all
# NEXUS_SCRIPT_METADATA_END
```

## Metadata Field Specifications

### Required Fields

1. **name** (string, 3-50 chars)
   - Unique identifier for the script
   - Must be lowercase with underscores
   - Pattern: `^[a-z][a-z0-9_]*$`

2. **version** (string)
   - Semantic versioning format: MAJOR.MINOR.PATCH
   - Pattern: `^\d+\.\d+\.\d+$`

3. **description** (string, 10-200 chars)
   - Clear, concise explanation of script functionality
   - Must not contain special characters that break JSON

4. **author** (string, 2-100 chars)
   - Name or identifier of script creator

5. **category** (enum)
   - Must be one of: `system`, `data`, `integration`, `utility`
   - **system**: OS-level operations (restart services, check processes)
   - **data**: Data processing, transformation, analysis
   - **integration**: External API calls, third-party services
   - **utility**: Helper functions, formatting, validation

6. **risk_level** (enum)
   - Must be one of: `read`, `write`, `admin`
   - **read**: Only reads data, no modifications
   - **write**: Modifies data or system state
   - **admin**: Requires elevated privileges

7. **requires_confirmation** (boolean)
   - `true`: User must confirm before execution
   - `false`: Can execute without confirmation
   - MUST be `true` for `write` and `admin` risk levels

8. **returns** (object)
   - **type**: `json`, `text`, or `boolean`
   - **description**: What the script returns

### Optional Fields

9. **parameters** (array of objects)
   - List of input parameters the script accepts
   - Each parameter must specify:
     - **name**: Parameter identifier
     - **type**: Data type (string, int, float, bool)
     - **required**: Whether parameter is mandatory
     - **description**: What the parameter does

10. **dependencies** (array of strings)
    - External packages or tools required
    - Empty array if no dependencies

11. **platform** (enum)
    - Target operating system: `linux`, `windows`, `macos`, `all`
    - Default: `all`

## Script Implementation Requirements

### 1. Error Handling

All scripts MUST implement proper error handling:

**Python:**
```python
import sys
import json

try:
    # Script logic here
    result = {"status": "success", "data": "result"}
    print(json.dumps(result))
    sys.exit(0)
except Exception as e:
    error = {"status": "error", "message": str(e)}
    print(json.dumps(error))
    sys.exit(1)
```

**Bash:**
```bash
set -e  # Exit on error

trap 'echo "{\"status\":\"error\",\"message\":\"Script failed at line $LINENO\"}"; exit 1' ERR

# Script logic here
echo '{"status":"success","data":"result"}'
exit 0
```

### 2. Output Format

Scripts MUST return structured output:

- **Success**: JSON with `status: "success"` and relevant data
- **Error**: JSON with `status: "error"` and error message
- No extraneous output (debug prints, warnings) to stdout

### 3. Input Validation

Scripts MUST validate all input parameters:

```python
def validate_parameters(params):
    required = ["param1", "param2"]
    for param in required:
        if param not in params:
            raise ValueError(f"Missing required parameter: {param}")
```

### 4. Sensitive Data Handling

Scripts MUST NOT:
- Log passwords, API keys, or tokens
- Print PII (Personally Identifiable Information) to stdout
- Store credentials in plaintext

Scripts SHOULD:
- Use environment variables for secrets
- Mask sensitive output using the platform's output masking service

### 5. Timeout Compliance

Scripts MUST complete within reasonable time:
- **read** operations: < 30 seconds
- **write** operations: < 60 seconds
- **admin** operations: < 120 seconds

Long-running tasks should be rejected or redesigned.

### 6. Idempotency

Scripts with `write` or `admin` risk levels SHOULD be idempotent:
- Running the script multiple times produces the same result
- No unintended side effects from repeated execution

## Security Requirements

### 1. No Arbitrary Code Execution

Scripts MUST NOT:
- Use `eval()`, `exec()`, or similar functions with user input
- Execute shell commands with unsanitized input
- Import modules dynamically based on user input

### 2. Path Traversal Prevention

Scripts MUST:
- Validate file paths to prevent directory traversal
- Use absolute paths or restrict to specific directories
- Check file permissions before access

### 3. Resource Limits

Scripts MUST:
- Limit memory usage (< 500MB for typical operations)
- Avoid infinite loops or recursion
- Clean up temporary files and resources

## Validation Process

Scripts submitted to the registry undergo automated validation:

1. **Metadata Validation**
   - All required fields present
   - Field values match specifications
   - Metadata format is parseable

2. **Syntax Validation**
   - Python: `python -m py_compile script.py`
   - Bash: `bash -n script.sh`

3. **Security Scan**
   - Check for dangerous functions
   - Validate input handling
   - Verify no hardcoded credentials

4. **Dependency Check**
   - Verify all dependencies are available
   - Check for version conflicts

5. **Test Execution**
   - Run with sample inputs
   - Verify output format
   - Check error handling

## Registration Process

1. **Submit Script**
   - Place script file in `scripts_registry/pending/` directory
   - Ensure metadata is complete and accurate

2. **Automated Validation**
   - `script_validator.py` runs validation checks
   - Results logged to `registration_log.txt`

3. **Approval**
   - Valid scripts moved to `scripts_registry/approved/`
   - Invalid scripts moved to `scripts_registry/rejected/`
   - Rejection reason logged

4. **Integration**
   - Approved scripts indexed by Task Executor
   - Available for execution via NLP commands

## Example: Valid Python Script

```python
"""
NEXUS_SCRIPT_METADATA = {
    "name": "check_disk_usage",
    "version": "1.0.0",
    "description": "Check disk usage and return percentage used",
    "author": "Nexus Team",
    "category": "system",
    "risk_level": "read",
    "requires_confirmation": false,
    "parameters": [
        {
            "name": "path",
            "type": "string",
            "required": false,
            "description": "Path to check (default: /)"
        }
    ],
    "returns": {
        "type": "json",
        "description": "Disk usage statistics"
    },
    "dependencies": ["psutil"],
    "platform": "all"
}
"""

import sys
import json
import psutil

def main():
    try:
        path = sys.argv[1] if len(sys.argv) > 1 else "/"
        
        usage = psutil.disk_usage(path)
        
        result = {
            "status": "success",
            "data": {
                "path": path,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": usage.percent
            }
        }
        
        print(json.dumps(result))
        sys.exit(0)
        
    except Exception as e:
        error = {
            "status": "error",
            "message": str(e)
        }
        print(json.dumps(error))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Example: Valid Bash Script

```bash
#!/bin/bash

# NEXUS_SCRIPT_METADATA_START
# name: list_running_services
# version: 1.0.0
# description: List all running systemd services
# author: Nexus Team
# category: system
# risk_level: read
# requires_confirmation: false
# parameters: none
# returns: json
# dependencies: systemctl, jq
# platform: linux
# NEXUS_SCRIPT_METADATA_END

set -e
trap 'echo "{\"status\":\"error\",\"message\":\"Failed to list services\"}"; exit 1' ERR

services=$(systemctl list-units --type=service --state=running --no-pager --no-legend | awk '{print $1}')

count=$(echo "$services" | wc -l)

echo "{\"status\":\"success\",\"data\":{\"count\":$count,\"services\":$(echo "$services" | jq -R . | jq -s .)}}"
exit 0
```

## Rejection Reasons

Common reasons for script rejection:

1. **Missing or incomplete metadata**
2. **Invalid metadata format**
3. **Syntax errors in script code**
4. **Security vulnerabilities detected**
5. **Missing error handling**
6. **Incorrect output format**
7. **Undeclared dependencies**
8. **Timeout during test execution**
9. **Risk level mismatch with confirmation requirement**
10. **Duplicate script name**

## Maintenance and Updates

### Updating Existing Scripts

To update a registered script:
1. Increment version number (follow semantic versioning)
2. Update metadata with changes
3. Submit to `scripts_registry/pending/` with new version
4. Old version remains active until new version approved

### Deprecation

Scripts can be deprecated:
1. Add `"deprecated": true` to metadata
2. Add `"replacement": "new_script_name"` if applicable
3. Script remains available but shows deprecation warning

## Support and Contact

For questions about script registration:
- Review this standard document
- Check `scripts_registry/examples/` for reference implementations
- Consult the Task Executor documentation
- Contact the Nexus development team

## Version History

- **1.0.0** (2026-03-10): Initial standard definition
