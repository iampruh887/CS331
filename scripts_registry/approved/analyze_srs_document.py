#!/usr/bin/env python3
"""
NEXUS_SCRIPT_METADATA = {
    "name": "analyze_srs_document",
    "version": "1.0.0",
    "description": "Analyzes SRS document and extracts key requirements and statistics",
    "author": "Nexus Team",
    "category": "data",
    "risk_level": "read",
    "requires_confirmation": false,
    "parameters": [
        {
            "name": "srs_path",
            "type": "string",
            "required": false,
            "description": "Path to SRS directory (default: 1_SRS)"
        }
    ],
    "returns": {
        "type": "json",
        "description": "Analysis results with document statistics"
    },
    "dependencies": [],
    "platform": "all"
}
"""

import sys
import json
import os
from pathlib import Path

def analyze_srs(srs_path="1_SRS"):
    """Analyze SRS documents and return statistics"""
    try:
        srs_dir = Path(srs_path)
        
        if not srs_dir.exists():
            raise FileNotFoundError(f"SRS directory not found: {srs_path}")
        
        files = list(srs_dir.glob("*"))
        doc_files = [f for f in files if f.suffix in ['.docx', '.md', '.txt', '.pdf']]
        
        total_size = sum(f.stat().st_size for f in doc_files if f.is_file())
        
        analysis = {
            "directory": str(srs_dir),
            "total_files": len(doc_files),
            "total_size_kb": round(total_size / 1024, 2),
            "file_types": {},
            "files": []
        }
        
        for doc_file in doc_files:
            ext = doc_file.suffix
            analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
            
            analysis["files"].append({
                "name": doc_file.name,
                "size_kb": round(doc_file.stat().st_size / 1024, 2),
                "type": ext
            })
        
        result = {
            "status": "success",
            "data": analysis
        }
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def main():
    srs_path = sys.argv[1] if len(sys.argv) > 1 else "1_SRS"
    
    result = analyze_srs(srs_path)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    main()
