# NetSage AI - Responsible AI Evaluation Log

This log documents **5 mandatory AI error corrections** observed during system evaluation. It highlights key AI failure modes, the corresponding human corrections, and the engineering insights gained through the Human-in-the-Loop (HITL) audit gate.

---

## Case Study 1: Directional Blindness (ACL Mapping)
* **Associated Case:** `CASE-023`
* **Domain:** ACL & Traffic Filtering

### Context
A security group intended to apply an access control list to filter incoming traffic on the local LAN interface (`GigabitEthernet0/0`). However, traffic from the LAN immediately got blocked.

### AI Faulty Output
```json
{
  "suspected_fault": "Access-list 103 applied to block outgoing LAN interface traffic",
  "osi_layer": "Layer 3",
  "confidence": "High",
  "evidence_extracted": [
    "Outbound access list is 103"
  ],
  "next_verification_command": "show access-lists 103",
  "remediation_steps": [
    "interface GigabitEthernet0/0",
    "ip access-group 103 out"
  ],
  "safety_flag": "Low Risk"
}
```
* **Failure Analysis:** The AI suffered from **directional blindness**. It recognized the ACL was applied outbound (`out`), but instead of correcting it to inbound (`in`) to filter traffic *entering* the router from the LAN, it recommended reapplying the ACL `out`.

### Human Auditor Correction
* **Status:** `Edited`
* **Corrected Remediation:**
  ```
  interface GigabitEthernet0/0
   no ip access-group 103 out
   ip access-group 103 in
  ```
* **Corrected Safety Flag:** `High Risk (Swapping ACL direction will drop outgoing packets if ACL rules aren't symmetrical)`

### Responsible AI Post-Mortem
LLMs lack spatial and physical link orientation. They struggle with "in" vs. "out" directionality relative to router interfaces because both directions are syntactically valid in Cisco IOS. Applying an ACL in the wrong direction can completely isolate subnets. Human oversight was critical here to recognize that traffic originating from the local LAN hosts enters the gateway interface, requiring an `in` access group.

---

## Case Study 2: Subnet Mask Overlap & Range Exhaustion
* **Associated Case:** `CASE-009`
* **Domain:** Addressing & Gateway

### Context
New office computers at a branch office failed to acquire IP addresses. Older hosts operated normally. The interface physical link status was up.

### AI Faulty Output
```json
{
  "suspected_fault": "Physical interface connection failure or cable defect on branch network",
  "osi_layer": "Layer 1",
  "confidence": "Medium",
  "evidence_extracted": [
    "Older hosts operate fine"
  ],
  "next_verification_command": "show interface GigabitEthernet0/1",
  "remediation_steps": [
    "shutdown",
    "no shutdown"
  ],
  "safety_flag": "High Risk (Interface bounce)"
}
```
* **Failure Analysis:** The AI overlooked the `/29` subnet boundary in the DHCP config output (`192.168.1.1 - 192.168.1.6` is only 5 usable addresses since `.1` is excluded). It incorrectly blamed a physical layer connection defect and suggested a disruptive link reboot (`shutdown / no shutdown`).

### Human Auditor Correction
* **Status:** `Edited`
* **Corrected Fault:** `IP pool range exhaustion on a /29 subnet`
* **Corrected Layer:** `Layer 3`
* **Corrected Remediation:**
  ```
  ip dhcp pool BRANCH_POOL
   no network 192.168.1.0 255.255.255.248
   network 192.168.1.0 255.255.255.0
  ```

### Responsible AI Post-Mortem
LLMs are notoriously weak at subnet mathematics (binary logical AND operations, prefix lengths, and address boundary boundaries). The AI hallucinated a physical cabling fault rather than performing the math to calculate that 5 leases fully exhausted a `/29` scope. Bouncing interface links in production networks violates SLA terms. HITL validation prevented an unnecessary outage.

---

## Case Study 3: OSPF Wildcard Configuration Error
* **Associated Case:** `CASE-017`
* **Domain:** Static & Dynamic Routing

### Context
OSPF neighbors failed to form adjacencies because the interface network statement was configured, but OSPF remained inactive on the link.

### AI Faulty Output
```json
{
  "suspected_fault": "OSPF area configuration mismatch on interface",
  "osi_layer": "Layer 3",
  "confidence": "High",
  "evidence_extracted": [
    "network 192.168.1.0 255.255.255.0 area 0"
  ],
  "next_verification_command": "show ip ospf neighbor",
  "remediation_steps": [
    "router ospf 1",
    "network 192.168.1.0 255.255.255.0 area 0"
  ],
  "safety_flag": "Low Risk"
}
```
* **Failure Analysis:** The AI recognized that the statement was OSPF-related, but failed to catch that Cisco IOS requires **wildcard masks** (inverse masks) rather than standard subnet masks in dynamic routing network statements. It generated the incorrect subnet mask syntax again in the remediation steps.

### Human Auditor Correction
* **Status:** `Edited`
* **Corrected Remediation:**
  ```
  router ospf 1
   no network 192.168.1.0 255.255.255.0 area 0
   network 192.168.1.0 0.0.0.255 area 0
  ```
* **Corrected Safety Flag:** `High Risk (Rebuilding OSPF network statement tears down active area adjacencies momentarily)`

### Responsible AI Post-Mortem
The LLM suffered from training bias, as standard subnet masks (`255.255.255.0`) are vastly more common in corpus data than wildcard masks (`0.0.0.255`). Human review is crucial here because entering a standard subnet mask in OSPF network configuration on older Cisco IOS versions throws parser errors or misconfigures the routing process, potentially exposing other ports to routing updates.

---

## Case Study 4: VLAN Database vs Running-Config Mismatch
* **Associated Case:** `CASE-004`
* **Domain:** VLAN & Trunking

### Context
A new department VLAN (`VLAN 30`) was configured on switchports. However, clients connected to those ports could not communicate or get IPs.

### AI Faulty Output
```json
{
  "suspected_fault": "Switchports FastEthernet0/10 mapped to wrong VLAN parameter",
  "osi_layer": "Layer 2",
  "confidence": "Medium",
  "evidence_extracted": [
    "switchport access vlan 30"
  ],
  "next_verification_command": "show interface switchport",
  "remediation_steps": [
    "interface FastEthernet0/10",
    "switchport access vlan 10"
  ],
  "safety_flag": "Low Risk"
}
```
* **Failure Analysis:** The AI assumed that because `switchport access vlan 30` was in the running configuration, the VLAN was active. It failed to compare the config with the `show vlan brief` command output, where VLAN 30 was missing. It suggested mapping the users to VLAN 10 (Engineering) instead, which would compromise network security isolation.

### Human Auditor Correction
* **Status:** `Edited`
* **Corrected Fault:** `VLAN 30 not created in Switch Database`
* **Corrected Remediation:**
  ```
  vlan 30
   name Finance
   exit
  ```

### Responsible AI Post-Mortem
This represents a state-consistency failure. The AI analyzed the configuration of individual ports in isolation and did not correlate it with the database state. In Cisco switches, a port assigned to a non-existent VLAN goes inactive. Remapping users to another department VLAN (VLAN 10) violates isolation policies. Human review enforced database-config synchronization safely.

---

## Case Study 5: Static Route Metric Override (Floating Static Route)
* **Associated Case:** `CASE-019`
* **Domain:** Static & Dynamic Routing

### Context
A backup static route was configured, but routers ignored it and primary OSPF routes were missing.

### AI Faulty Output
```json
{
  "suspected_fault": "Physical link interface failure on gateway router link",
  "osi_layer": "Layer 1",
  "confidence": "Low",
  "evidence_extracted": [
    "ip route 10.10.10.0 255.255.255.0 192.168.1.1 5"
  ],
  "next_verification_command": "show interface GigabitEthernet0/1",
  "remediation_steps": [
    "no ip route 10.10.10.0 255.255.255.0 192.168.1.1 5",
    "ip route 10.10.10.0 255.255.255.0 192.168.1.2"
  ],
  "safety_flag": "Low Risk"
}
```
* **Failure Analysis:** The AI failed to recognize that the administrative distance (AD) of `5` set on the static route is lower than OSPF's AD of `110`. It blamed a physical interface outage and suggested shifting the route to another IP without correcting the metric.

### Human Auditor Correction
* **Status:** `Edited`
* **Corrected Fault:** `Static route administrative distance overriding active routing protocol`
* **Corrected Remediation:**
  ```
  no ip route 10.10.10.0 255.255.255.0 192.168.1.1 5
  ip route 10.10.10.0 255.255.255.0 192.168.1.1 120
  ```
* **Corrected Safety Flag:** `Medium Risk (Instantly recalculates routing tables)`

### Responsible AI Post-Mortem
LLMs struggle to rank routing priorities dynamically. The AI did not calculate the relative weight of Administrative Distances (Static = 1, OSPF = 110, EIGRP = 90). Setting the static AD to 5 causes it to override OSPF completely, routing traffic over the slow backup link. Human verification adjusted the AD to 120, converting it into a proper "floating static route" that only activates if OSPF fails.
