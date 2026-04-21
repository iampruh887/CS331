#!/usr/bin/env python3
"""
Script Validator for Nexus Scripts Registry
Validates scripts against the registration standard and manages registration process.
"""

import os
import sys
import json
import re
import ast
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class ScriptValidator:
    def __init__(self, registry_dir: str = "scripts_registry"):
        self.registry_dir = Path(registry_dir)
        self.pending_dir = self.registry_dir / "pending"
        self.approved_dir = self.registry_dir / "approved"
        self.rejected_dir = self.registry_dir / "rejected"
        self.log_file = self.registry_dir / "registration_log.txt"
        
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for directory in [self.pending_dir, self.approved_dir, self.rejected_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_type: str, script_name: str, status: str, details: str):
        """Log registration events to registration_log.txt"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {event_type} | {script_name} | {status} | {details}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        print(f"{event_type}: {script_name} - {status}")
        if details:
            print(f"  Details: {details}")
    
    def extract_python_metadata(self, filepath: Path) -> Optional[Dict]:
        """Extract metadata from Python script docstring"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            pattern = r'NEXUS_SCRIPT_METADATA\s*=\s*(\{.*?\n\})'
            match = re.search(pattern, content, re.DOTALL)
            
            if not match:
                return None
            
            metadata_str = match.group(1)
            metadata_str = metadata_str.replace('false', 'False').replace('true', 'True')
            metadata = ast.literal_eval(metadata_str)
            return metadata
            
        except Exception as e:
            print(f"  Error extracting metadata: {e}")
            return None
    
    def extract_bash_metadata(self, filepath: Path) -> Optional[Dict]:
        """Extract metadata from Bash script comments"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            start_marker = "# NEXUS_SCRIPT_METADATA_START"
            end_marker = "# NEXUS_SCRIPT_METADATA_END"
            
            if start_marker not in content or end_marker not in content:
                return None
            
            start_idx = content.index(start_marker) + len(start_marker)
            end_idx = content.index(end_marker)
            metadata_section = content[start_idx:end_idx]
            
            metadata = {}
            for line in metadata_section.strip().split('\n'):
                line = line.strip()
                if not line.startswith('#'):
                    continue
                
                line = line[1:].strip()
                if ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == "parameters":
                    params = []
                    if value and value != "none":
                        for param in value.split(','):
                            parts = param.strip().split(':')
                            if len(parts) >= 3:
                                params.append({
                                    "name": parts[0],
                                    "type": parts[1],
                                    "required": parts[2] == "required"
                                })
                    metadata["parameters"] = params
                elif key == "dependencies":
                    metadata["dependencies"] = [d.strip() for d in value.split(',') if d.strip()]
                elif key == "requires_confirmation":
                    metadata[key] = value.lower() == "true"
                else:
                    metadata[key] = value
            
            if "returns" in metadata:
                metadata["returns"] = {
                    "type": metadata["returns"],
                    "description": "Script output"
                }
            
            return metadata
            
        except Exception as e:
            return None
    
    def validate_metadata_fields(self, metadata: Dict) -> Tuple[bool, List[str]]:
        """Validate that all required metadata fields are present and valid"""
        errors = []
        
        required_fields = ["name", "version", "description", "author", "category", 
                          "risk_level", "requires_confirmation", "returns"]
        
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")
        
        if "name" in metadata:
            if not re.match(r'^[a-z][a-z0-9_]*$', metadata["name"]):
                errors.append("Invalid name format (must be lowercase with underscores)")
            if len(metadata["name"]) < 3 or len(metadata["name"]) > 50:
                errors.append("Name must be 3-50 characters")
        
        if "version" in metadata:
            if not re.match(r'^\d+\.\d+\.\d+$', metadata["version"]):
                errors.append("Invalid version format (must be MAJOR.MINOR.PATCH)")
        
        if "description" in metadata:
            if len(metadata["description"]) < 10 or len(metadata["description"]) > 200:
                errors.append("Description must be 10-200 characters")
        
        if "category" in metadata:
            valid_categories = ["system", "data", "integration", "utility"]
            if metadata["category"] not in valid_categories:
                errors.append(f"Invalid category (must be one of: {', '.join(valid_categories)})")
        
        if "risk_level" in metadata:
            valid_risk_levels = ["read", "write", "admin"]
            if metadata["risk_level"] not in valid_risk_levels:
                errors.append(f"Invalid risk_level (must be one of: {', '.join(valid_risk_levels)})")
        
        if "risk_level" in metadata and "requires_confirmation" in metadata:
            if metadata["risk_level"] in ["write", "admin"] and not metadata["requires_confirmation"]:
                errors.append("Scripts with write/admin risk level must require confirmation")
        
        if "returns" in metadata:
            if not isinstance(metadata["returns"], dict):
                errors.append("Returns field must be an object with type and description")
            elif "type" not in metadata["returns"]:
                errors.append("Returns object must have a type field")
        
        return len(errors) == 0, errors
    
    def validate_syntax(self, filepath: Path) -> Tuple[bool, str]:
        """Validate script syntax"""
        try:
            if filepath.suffix == '.py':
                result = subprocess.run(
                    ['python3', '-m', 'py_compile', str(filepath)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    return False, f"Python syntax error: {result.stderr}"
            
            elif filepath.suffix == '.sh':
                result = subprocess.run(
                    ['bash', '-n', str(filepath)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    return False, f"Bash syntax error: {result.stderr}"
            
            return True, "Syntax valid"
            
        except subprocess.TimeoutExpired:
            return False, "Syntax check timeout"
        except Exception as e:
            return False, f"Syntax check failed: {str(e)}"
    
    def security_scan(self, filepath: Path) -> Tuple[bool, List[str]]:
        """Perform basic security checks"""
        warnings = []
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            dangerous_patterns = [
                (r'\beval\s*\(', "Use of eval() detected"),
                (r'\bexec\s*\(', "Use of exec() detected"),
                (r'__import__\s*\(', "Dynamic import detected"),
                (r'os\.system\s*\(', "Use of os.system() detected"),
                (r'subprocess\.call\([^)]*shell\s*=\s*True', "Shell=True in subprocess detected"),
                (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
                (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
                (r'\.\./|\.\.\\', "Path traversal pattern detected"),
            ]
            
            for pattern, message in dangerous_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    warnings.append(message)
            
            return len(warnings) == 0, warnings
            
        except Exception as e:
            return False, [f"Security scan failed: {str(e)}"]
    
    def check_duplicate(self, script_name: str) -> bool:
        """Check if script name already exists in approved registry"""
        for script_file in self.approved_dir.glob('*'):
            if script_file.stem == script_name:
                return True
        return False
    
    def validate_script(self, filepath: Path) -> Tuple[bool, str, Optional[Dict]]:
        """Main validation function"""
        script_name = filepath.stem
        
        if filepath.suffix not in ['.py', '.sh']:
            return False, "Invalid file type (must be .py or .sh)", None
        
        if filepath.suffix == '.py':
            metadata = self.extract_python_metadata(filepath)
        else:
            metadata = self.extract_bash_metadata(filepath)
        
        if metadata is None:
            return False, "Missing or invalid metadata format", None
        
        valid_metadata, metadata_errors = self.validate_metadata_fields(metadata)
        if not valid_metadata:
            return False, "; ".join(metadata_errors), metadata
        
        if self.check_duplicate(metadata["name"]):
            return False, f"Duplicate script name: {metadata['name']}", metadata
        
        syntax_valid, syntax_message = self.validate_syntax(filepath)
        if not syntax_valid:
            return False, syntax_message, metadata
        
        secure, security_warnings = self.security_scan(filepath)
        if not secure:
            return False, "; ".join(security_warnings), metadata
        
        return True, "All validations passed", metadata
    
    def process_pending_scripts(self):
        """Process all scripts in the pending directory"""
        pending_scripts = list(self.pending_dir.glob('*.py')) + list(self.pending_dir.glob('*.sh'))
        
        if not pending_scripts:
            print("No pending scripts to process")
            return
        
        print(f"Processing {len(pending_scripts)} pending script(s)...")
        print("="*60)
        
        for script_path in pending_scripts:
            print(f"\nValidating: {script_path.name}")
            
            is_valid, message, metadata = self.validate_script(script_path)
            
            if is_valid:
                dest_path = self.approved_dir / script_path.name
                script_path.rename(dest_path)
                
                self.log_event(
                    "REGISTRATION",
                    script_path.name,
                    "APPROVED",
                    f"Version: {metadata['version']}, Category: {metadata['category']}"
                )
                
                print(f"  Status: APPROVED")
                print(f"  Moved to: {dest_path}")
            else:
                dest_path = self.rejected_dir / script_path.name
                script_path.rename(dest_path)
                
                self.log_event(
                    "REGISTRATION",
                    script_path.name,
                    "REJECTED",
                    message
                )
                
                print(f"  Status: REJECTED")
                print(f"  Reason: {message}")
                print(f"  Moved to: {dest_path}")
        
        print("\n" + "="*60)
        print("Processing complete")
    
    def list_approved_scripts(self):
        """List all approved scripts with their metadata"""
        approved_scripts = list(self.approved_dir.glob('*.py')) + list(self.approved_dir.glob('*.sh'))
        
        if not approved_scripts:
            print("No approved scripts in registry")
            return
        
        print(f"\nApproved Scripts ({len(approved_scripts)}):")
        print("="*60)
        
        for script_path in approved_scripts:
            if script_path.suffix == '.py':
                metadata = self.extract_python_metadata(script_path)
            else:
                metadata = self.extract_bash_metadata(script_path)
            
            if metadata:
                print(f"\n{script_path.name}")
                print(f"  Name: {metadata.get('name', 'N/A')}")
                print(f"  Version: {metadata.get('version', 'N/A')}")
                print(f"  Description: {metadata.get('description', 'N/A')}")
                print(f"  Category: {metadata.get('category', 'N/A')}")
                print(f"  Risk Level: {metadata.get('risk_level', 'N/A')}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("Nexus Script Validator")
        print("\nUsage:")
        print("  python script_validator.py              # Process pending scripts")
        print("  python script_validator.py --list       # List approved scripts")
        print("  python script_validator.py --help       # Show this help")
        print("\nDirectories:")
        print("  scripts_registry/pending/    - Place new scripts here")
        print("  scripts_registry/approved/   - Validated scripts")
        print("  scripts_registry/rejected/   - Invalid scripts")
        print("  scripts_registry/registration_log.txt - Event log")
        return
    
    validator = ScriptValidator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        validator.list_approved_scripts()
    else:
        validator.process_pending_scripts()

if __name__ == "__main__":
    main()
