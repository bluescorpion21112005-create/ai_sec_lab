#!/usr/bin/env python3
"""
AI Security Lab - Main Application
Educational tool for learning AI-powered security testing
ONLY for use in authorized lab environments
"""

import argparse
import logging
import sys
from pathlib import Path
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.ai_engine import AISecurityEngine
from core.logger import setup_logger
from modules.subdomain_finder import AISubfinder
from modules.sqli_detector import AISQLiDetector
from modules.fuzzer import AIFuzzer
from modules.network_scanner import NetworkScanner
from modules.privesc_checker import PrivilegeEscalationChecker


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def setup_argparse():
    """Setup command line arguments"""
    parser = argparse.ArgumentParser(
        description="AI Security Lab - Educational Security Testing Tool",
        epilog="⚠️  ONLY use on systems you own or have written permission to test!"
    )
    
    parser.add_argument('--target', '-t', help='Target domain or IP')
    parser.add_argument('--module', '-m', 
                       choices=['subdomain', 'sqli', 'fuzzer', 'network', 'privesc', 'all'],
                       default='all', help='Module to run')
    parser.add_argument('--wordlist', '-w', default='datasets/subdomains.txt',
                       help='Wordlist file path')
    parser.add_argument('--output', '-o', default='results/',
                       help='Output directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--safe-mode', action='store_true',
                       help='Enable safe mode (no actual requests)')
    
    return parser


def main():
    """Main application entry point"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger(log_level)
    
    # Display warning
    print("\n" + "="*70)
    print("⚠️  WARNING: This tool is for EDUCATIONAL PURPOSES only!")
    print("⚠️  ONLY use on systems you own or have EXPLICIT permission!")
    print("="*70 + "\n")
    
    if args.safe_mode:
        print("🔒 Safe mode enabled - no actual requests will be made\n")
    
    # Load config
    config = load_config()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    logger.info("🤖 AI Security Lab Starting")
    
    # Initialize AI Engine
    ai_engine = AISecurityEngine()
    
    results = {}
    
    # Run modules
    if args.module in ['subdomain', 'all'] and args.target:
        logger.info("🔍 Running subdomain discovery...")
        finder = AISubfinder()
        
        if not args.safe_mode:
            subdomains = finder.scan(args.target, args.wordlist)
            finder.print_results(subdomains)
            results['subdomain'] = subdomains
        else:
            logger.info("Safe mode: skipping subdomain scan")
    
    if args.module in ['sqli', 'all'] and args.target:
        logger.info("💉 Running SQL injection detection...")
        detector = AISQLiDetector()
        
        if not args.safe_mode:
            result = detector.scan(args.target)
            print(f"SQLi Result: {result['message']}")
            results['sqli'] = result
        else:
            logger.info("Safe mode: skipping SQLi detection")
    
    if args.module in ['fuzzer', 'all'] and args.target:
        logger.info("🎯 Running fuzzer...")
        fuzzer = AIFuzzer()
        
        if not args.safe_mode:
            crash = fuzzer.fuzz_endpoint(args.target, max_requests=50)
            if crash:
                print(f"💥 Crash detected: {crash[:100]}")
            results['fuzzer'] = {'crash_found': crash is not None}
        else:
            logger.info("Safe mode: skipping fuzzer")
    
    if args.module in ['network', 'all']:
        logger.info("🌐 Running network scanner...")
        scanner = NetworkScanner()
        
        if not args.safe_mode:
            hosts = scanner.scan_network("192.168.1.0/24")  # Default network
            scanner.print_results(hosts)
            results['network'] = hosts
        else:
            logger.info("Safe mode: skipping network scan")
    
    if args.module in ['privesc', 'all']:
        logger.info("🔓 Running privilege escalation check...")
        checker = PrivilegeEscalationChecker()
        
        # This runs locally, safe mode doesn't affect it
        vulns = checker.run_check()
        checker.print_results(vulns)
        results['privesc'] = vulns
    
    logger.info("✅ Security Lab completed")
    
    return results


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)