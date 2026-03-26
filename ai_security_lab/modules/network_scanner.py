#!/usr/bin/env python3
"""
Network scanner and discovery
Educational purpose only - Use only in your own network
"""

import socket
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Dict
import argparse

logger = logging.getLogger(__name__)

class NetworkScanner:
    """Network host and port scanner"""
    
    def __init__(self, timeout: float = 1.0):
        self.timeout = timeout
    
    def scan_host(self, ip: str, ports: List[int] = None) -> Dict:
        """Scan single host for open ports"""
        if ports is None:
            ports = [21, 22, 23, 80, 443, 445, 3389, 8080, 8443]
        
        open_ports = []
        for port in ports:
            if self._check_port(ip, port):
                open_ports.append(port)
        
        return {
            'ip': ip,
            'open_ports': open_ports,
            'status': 'up' if open_ports else 'unknown'
        }
    
    def _check_port(self, ip: str, port: int) -> bool:
        """Check if port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def ping_host(self, ip: str) -> bool:
        """Check if host is reachable"""
        try:
            socket.gethostbyaddr(ip)
            return True
        except:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect((ip, 80))
                sock.close()
                return True
            except:
                return False
    
    def scan_network(self, network: str, max_workers: int = 50) -> List[Dict]:
        """Scan entire network for live hosts"""
        try:
            net = ipaddress.ip_network(network, strict=False)
            hosts = [str(ip) for ip in net.hosts()]
        except ValueError as e:
            logger.error(f"Invalid network: {e}")
            return []
        
        logger.info(f"Scanning network {network} ({len(hosts)} hosts)")
        
        live_hosts = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.ping_host, host): host for host in hosts[:256]}
            
            for future in as_completed(futures):
                host = futures[future]
                if future.result():
                    ports = self.scan_host(host)
                    live_hosts.append(ports)
                    logger.info(f"Found live host: {host}")
        
        return live_hosts
    
    def print_results(self, results: List[Dict]):
        """Pretty print scan results"""
        if not results:
            print("No hosts found")
            return
        
        print("\n" + "="*60)
        print("📡 NETWORK SCAN RESULTS")
        print("="*60)
        
        for host in results:
            print(f"\nHost: {host['ip']}")
            if host['open_ports']:
                print(f"  Open ports: {', '.join(map(str, host['open_ports']))}")
            else:
                print("  No open ports found")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network Scanner")
    parser.add_argument("-n", "--network", default="192.168.1.0/24", help="Network to scan")
    parser.add_argument("-t", "--threads", type=int, default=50, help="Number of threads")
    
    args = parser.parse_args()
    
    scanner = NetworkScanner()
    results = scanner.scan_network(args.network, args.threads)
    scanner.print_results(results)