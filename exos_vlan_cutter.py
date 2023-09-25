#!/usr/bin/env python
import argparse
from datetime import datetime
from netmiko import (ConnectHandler, 
                     file_transfer,
                     NetmikoTimeoutException,
                     NetmikoAuthenticationException)
import re
import getpass, sys

__version__ = "0.1.0"

netmiko_exceptions = (NetmikoTimeoutException,
                      NetmikoAuthenticationException)

class DeviceWorker():
    def __init__(self):
        #self.start_time = datetime.now()

        #self.conn_handler: ConnectHandler = None
        #self.vlans_ports: dict = {}
        #self.vlans_tags: dict = {}

        #self.device_conn: dict = {
        #    'device_type': 'extreme_exos',
        #    "host": "HOST",
        #    "username": "USERNAME",
        #    "password": "PASSWORD"
        #    }
        
        #self.conn_open()
        ## get vlan tag
        #self.show_vlans_tags(["VLAN_NAME"])
        ## get vlan ports
        #self.show_vlans_ports(["VLAN_NAME"])
        ## download .pol files from device
        #self.transfer_policies(["POLICY_NAME"], direction="get")
        ## Change destination-address 0.0.0.0/0 to vlan tag
        #self.policy_changer("POLICY_NAME", self.vlans_tags["VLAN_NAME"])

        """
        # Exemple of nexts steps
      
        # unconfig policy from vlan
        # self.policy_unconfugire(["POLICY_NAME"])

        # transfer .pol files to device
        # self.transfer_policies(["POLICY_NAME"], direction="put")

        # Check policy syntax on device
        # self.policy_check("POLICY_NAME")

        # Bind policy with same named vlan
        # self.policy_configure("POLICY_NAME")
        
        # Refresh policy slices on device
        # self.policy_refresh("POLICY_NAME")
        """
    
    def args_parser(self, args):
        prog = "Exos Spy"
        description = "Script to get information from exos device"
        parser = argparse.ArgumentParser(prog = prog, description=description)

        parser.add_argument(
            "-devices",
            nargs="?",
            help="Device / group of devices to use",
            action="store",
            type=str,
        )
        parser.add_argument(
            "-cmd",
            help="Remote command to execute",
            action="store",
            default=None,
            type=str,
        )
        parser.add_argument(
            "-runtime", 
            help="Display script runtime", 
            action="store_true",
        )

        parser.add_argument("--set_username", help="Setup you username at .env", action="store", type=str)
        parser.add_argument("--set_password", help="Setup you password at .env", action="store", type=str)
        parser.add_argument("--set_secret", help="Setup you SSH secret at .env", action="store", type=str)

        parser.add_argument("--inventory", help="List devices from inventory", action="store_true")
        parser.add_argument("--version", help="Display version", action="store_true")

        cli_args = parser.parse_args(args)
        if not cli_args.inventory and not cli_args.version:
            if not cli_args.devices:
                parser.error("Enter the devices")
        return cli_args


    def main(self, args):
        cli_args = self.args_parser(args)
        print(cli_args)
        pass

    def conn_open(self):
        if self.conn_handler is None:
            try:
                self.conn_handler = ConnectHandler(**self.device_conn)
                return True
            except Exception as error:
                print("Connection failed: " + error)
                return False
    
    def show_vlans_ports(self, vlans):
        try:
            port_pattern = r"\s[0-9]+"

            for vlan in vlans:
                # configure vlan NAME add ports 1,2 tagged
                output = self.conn_handler.send_command("show configuration | include (" + vlan + ").*(untagged|tagged)")
                # configure vlan NAME add ports 1 2 tagged
                no_commas_output = output.replace(",", " ")

                # [" 1"," 2"]
                port_list  = re.findall(port_pattern, no_commas_output)
                
                # ["1","2"]
                port_list = [x.strip(' ') for x in port_list]

                # return nested dict: {"vlan" : ["port", "port"]}
                self.vlans_ports[vlan] = port_list
            return True
        except netmiko_exceptions as error:
            print("CMD failed: " + error)
            return False

    def show_vlans_tags(self, vlans):
        print("show_vlans_tags")
        try:
            tag_pattern = r"[A-Za-z]+\s[0-9]+"

            for vlan in vlans:
                # Admin State:         Enabled     Tagging:   802.1Q Tag 666
                output = self.conn_handler.send_command("show vlan "+vlan+" | include Tagging")

                # walkaround to make tag from output
                search_tag  = re.search(tag_pattern, output)
                if search_tag is not None:
                    dirty_tag = search_tag.group()
                    tag = re.sub("[^0-9]", "", dirty_tag)

                # {'NameVlan': 'Tag'}
                self.vlans_tags[vlan] = tag
            return True
        except netmiko_exceptions as error:
            print("CMD failed: " + error)
            return False

    def policy_unconfugire(self, policies):
        try:
            for policy in policies:
                output = self.conn_handler.send_command("unconfigure access-list" + policy)
                print(output)
                return True
        except netmiko_exceptions as error:
            print("Unconfigure failed: " + error)

    def transfer_policies(self, policies, direction):
        for policy in policies:
            file = policy + ".pol"
            self.file_transfer = {}
            try:
                self.file_transfer = file_transfer(self.conn_handler, file, file, direction = direction)
                print(self.file_transfer)
            except netmiko_exceptions as error:
                print("Transfer failed: " + error)

    # change in .pol file destination-address 0.0.0.0/0, or string what you want to vlan-id
    def policy_changer(self, file, vlan_id):
        vlan_id = self.vlans_tags[file]
        filename = f'{file}.pol'

        print("started changer with file: " + filename, " and vlan-id: " + vlan_id)
        with open(filename, "r") as file:
            filedata  = file.read()

        filedata = filedata.replace("destination-address 0.0.0.0/0", "vlan-id " + vlan_id )

        with open(filename, 'w') as file:
            file.write(filedata)
            print(".pol changed")

        return True

    def policy_check(self, policy):
        # Error:  Policy testpol has syntax errors
        # Policy file check successful.
        check_pattern = r"successful"
        try:
            output = self.conn_handler.send_command("check policy " + policy)

            if re.match(check_pattern, output):
                return True
            else:
                return False
        except netmiko_exceptions as error:
            print("Check failed: " + error)
            return False

    def policy_refresh(self, policy):
        refresh_pattern = r"refresh done!"
        try:
            output = self.conn_handler.send_command("refresh policy " + policy)

            if re.match(refresh_pattern, output):
                return True
            else:
                return False
        except netmiko_exceptions as error:
            print("Refresh failed: " + error)
            return False
    
    # TEST
    # IF YOU POLICY NAME = VLAN NAME
    # INGRESS ONLY, some devices models dont support egress, test on you device
    def policy_configure(self, policy):
        try:
            # use nested dict: {"vlan" : ["port", "port"]} 
            for port in self.vlans_ports[policy]:
                output = self.conn_handler.send_command("configure access-list "+ policy +" ports "+ port +" ingress")
                print(output)
            return True
        except netmiko_exceptions as error:
            print("Configure failed: " + error)
            return False

if __name__ == "__main__":
    worker = DeviceWorker()
    sys.exit(worker.main((sys.argv[1:])))






    