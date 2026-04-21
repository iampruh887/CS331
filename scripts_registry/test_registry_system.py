#!/usr/bin/env python3
"""
Comprehensive test script for the Scripts Registry System
Demonstrates all components and their functionality
"""

import json
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_validator():
    """Test the script validator"""
    print_section("Testing Script Validator")
    
    print("\nListing approved scripts:")
    success, stdout, stderr = run_command("python3 scripts_registry/script_validator.py --list")
    if success:
        print(stdout)
    else:
        print(f"Error: {stderr}")
    
    return success

def test_approved_scripts():
    """Test all approved scripts"""
    print_section("Testing Approved Scripts")
    
    scripts = [
        ("analyze_srs_document.py", "Analyzing SRS documents"),
        ("validate_uml_diagrams.py", "Validating UML diagrams"),
        ("check_architecture_docs.py", "Checking architecture documentation")
    ]
    
    all_passed = True
    
    for script, description in scripts:
        print(f"\n{description}...")
        success, stdout, stderr = run_command(f"python3 scripts_registry/approved/{script}")
        
        if success:
            try:
                result = json.loads(stdout)
                if result.get("status") == "success":
                    print(f"  Status: SUCCESS")
                    print(f"  Output: {json.dumps(result['data'], indent=2)[:200]}...")
                else:
                    print(f"  Status: FAILED - {result.get('message')}")
                    all_passed = False
            except json.JSONDecodeError:
                print(f"  Status: FAILED - Invalid JSON output")
                all_passed = False
        else:
            print(f"  Status: ERROR - {stderr}")
            all_passed = False
    
    return all_passed

def test_sensitive_masking():
    """Test the sensitive output mask"""
    print_section("Testing Sensitive Output Masking")
    
    test_cases = [
        {
            "name": "Email and Password",
            "input": '{"user":"john","email":"john@example.com","password":"secret123"}',
            "expected_masks": ["[EMAIL_MASKED]", "[REDACTED]"]
        },
        {
            "name": "Phone and API Key",
            "input": '{"phone":"555-123-4567","api_key":"sk-1234567890abcdefghij"}',
            "expected_masks": ["[PHONE_MASKED]", "[REDACTED]"]
        },
        {
            "name": "Nested Sensitive Data",
            "input": '{"user":{"name":"Alice","email":"alice@test.com","credentials":{"password":"pass123"}}}',
            "expected_masks": ["[EMAIL_MASKED]", "[REDACTED]"]
        }
    ]
    
    all_passed = True
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        cmd = f"python3 scripts_registry/sensitive_output_mask.py '{test['input']}'"
        success, stdout, stderr = run_command(cmd)
        
        if success:
            try:
                result = json.loads(stdout)
                if result.get("status") == "success" and result.get("masking_applied"):
                    masked_output = json.dumps(result["masked_data"])
                    masks_found = all(mask in masked_output for mask in test["expected_masks"])
                    
                    if masks_found:
                        print(f"  Status: PASSED")
                        print(f"  Masked: {json.dumps(result['masked_data'])}")
                    else:
                        print(f"  Status: FAILED - Expected masks not found")
                        all_passed = False
                else:
                    print(f"  Status: FAILED - Masking not applied")
                    all_passed = False
            except json.JSONDecodeError:
                print(f"  Status: FAILED - Invalid JSON output")
                all_passed = False
        else:
            print(f"  Status: ERROR - {stderr}")
            all_passed = False
    
    return all_passed

def test_differencing_log():
    """Test the differencing log system"""
    print_section("Testing Differencing Log System")
    
    test_user = "test_user_demo"
    
    print("\n1. Logging first change...")
    cmd = f"python3 scripts_registry/differencing_log.py log {test_user} 'update_setting' 'config.json' '{{\"debug\":false}}' '{{\"debug\":true}}'"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        result = json.loads(stdout)
        print(f"  Status: {result['status'].upper()}")
        print(f"  Diff ID: {result.get('diff_id')}")
    else:
        print(f"  Status: FAILED - {stderr}")
        return False
    
    print("\n2. Logging second change...")
    cmd = f"python3 scripts_registry/differencing_log.py log {test_user} 'update_port' 'server.conf' '{{\"port\":8080}}' '{{\"port\":9090}}'"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        result = json.loads(stdout)
        print(f"  Status: {result['status'].upper()}")
        print(f"  Diff ID: {result.get('diff_id')}")
    else:
        print(f"  Status: FAILED - {stderr}")
        return False
    
    print("\n3. Viewing user history...")
    cmd = f"python3 scripts_registry/differencing_log.py history {test_user}"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        result = json.loads(stdout)
        print(f"  Status: {result['status'].upper()}")
        print(f"  Total diffs: {result.get('total_diffs')}")
        for entry in result.get('history', []):
            print(f"    - Diff {entry['diff_id']}: {entry['action']} on {entry['resource']}")
    else:
        print(f"  Status: FAILED - {stderr}")
        return False
    
    print("\n4. Reverting first change...")
    cmd = f"python3 scripts_registry/differencing_log.py revert {test_user} 1"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        result = json.loads(stdout)
        print(f"  Status: {result['status'].upper()}")
        print(f"  Restore state: {result.get('restore_state')}")
    else:
        print(f"  Status: FAILED - {stderr}")
        return False
    
    print("\n5. Cleaning up test data...")
    cmd = f"python3 scripts_registry/differencing_log.py clear {test_user}"
    success, stdout, stderr = run_command(cmd)
    
    if success:
        result = json.loads(stdout)
        print(f"  Status: {result['status'].upper()}")
    else:
        print(f"  Status: FAILED - {stderr}")
        return False
    
    return True

def test_registration_log():
    """Check the registration log"""
    print_section("Checking Registration Log")
    
    log_file = Path("scripts_registry/registration_log.txt")
    
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        print(f"\nTotal registration events: {len(lines)}")
        print("\nLast 5 events:")
        for line in lines[-5:]:
            print(f"  {line.strip()}")
        
        approved = sum(1 for line in lines if "APPROVED" in line)
        rejected = sum(1 for line in lines if "REJECTED" in line)
        
        print(f"\nSummary:")
        print(f"  Approved: {approved}")
        print(f"  Rejected: {rejected}")
        
        return True
    else:
        print("Registration log not found")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  NEXUS SCRIPTS REGISTRY SYSTEM - COMPREHENSIVE TEST")
    print("="*70)
    
    tests = [
        ("Script Validator", test_validator),
        ("Approved Scripts", test_approved_scripts),
        ("Sensitive Output Masking", test_sensitive_masking),
        ("Differencing Log System", test_differencing_log),
        ("Registration Log", test_registration_log)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\nTest '{test_name}' encountered an error: {e}")
            results[test_name] = False
    
    print_section("TEST SUMMARY")
    
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\nAll tests passed successfully!")
        return 0
    else:
        print(f"\n{total_tests - passed_tests} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
