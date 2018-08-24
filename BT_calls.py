global domoticzUnitcount

import time
import sys
import re
import os
import requests
import json
import pdb
import urllib.parse
import bluetooth

# Settings for the domoticz server
domoticzserver="127.0.0.1:8080"  # local host IP!!!!
domoticzHardwareIdx=None
domoticzUnitcount=0

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
 
    domoticzHardwareIdx = requestDzListHardware()
    
    if domoticzHardwareIdx == None:
        print("Failure to get Hardware Idx for SmartThingsBT, exit 99")
        sys.exit(99)
                       
        
    while 1 == 1:
      
        allDzDevices = requestDzAll(domoticzHardwareIdx)

        search_time = 10
        blDevs = bluetooth.discover_devices(duration=search_time, flush_cache=True, lookup_names=True)
        
        for mac_address, name in blDevs:
            
            dzExistingDevice = False
            
            for j in allDzDevices:
                if mac_address in j["Name"]:
                    dzExistingDevice = True
                    
                    if j["Status"] == "Off":
                        print( time.strftime("%c") + " Presence detected of " + name)
                        requestDzOn(j["idx"])
                        
            if not dzExistingDevice:
                if not name.replace("-",":") == mac_address:
                    dzName = "(BT) (" + name + ") " + mac_address
                    print( time.strftime("%c") + " Create presence device " + dzName)
                    domoticzUnitcount = domoticzUnitcount+1
                    requestDzCreateDevice(dzName)
                
        for i in allDzDevices:
            if "(BT)" in i["Name"]:
                blPresentDevice = False
                for jmac, jname in blDevs:
                    if jmac in i["Name"]:
                        blPresentDevice = True
                if not blPresentDevice:
                    if i["Status"] == "On":
                        print(time.strftime("%c") + " No Presence detected of " + i["Name"])
                        requestDzOff(i["idx"])


