#!/usr/bin/env python3
"""
NEXUS_SCRIPT_METADATA = {
    "name": "check_architecture_docs",
    "version": "1.0.0",
    "description": "Checks architecture documentation completeness across all directories",
    "author": "Nexus Team",
    "category": "utility",
    "risk_level": "read",
    "requires_confirmation": false,
    "parameters": [],
    "returns": {
        "type": "json",
        "description": "Documentation completeness report"
    },
    "dependencies": [],
    "platform": "all"
}
"""

import sys
import json
from pathlib import Path

def check_architecture_docs():
    """Check architecture documentation across project directories"""
    try:
        directories = {
            "1_SRS": ["Software Requirements Specification (SRS).docx"],
            "2_UML": ["list_of_actors.txt", "list_of_functionalities.txt", 
                     "list_of_use_cases.txt", "uml_diagram.png"],
            "3_DFD": ["context_diagram.md", "level1_dfd_details.md", 
                     "class_specifications.md", "uml_relationships.md"],
            "4_COMP": ["application_components.md", "software_architecture.md"]
        }
        
        report = {
            "total_directories": len(directories),
            "directories_checked": 0,
            "total_expected_files": 0,
            "total_found_files": 0,
            "directory_status": []
        }
        
        for dir_name, expected_files in directories.items():
            dir_path = Path(dir_name)
            
            if not dir_path.exists():
                report["directory_status"].append({
                    "directory": dir_name,
                    "exists": False,
                    "completeness": 0,
                    "missing_files": expected_files
                })
                report["total_expected_files"] += len(expected_files)
                continue
            
            report["directories_checked"] += 1
            found = []
            missing = []
            
            for file_name in expected_files:
                file_path = dir_path / file_name
                if file_path.exists():
                    found.append(file_name)
                    report["total_found_files"] += 1
                else:
                    missing.append(file_name)
                
                report["total_expected_files"] += 1
            
            completeness = (len(found) / len(expected_files)) * 100 if expected_files else 100
            
            report["directory_status"].append({
                "directory": dir_name,
                "exists": True,
                "completeness": round(completeness, 2),
                "expected_files": len(expected_files),
                "found_files": len(found),
                "missing_files": missing
            })
        
        overall_completeness = (report["total_found_files"] / report["total_expected_files"]) * 100 if report["total_expected_files"] > 0 else 0
        report["overall_completeness"] = round(overall_completeness, 2)
        
        result = {
            "status": "success",
            "data": report
        }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def main():
    result = check_architecture_docs()
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    main()
