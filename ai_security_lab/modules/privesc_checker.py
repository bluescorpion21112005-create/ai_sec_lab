#!/usr/bin/env python3
"""
Privilege escalation checker
Educational purpose only - Use only on your own systems
"""

import subprocess
import os
import sys
import logging
from typing import List, Dict
import argparse

logger = logging.getLogger(__name__)

class PrivilegeEscalationChecker:
    """Check for privilege escalation vectors"""
    
    def __init__(self):
        self.vulnerabilities = []
    
    def check_linux(self) -> List[Dict]:
        """Check Linux for privilege escalation vectors"""
        results = []
        
        # Check sudo permissions
        try:
            sudo_output = subprocess.getoutput("sudo -l 2>/dev/null")
            if "NOPASSWD" in sudo_output:
                results.append({
                    'type': 'sudo_nopasswd',
                    'severity': 'high',
                    'description': 'User can run sudo commands without password',
                    'details': sudo_output
                })
        except:
            pass
        
        # Check SUID binaries
        try:
            suid_binaries = subprocess.getoutput("find / -perm -4000 -type f 2>/dev/null")
            suid_list = [b for b in suid_binaries.split('\n') if b]
            if suid_list:
                dangerous = ['find', 'vim', 'nano', 'cp', 'mv', 'python', 'perl']
                for binary in suid_list:
                    for dangerous_bin in dangerous:
                        if dangerous_bin in binary:
                            results.append({
                                'type': 'suid_binary',
                                'severity': 'high',
                                'description': f'Dangerous SUID binary: {binary}',
                                'details': binary
                            })
        except:
            pass
        
        # Check writable files
        try:
            writable = subprocess.getoutput("find / -writable -type f 2>/dev/null | head -20")
            if writable:
                results.append({
                    'type': 'writable_files',
                    'severity': 'medium',
                    'description': 'Writable system files found',
                    'details': writable[:200]
                })
        except:
            pass
        
        return results
    
    def check_windows(self) -> List[Dict]:
        """Check Windows for privilege escalation vectors"""
        results = []
        
        if sys.platform != 'win32':
            return results
        
        try:
            # Check privileges
            priv_output = subprocess.getoutput("whoami /priv")
            dangerous_privs = ['SeDebugPrivilege', 'SeTakeOwnershipPrivilege', 'SeImpersonatePrivilege']
            for priv in dangerous_privs:
                if priv in priv_output and "Disabled" not in priv_output.split(priv)[1][:20]:
                    results.append({
                        'type': 'dangerous_privilege',
                        'severity': 'high',
                        'description': f'User has {priv} enabled',
                        'details': priv
                    })
        except:
            pass
        
        return results
    
    def run_check(self) -> List[Dict]:
        """Run all privilege escalation checks"""
        logger.info("Running privilege escalation checks...")
        
        if sys.platform == 'linux' or sys.platform == 'darwin':
            results = self.check_linux()
        elif sys.platform == 'win32':
            results = self.check_windows()
        else:
            results = []
        
        logger.info(f"Found {len(results)} potential privilege escalation vectors")
        return results
    
    def print_results(self, results: List[Dict]):
        """Pretty print results"""
        if not results:
            print("✅ No obvious privilege escalation vectors found")
            return
        
        print("\n" + "="*70)
        print("🔓 PRIVILEGE ESCALATION VECTORS")
        print("="*70)
        
        severity_colors = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }
        
        for res in results:
            emoji = severity_colors.get(res['severity'], '⚪')
            print(f"\n{emoji} {res['type'].upper()} [{res['severity'].upper()}]")
            print(f"   Description: {res['description']}")
            print(f"   Details: {res['details'][:100]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Privilege Escalation Checker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    
    checker = PrivilegeEscalationChecker()
    results = checker.run_check()
    checker.print_results(results)