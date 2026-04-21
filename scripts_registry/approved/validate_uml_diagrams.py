#!/usr/bin/env python3
"""
NEXUS_SCRIPT_METADATA = {
    "name": "validate_uml_diagrams",
    "version": "1.0.0",
    "description": "Validates UML diagram files and checks for completeness",
    "author": "Nexus Team",
    "category": "data",
    "risk_level": "read",
    "requires_confirmation": false,
    "parameters": [
        {
            "name": "uml_path",
            "type": "string",
            "required": false,
            "description": "Path to UML directory (default: 2_UML)"
        }
    ],
    "returns": {
        "type": "json",
        "description": "Validation results with completeness check"
    },
    "dependencies": [],
    "platform": "all"
}
"""

import sys
import json
from pathlib import Path

def validate_uml(uml_path="2_UML"):
    """Validate UML diagrams and check for required files"""
    try:
        uml_dir = Path(uml_path)
        
        if not uml_dir.exists():
            raise FileNotFoundError(f"UML directory not found: {uml_path}")
        
        required_files = [
            "list_of_actors.txt",
            "list_of_functionalities.txt",
            "list_of_use_cases.txt",
            "uml_diagram.png"
        ]
        
        found_files = []
        missing_files = []
        
        for req_file in required_files:
            file_path = uml_dir / req_file
            if file_path.exists():
                found_files.append({
                    "name": req_file,
                    "size_kb": round(file_path.stat().st_size / 1024, 2),
                    "exists": True
                })
            else:
                missing_files.append(req_file)
        
        completeness = (len(found_files) / len(required_files)) * 100
        
        validation = {
            "directory": str(uml_dir),
            "completeness_percent": round(completeness, 2),
            "required_files": len(required_files),
            "found_files": len(found_files),
            "missing_files": missing_files,
            "files": found_files,
            "is_complete": len(missing_files) == 0
        }
        
        result = {
            "status": "success",
            "data": validation
        }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def main():
    uml_path = sys.argv[1] if len(sys.argv) > 1 else "2_UML"
    
    result = validate_uml(uml_path)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    main()
