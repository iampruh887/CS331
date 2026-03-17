#!/usr/bin/env python3
"""
Differencing Log System for Nexus Self-Correction Engine
Maintains last 5 state differences per user for rollback capability
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

class DifferencingLog:
    def __init__(self, log_dir: str = "scripts_registry/diff_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_diffs = 5
    
    def _get_user_log_file(self, user_id: str) -> Path:
        """Get the log file path for a specific user"""
        safe_user_id = hashlib.md5(user_id.encode()).hexdigest()[:16]
        return self.log_dir / f"user_{safe_user_id}_diffs.json"
    
    def _load_user_log(self, user_id: str) -> List[Dict]:
        """Load existing log for a user"""
        log_file = self._get_user_log_file(user_id)
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_user_log(self, user_id: str, log_data: List[Dict]):
        """Save log data for a user"""
        log_file = self._get_user_log_file(user_id)
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def compute_diff(self, before_state: Any, after_state: Any) -> Dict:
        """
        Compute difference between two states
        Returns a diff object that can be used for rollback
        """
        diff = {
            "before": before_state,
            "after": after_state,
            "diff_type": self._determine_diff_type(before_state, after_state)
        }
        
        return diff
    
    def _determine_diff_type(self, before: Any, after: Any) -> str:
        """Determine the type of change"""
        if before is None and after is not None:
            return "create"
        elif before is not None and after is None:
            return "delete"
        elif before != after:
            return "modify"
        else:
            return "no_change"
    
    def log_change(self, user_id: str, action: str, resource: str, 
                   before_state: Any, after_state: Any, metadata: Optional[Dict] = None) -> Dict:
        """
        Log a state change for a user
        
        Args:
            user_id: Unique identifier for the user
            action: Description of the action performed
            resource: Resource that was modified (e.g., file path, database record)
            before_state: State before the change
            after_state: State after the change
            metadata: Additional context about the change
        
        Returns:
            Result dictionary with diff_id for reference
        """
        try:
            user_log = self._load_user_log(user_id)
            
            diff = self.compute_diff(before_state, after_state)
            
            diff_entry = {
                "diff_id": len(user_log) + 1,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "diff": diff,
                "metadata": metadata or {},
                "reverted": False
            }
            
            user_log.append(diff_entry)
            
            if len(user_log) > self.max_diffs:
                user_log = user_log[-self.max_diffs:]
                for i, entry in enumerate(user_log, 1):
                    entry["diff_id"] = i
            
            self._save_user_log(user_id, user_log)
            
            return {
                "status": "success",
                "diff_id": diff_entry["diff_id"],
                "timestamp": diff_entry["timestamp"],
                "message": f"Change logged successfully (keeping last {self.max_diffs} diffs)"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to log change: {str(e)}"
            }
    
    def get_user_history(self, user_id: str, limit: Optional[int] = None) -> Dict:
        """
        Get change history for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of entries to return (default: all)
        
        Returns:
            Dictionary with user's change history
        """
        try:
            user_log = self._load_user_log(user_id)
            
            if limit:
                user_log = user_log[-limit:]
            
            return {
                "status": "success",
                "user_id": user_id,
                "total_diffs": len(user_log),
                "history": user_log
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to retrieve history: {str(e)}"
            }
    
    def get_diff_by_id(self, user_id: str, diff_id: int) -> Dict:
        """Get a specific diff entry by ID"""
        try:
            user_log = self._load_user_log(user_id)
            
            for entry in user_log:
                if entry["diff_id"] == diff_id:
                    return {
                        "status": "success",
                        "diff": entry
                    }
            
            return {
                "status": "error",
                "message": f"Diff ID {diff_id} not found for user {user_id}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to retrieve diff: {str(e)}"
            }
    
    def revert_change(self, user_id: str, diff_id: int) -> Dict:
        """
        Revert a specific change by returning the before state
        
        Args:
            user_id: User identifier
            diff_id: ID of the diff to revert
        
        Returns:
            Dictionary with the before state for restoration
        """
        try:
            user_log = self._load_user_log(user_id)
            
            for entry in user_log:
                if entry["diff_id"] == diff_id:
                    if entry["reverted"]:
                        return {
                            "status": "warning",
                            "message": "This change has already been reverted",
                            "diff_id": diff_id
                        }
                    
                    entry["reverted"] = True
                    entry["reverted_at"] = datetime.now().isoformat()
                    
                    self._save_user_log(user_id, user_log)
                    
                    return {
                        "status": "success",
                        "diff_id": diff_id,
                        "action": entry["action"],
                        "resource": entry["resource"],
                        "restore_state": entry["diff"]["before"],
                        "message": "Revert information retrieved. Apply restore_state to complete rollback."
                    }
            
            return {
                "status": "error",
                "message": f"Diff ID {diff_id} not found for user {user_id}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to revert change: {str(e)}"
            }
    
    def clear_user_history(self, user_id: str) -> Dict:
        """Clear all history for a user"""
        try:
            log_file = self._get_user_log_file(user_id)
            
            if log_file.exists():
                log_file.unlink()
            
            return {
                "status": "success",
                "message": f"History cleared for user {user_id}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to clear history: {str(e)}"
            }

def main():
    """CLI interface for the differencing log"""
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print("Differencing Log System for Self-Correction")
        print("\nUsage:")
        print("  python differencing_log.py log <user_id> <action> <resource> '<before_json>' '<after_json>'")
        print("  python differencing_log.py history <user_id> [limit]")
        print("  python differencing_log.py get <user_id> <diff_id>")
        print("  python differencing_log.py revert <user_id> <diff_id>")
        print("  python differencing_log.py clear <user_id>")
        print("\nExamples:")
        print("  python differencing_log.py log user123 'update_config' '/etc/app.conf' '{\"port\":8080}' '{\"port\":9090}'")
        print("  python differencing_log.py history user123 5")
        print("  python differencing_log.py revert user123 3")
        sys.exit(0)
    
    diff_log = DifferencingLog()
    command = sys.argv[1]
    
    if command == "log" and len(sys.argv) >= 7:
        user_id = sys.argv[2]
        action = sys.argv[3]
        resource = sys.argv[4]
        before_state = json.loads(sys.argv[5])
        after_state = json.loads(sys.argv[6])
        
        result = diff_log.log_change(user_id, action, resource, before_state, after_state)
        print(json.dumps(result, indent=2))
    
    elif command == "history" and len(sys.argv) >= 3:
        user_id = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        
        result = diff_log.get_user_history(user_id, limit)
        print(json.dumps(result, indent=2))
    
    elif command == "get" and len(sys.argv) >= 4:
        user_id = sys.argv[2]
        diff_id = int(sys.argv[3])
        
        result = diff_log.get_diff_by_id(user_id, diff_id)
        print(json.dumps(result, indent=2))
    
    elif command == "revert" and len(sys.argv) >= 4:
        user_id = sys.argv[2]
        diff_id = int(sys.argv[3])
        
        result = diff_log.revert_change(user_id, diff_id)
        print(json.dumps(result, indent=2))
    
    elif command == "clear" and len(sys.argv) >= 3:
        user_id = sys.argv[2]
        
        result = diff_log.clear_user_history(user_id)
        print(json.dumps(result, indent=2))
    
    else:
        print(json.dumps({
            "status": "error",
            "message": "Invalid command or missing arguments. Use --help for usage information."
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
