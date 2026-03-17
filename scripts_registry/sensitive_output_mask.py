#!/usr/bin/env python3
"""
Sensitive Output Mask Script for Nexus Intelligent Chatbot System
Masks PII/SPII data in JSON outputs before returning to users
"""

import json
import re
import sys
from typing import Any, Dict, List, Union

class SensitiveDataMasker:
    def __init__(self):
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            'api_key': r'\b(?:sk|pk|api)[-_]?[a-zA-Z0-9]{20,}\b',
            'password': r'(?i)(?:password|passwd|pwd)[\s:=]+[^\s,}]+',
            'token': r'(?i)(?:token|bearer)[\s:=]+[^\s,}]+',
            'secret': r'(?i)(?:secret|key)[\s:=]+[^\s,}]+',
        }
        
        self.sensitive_keys = [
            'password', 'passwd', 'pwd', 'secret', 'api_key', 'apikey',
            'token', 'auth', 'authorization', 'ssn', 'social_security',
            'credit_card', 'creditcard', 'cvv', 'pin', 'private_key',
            'privatekey', 'access_token', 'refresh_token', 'session_id',
            'cookie', 'credentials'
        ]
    
    def mask_string(self, text: str, pattern_name: str = None) -> str:
        """Mask sensitive data in a string"""
        if not isinstance(text, str):
            return text
        
        masked_text = text
        
        for name, pattern in self.pii_patterns.items():
            if pattern_name and name != pattern_name:
                continue
            
            if name == 'email':
                masked_text = re.sub(pattern, '[EMAIL_MASKED]', masked_text)
            elif name == 'phone':
                masked_text = re.sub(pattern, '[PHONE_MASKED]', masked_text)
            elif name == 'ssn':
                masked_text = re.sub(pattern, '[SSN_MASKED]', masked_text)
            elif name == 'credit_card':
                masked_text = re.sub(pattern, '[CARD_MASKED]', masked_text)
            elif name == 'ip_address':
                masked_text = re.sub(pattern, '[IP_MASKED]', masked_text)
            elif name == 'api_key':
                masked_text = re.sub(pattern, '[API_KEY_MASKED]', masked_text)
            elif name in ['password', 'token', 'secret']:
                masked_text = re.sub(pattern, f'[{name.upper()}_MASKED]', masked_text)
        
        return masked_text
    
    def is_sensitive_key(self, key: str) -> bool:
        """Check if a key name indicates sensitive data"""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.sensitive_keys)
    
    def mask_value(self, value: Any) -> Any:
        """Mask a single value based on its type"""
        if isinstance(value, str):
            return self.mask_string(value)
        elif isinstance(value, dict):
            return self.mask_dict(value)
        elif isinstance(value, list):
            return self.mask_list(value)
        else:
            return value
    
    def mask_dict(self, data: Dict) -> Dict:
        """Recursively mask sensitive data in a dictionary"""
        masked_data = {}
        
        for key, value in data.items():
            if self.is_sensitive_key(key):
                if isinstance(value, str) and value:
                    masked_data[key] = '[REDACTED]'
                elif isinstance(value, (int, float)):
                    masked_data[key] = '[REDACTED]'
                else:
                    masked_data[key] = '[REDACTED]'
            else:
                masked_data[key] = self.mask_value(value)
        
        return masked_data
    
    def mask_list(self, data: List) -> List:
        """Recursively mask sensitive data in a list"""
        return [self.mask_value(item) for item in data]
    
    def mask_json(self, json_input: Union[str, Dict]) -> Dict:
        """
        Main function to mask sensitive data in JSON
        
        Args:
            json_input: Either a JSON string or a dictionary
        
        Returns:
            Dictionary with masked sensitive data
        """
        try:
            if isinstance(json_input, str):
                data = json.loads(json_input)
            else:
                data = json_input
            
            masked_data = self.mask_value(data)
            
            return {
                "status": "success",
                "masked_data": masked_data,
                "masking_applied": True
            }
            
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": f"Invalid JSON input: {str(e)}",
                "masking_applied": False
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Masking failed: {str(e)}",
                "masking_applied": False
            }

def main():
    """CLI interface for the masker"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: python sensitive_output_mask.py '<json_string>' or pipe JSON via stdin"
        }))
        sys.exit(1)
    
    masker = SensitiveDataMasker()
    
    if sys.argv[1] == "-":
        json_input = sys.stdin.read()
    else:
        json_input = sys.argv[1]
    
    result = masker.mask_json(json_input)
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("Sensitive Output Mask Script")
        print("\nMasks PII/SPII data in JSON outputs")
        print("\nUsage:")
        print("  python sensitive_output_mask.py '<json_string>'")
        print("  echo '<json>' | python sensitive_output_mask.py -")
        print("\nMasked Data Types:")
        print("  - Email addresses")
        print("  - Phone numbers")
        print("  - Social Security Numbers")
        print("  - Credit card numbers")
        print("  - IP addresses")
        print("  - API keys and tokens")
        print("  - Passwords and secrets")
        print("\nExample:")
        print('  python sensitive_output_mask.py \'{"email":"user@example.com","password":"secret123"}\'')
        sys.exit(0)
    
    main()
