global domoticzUnitcount

import time
import pexpect
import subprocess
import sys
import re
import os
import requests
import json
import pdb
import urllib.parse

# Settings for the domoticz server
domoticzserver="127.0.0.1:8080"  # local host IP!!!!
domoticzHardwareIdx=None
domoticzUnitcount=0


class BluetoothctlError(Exception):
    """This exception is raised, when bluetoothctl fails to start."""
    pass

class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""
 
    def __init__(self):
        out = subprocess.check_output("rfkill unblock bluetooth", shell = True)
        self.child = pexpect.spawnu("bluetoothctl", echo = False)
 
    def get_output(self, command, pause = 0):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.child.send(command + "\n")
        time.sleep(pause)
        start_failed = self.child.expect(["bluetooth", pexpect.EOF])
 
        if start_failed:
            raise BluetoothctlError("Bluetoothctl failed after running " + command)
 
        return self.child.before.split("\r\n")
 
    def start_scan(self):
        """Start bluetooth scanning process."""
        try:
            out = self.get_output("scan on")
        except BluetoothctlError:
            print(e)
            return None
 
    def make_discoverable(self):
        """Make device discoverable."""
        try:
            out = self.get_output("discoverable on")
        except BluetoothctlError:
            print(e)
            return None
 
    def parse_device_info(self, info_string):
        """Parse a string corresponding to a device."""
        device = {}
        block_list = ["[\x1b[0;", "removed"]
        string_valid = not any(keyword in info_string for keyword in block_list)
 
        if string_valid:
            try:
                device_position = info_string.index("Device")
            except ValueError:
                pass
            else:
                if device_position > -1:
                    attribute_list = info_string[device_position:].split(" ", 2)
                    device = {
                        "mac_address": attribute_list[1],
                        "name": attribute_list[2]
                    }
 
        return device
 
    def get_available_devices(self):
        """Return a list of tuples of paired and discoverable devices."""
        try:
            out = self.get_output("devices")
        except BluetoothctlError:
            print(e)
            return None
        else:
            available_devices = []
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    available_devices.append(device)
 
            return available_devices

    def get_paired_devices(self):
        """Return a list of tuples of paired devices."""
        try:
            out = self.get_output("paired-devices")
        except BluetoothctlError:
            print(e)
            return None
        else:
            paired_devices = []
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    paired_devices.append(device)
 
            return paired_devices
 
    def get_discoverable_devices(self):
        """Filter paired devices out of available."""
        available = self.get_available_devices()
        paired = self.get_paired_devices()
 
        return [d for d in available if d not in paired]
 
    def get_device_info(self, mac_address):
        """Get device info by mac address."""
        try:
            out = self.get_output("info " + mac_address)
        except BluetoothctlError:
            print(e)
            return None
        else:
            return out
        
    def get_connectable_devices(self):
        """Get a  list of connectable devices.
        Must install 'sudo apt-get install bluez blueztools' to use this"""
        try:
            res = []
            out = subprocess.check_output(["hcitool", "scan"]).decode()  # Requires 'apt-get install bluez'
            out = out.split("\n")
            device_name_re = re.compile("^\t([0-9,:,A-F]{17})\t(.*)$")
            for line in out:
                device_name = device_name_re.match(line)
                if device_name != None:
                    res.append({
                            "mac_address": device_name.group(1),
                            "name": device_name.group(2)
                        })
        except BluetoothctlError:
            print(e)
            return None
        else:
            return res
 
    def is_connected(self):
        """Returns True if there is a current connection to any device, otherwise returns False"""
        try:
            res = False
            out = subprocess.check_output(["hcitool", "con"])  # Requires 'apt-get install bluez'
            out = out.split("\n")
            mac_addr_re = re.compile("^.*([0-9,:,A-F]{17}).*$")
            for line in out:
                mac_addr = mac_addr_re.match(line)
                if mac_addr != None:
                    res = True
        except BluetoothctlError:
            print(e)
            return None
        else:
            return res

    def pair(self, mac_address):
        """Try to pair with a device by mac address."""
        try:
            out = self.get_output("pair " + mac_address, 4)
        except BluetoothctlError:
            print(e)
            return None
        else:
            res = self.child.expect(["Failed to pair", "Pairing successful", pexpect.EOF])
            success = True if res == 1 else False
            return success
 
    def remove(self, mac_address):
        """Remove paired device by mac address, return success of the operation."""
        try:
            out = self.get_output("remove " + mac_address, 3)
        except BluetoothctlError:
            print(e)
            return None
        else:
            res = self.child.expect(["not available", "Device has been removed", pexpect.EOF])
            success = True if res == 1 else False
            return success
 
    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        try:
            out = self.get_output("connect " + mac_address, 2)
        except BluetoothctlError:
            print(e)
            return None
        else:
            res = self.child.expect(["Failed to connect", "Connection successful", pexpect.EOF])
            success = True if res == 1 else False
            return success
 
    def disconnect(self, mac_address):
        """Try to disconnect to a device by mac address."""
        try:
            out = self.get_output("disconnect " + mac_address, 2)
        except BluetoothctlError:
            print(e)
            return None
        else:
            res = self.child.expect(["Failed to disconnect", "Successful disconnected", pexpect.EOF])
            success = True if res == 1 else False
            return success

    def trust(self, mac_address):
        """Trust the device with the given MAC address"""
        try:
            out = self.get_output("trust " + mac_address, 4)
        except BluetoothctlError:
            print(e)
            return None
        else:
            res = self.child.expect(["not available", "trust succeeded", pexpect.EOF])
            success = True if res == 1 else False
            return success
 
    def start_agent(self):
        """Start agent"""
        try:
            out = self.get_output("agent on")
        except BluetoothctlError:
            print(e)
            return None
 
    def default_agent(self):
        """Start default agent"""
        try:
            out = self.get_output("default-agent")
        except BluetoothctlError:
            print(e)
            return None

 

def domoticzrequest (url):
    response = requests.get(url)
    return response.json()

def requestDzAll (idx):
    global domoticzUnitcount
    response = domoticzrequest('http://'+domoticzserver+'/json.htm?type=devices&filter=all')
    result = []
    if response["status"] == "OK":
        for i in response['result']:
            if "HardwareID" in i:
                if i["HardwareID"] == int(idx):  # we have a mac address
                    result.append(i)
                    if i["Unit"] >= domoticzUnitcount: domoticzUnitcount = i["Unit"] + 1
                
    return result

def requestDzOn (idx):
    response = domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=switchlight&idx=" + idx + "&switchcmd=On&level=0")
    return None

def requestDzOff (idx):
    response = domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=switchlight&idx=" + idx + "&switchcmd=Off&level=0")
    return None

def requestDzListHardware ():
    idx = None    
    response = domoticzrequest("http://" + domoticzserver + "/json.htm?type=hardware")
    if response["status"] == "OK":
        for i in response["result"]:
            #print (i['Name'])
            if i['Name'] == 'SmartThingsBT':
                idx = i['idx']
        if idx == None:
            idx = requestDzCreateHardware()
        
    return idx

def requestDzCreateHardware ():
    response = domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=addhardware&htype=15&port=1&name=SmartThingsBT&enabled=true")
    if response["status"] == "OK":
        return response["idx"]
    else:
        return None

def requestDzCreateDevice (name):
    unitCount = str(domoticzUnitcount)
    cName = name
    name = urllib.parse.quote_plus(name)
    req = "http://" + domoticzserver + "/json.htm?type=command&param=addswitch&name=" + name + "&description=undefined&used=false&switchtype=0&lighttype=0&hwdid=" + domoticzHardwareIdx + "&housecode=80&unitcode=" + unitCount
    response = domoticzrequest(req)
    
    if response["status"] == "OK":
        dzDevices = requestDzAll(domoticzHardwareIdx)
        
        if dzDevices[-1]["Name"] == cName:
            idx = dzDevices[-1]["idx"]
            req = "http://" + domoticzserver + "/json.htm?type=command&param=setunused&idx=" + idx
            response = domoticzrequest(req)
            print("Setting unused for " + cName + " with idx " + idx + " status was " + response["status"])
            
    return None

if __name__ == "__main__":

    print("Init bluetooth...")
    bl = Bluetoothctl()
    bl.start_scan()
    time.sleep(10)
    
    domoticzHardwareIdx = requestDzListHardware()
    
    if domoticzHardwareIdx == None:
        print("Failure to get Hardware Idx for SmartThingsBT, exit 99")
        sys.exit(99)
        
    while 1 == 1:
        
        allDzDevices = requestDzAll(domoticzHardwareIdx)
        
        #if len(allDzDevices) == 0:
        #    print("Failure to return devices from Domoticz, exit 99")
        #    sys.exit(99)            

        for i in bl.get_available_devices():
            dzExistingDevice = False
            for j in allDzDevices:
                if i["mac_address"] in j["Name"]:
                    dzExistingDevice = True
                    #print(j["Status"])
                    if j["Status"] == "Off":
                        print( time.strftime("%c") + " Presence detected of " + j["Name"])
                        requestDzOn(j["idx"])
                        
            if not dzExistingDevice:
                if not i["name"].replace("-",":") == i["mac_address"]:
                    dzName = "(BT) (" + i["name"] + ") " + i["mac_address"]
                    print( time.strftime("%c") + " Create presence device " + dzName)
                    domoticzUnitcount = domoticzUnitcount+1
                    requestDzCreateDevice(dzName)
                
        for i in allDzDevices:
            if "(BT)" in i["Name"]:
                blPresentDevice = False
                for j in bl.get_available_devices():
                    if j["mac_address"] in i["Name"]:
                        blPresentDevice = True
                if not blPresentDevice:
                    if i["Status"] == "On":
                        print(time.strftime("%c") + " No Presence detected of " + i["Name"])
                        requestDzOff(i["idx"])
            
        time.sleep(10)  
