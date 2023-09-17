# exos-vlan-cutter
Small script for Extreme OS Devices and some methods for my in-work pet project

**Primary Objective: **
Change the assignment of policies from vlans to ports.
Download the policy, change its destination address check to vlan-id check, download it to the device, bind the ingress ports to the policy 

**Req:** pip install netmiko

1) Can download .pol policy file from/to device and change strings "destination-address 0.0.0.0/0" to "vlan-id "
2) Can get vlan tag in exos
3) Can get vlan ports
4) Can add ports to policy, check and refresh in device policy slices

