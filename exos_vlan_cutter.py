from netmiko import (ConnectHandler, 
                     file_transfer,
                     NetmikoTimeoutException,
                     NetmikoAuthenticationException)
import re
import getpass, sys


class DeviceWorker(object):
    def __init__(self):
        self.conn_handler: ConnectHandler = None
        self.vlans_ports: dict = {}
        self.vlans_tags: dict = {}

        self.device_conn: dict = {
            'device_type': 'extreme_exos',
            "host": "HOST",
            "username": "USERNAME",
            "password": "PASSWORD"
            }
        
        self.conn_open()
        # get vlan tag
        self.show_vlans_tags(["VLAN_NAME"])
        # get vlan ports
        self.show_vlans_ports(["VLAN_NAME"])
        # download .pol files from device
        self.transfer_policies(["VLAN_NAME"], direction="get")

        self.policy_changer("VLAN_NAME", self.vlans_tags["VLAN_NAME"])
        

    def conn_open(self):
        if self.conn_handler is None:
            try:
                self.conn_handler = ConnectHandler(**self.device_conn)
                return True
            except Exception as e:
                print(e)
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
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(error)
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
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(error)
            return False

    def policy_unconfugire(self, policies):
        try:
            for policy in policies:
                output = self.conn_handler.send_command("unconfigure access-list" + policy)
                print(output)
                return True
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(error)

    def transfer_policies(self, policies, direction):
        for policy in policies:
            file = policy + ".pol"
            self.file_transfer = {}
            try:
                self.file_transfer = file_transfer(self.conn_handler, file, file, direction = direction)
                print(self.file_transfer)
            except Exception as e:
                print(e)

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
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(error)
            return False

    def policy_refresh(self, policy):
        refresh_pattern = r"refresh done!"
        try:
            output = self.conn_handler.send_command("refresh policy " + policy)

            if re.match(refresh_pattern, output):
                return True
            else:
                return False
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(error)
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
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as error:
            print(error)
            return False

worker = DeviceWorker()




    