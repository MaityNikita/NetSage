import re
from typing import Dict, Any

class NetworkRuleChecker:
    @staticmethod
    def audit_config(show_output: str) -> Dict[str, Any]:
        findings = []

        # 1. Check for administratively down interfaces
        down_ifaces = re.findall(r'(\S+)\s+is\s+administratively\s+down', show_output)
        if down_ifaces:
            findings.append({
                "rule": "INTERFACE_SHUTDOWN",
                "layer": "Layer 1",
                "detail": f"Interfaces shut down: {', '.join(down_ifaces)}",
                "suggested_fix": "interface <name> -> no shutdown"
            })

        # 2. Check for Native VLAN Mismatch logs
        if "Native VLAN mismatch detected" in show_output or re.search(r'Vlan mismatch', show_output, re.I):
            findings.append({
                "rule": "NATIVE_VLAN_MISMATCH",
                "layer": "Layer 2",
                "detail": "Trunk port native VLANs do not match across links",
                "suggested_fix": "switchport trunk native vlan <id>"
            })

        # 3. Check for Missing Default Gateway / 0.0.0.0 route
        if "show ip route" in show_output and "Gateway of last resort is not set" in show_output:
            findings.append({
                "rule": "NO_DEFAULT_ROUTE",
                "layer": "Layer 3",
                "detail": "No gateway of last resort configured",
                "suggested_fix": "ip route 0.0.0.0 0.0.0.0 <next-hop-ip>"
            })

        # 4. Check for IP Helper Address absence on DHCP-relayed subnets
        if "DHCP" in show_output and "ip helper-address" not in show_output:
            findings.append({
                "rule": "MISSING_DHCP_RELAY",
                "layer": "Layer 3",
                "detail": "Broadcast domain lacks ip helper-address pointing to DHCP server",
                "suggested_fix": "ip helper-address <dhcp-server-ip>"
            })

        return {
            "deterministic_faults_found": len(findings),
            "findings": findings
        }
