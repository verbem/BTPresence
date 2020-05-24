# Version 2.02 l2ping implement with grace period when ping is gving not connected

import time
import sys
import requests
import urllib.parse
import bluetooth
import subprocess

# Settings for the domoticz server
domoticzserver="127.0.0.1:8080"  # local host IP!!!! not a remlote IP, it will not work
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

def btL2ping(mac_addr):
    process = subprocess.Popen(['sudo', 'l2ping', '-c', '3', '-d', '1', mac_addr], bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    rc = None
    lastLine = None
    
    while True:
        line = process.stdout.readline()
        if not line:
            break
        else:
            #print(mac_addr + " " + str(line))
            lastLine = line
            
    if lastLine == None:
        print (mac_addr + " not present (no output)")
    else:
        if str(lastLine).find('down') > 0:
            #print (mac_addr + " not present (down)")
            rc = None
        else:
            #print( mac_addr + " is present")
            rc = True
    return rc        

def requestDzOn (idx):
    domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=switchlight&idx=" + idx + "&switchcmd=On&level=0")
    return None

def requestDzOff (idx):
    domoticzrequest("http://" + domoticzserver + "/json.htm?type=command&param=switchlight&idx=" + idx + "&switchcmd=Off&level=0")
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
            print(time.strftime("%c") + " Setting unused for " + cName + " with idx " + idx + " status was " + response["status"])
            
    return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(sys.argv[1])
        domoticzserver = sys.argv[1]
        
    domoticzBTDevices = {} 
    domoticzHardwareIdx = requestDzListHardware()
    
    if domoticzHardwareIdx == None:
        print(time.strftime("%c") + " Failure to get Hardware Idx for SmartThingsBT, exit 99")
        sys.exit(99)
        
    while True:

        # detect new devices
        
        allDzDevices = requestDzAll(domoticzHardwareIdx)
        #btDevs = bluetooth.discover_devices(duration=search_time, flush_cache=True, lookup_names=True)        
        #btDevs = bluetooth.discover_devices(flush_cache=True, lookup_names=True)
              
        for mac_address, name in bluetooth.discover_devices(flush_cache=True, lookup_names=True):            
            dzExistingDevice = False
            
            for j in allDzDevices:               
                if mac_address in j["Name"]:
                    dzExistingDevice = True                   
                        
            if not dzExistingDevice:                
                if not name.replace("-",":") == mac_address:
                    dzName = "(BT) (" + name + ") " + mac_address
                    print( time.strftime("%c") + " Create presence device " + dzName)
                    domoticzUnitcount = domoticzUnitcount+1
                    requestDzCreateDevice(dzName)
                    domoticzBTDevices[mac_address] = 0
            else:
                if not mac_address in domoticzBTDevices:
                    domoticzBTDevices[mac_address] = 0                   
                    
        # Tracing of activated (used) devices in Domoticz        
        for i in allDzDevices:
            if "(BT)" in i["Name"] and i["Used"] == 1:
                BT, *btName, mac = i["Name"].split()

                if btL2ping(mac) == None:
                    if i["Status"] == "On":
                        
                        if mac in domoticzBTDevices:
                            if domoticzBTDevices[mac] > 4:
                                print(time.strftime("%c") + " No Presence detected of " + i["Name"])
                                requestDzOff(i["idx"])
                                domoticzBTDevices[mac] = 0
                            else:
                                domoticzBTDevices[mac] = domoticzBTDevices[mac] +1
                        else:
                            domoticzBTDevices[mac] = 1
                            
                elif i["Status"] == "Off":                
                    print(time.strftime("%c") + " Presence detected of " + i["Name"])
                    requestDzOn(i["idx"])
                    domoticzBTDevices[mac] = 0
