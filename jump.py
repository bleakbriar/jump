#!/usr/bin/python
'''

SSH Management System
Automates SSH connections to VPS and Dedicated servers from desktop

Author:  Bleakbriar
Last modified 07/11/2019


'''

import requests
import argparse
import os
import time
from urllib import (urlencode, urlopen)
from re import (search)

#=== List of dedicated server prefixes ============================
dedicatedPrefixes=["ded", "advanced", "elite", "cc"]
sharedPrefixes=["biz", "ecbiz", "res", "ecres", "wp", "ld"]
#=== User credentials =============================================
# Jumpstation
jsUser = ""     
jsIP = "" 
# cpJump
authUser = ""
authPW = ""
#=== Primary Functions ===============================================================

requests.packages.urllib3.disable_warnings()

def isVPS(server):
    return server.lower().startswith("vps")

def isDedi(server):
    for serverType in dedicatedPrefixes:
        if(server.lower().startswith(serverType)):
            return True
    return False

def isShared(server):
    for serverType in sharedPrefixes:
        if(server.lower().startswith(serverType)):
            return True
    return False

def getNode(server):
    vpsNum = server[3:]
    result = urlopen('https://imhsc.imhadmin.net/blocks/VPS/vps_resultfind.php', urlencode({'vps':vpsNum})).read()
    noderegex = '((ec)?vp[0-9]+s?)|((ec|wc)comp[0-9]+-[a-z]+[0-9]+)'
    match = search('on ' + noderegex, result)
    if match:
        return match.group(0)
    else:
        print("[!] Unable to locate Node for " + server)
        return ""


def vpsJump(server, flag):
    print("\t[+] Connecting through JumpStation...\n\n")
    jsCommand = "vpsfind " + server[3:] + " " + flag
    os.system('ssh -t ' + jsUser + '@' + jsIP + ' "' + jsCommand + '"')

def vpsDirectJump(server, flag):
    vpsNum = server[3:]
    sshCommand = "ssh -t -oConnectTimeout=7 -o StrictHostKeyChecking=no -o PasswordAuthentication=no"
    if(flag == "n"):
        nodeCommand = ''
    else:
        nodeCommand = "vzctl enter " + vpsNum
    print("\t[LOCATING NODE]")
    vNode = getNode(server)
    vNodeAddress = jsUser +"@" + vNode + ".inmotionhosting.com"
    print("\t[CONNECTING]")
    os.system(sshCommand + " " + vNodeAddress + " " + nodeCommand)

def dediJump(server, port):
    print("\t[SETUP] Root Key")
    payload = {"server" : server, "port" : port}
    r = requests.post("https://cpjump.inmotionhosting.com/dedtmpkeys/process-dedkey.php", data=payload, auth=(authUser, authPW), verify=False)
    raw_input("\t[+] Press enter once key setup has been confirmed...")
    os.system("ssh -o StrictHostKeyChecking=no -p " + port + " root@" + server + ".inmotionhosting.com")

def dediKeylessJump(server, port):
    print("\t [BYPASS] Skipping root key setup....")
    os.system("ssh -o StrictHostKeyChecking=no -p " + port + " root@" + server + ".inmotionhosting.com")

def sharedJump(server, js):
    print("\t[+] Connecting...\n\n")
    if(js):
        jsCommand = "ssh -q -o StrictHostKeyChecking=no " + server
        os.system('ssh -t ' + jsUser + '@' + jsIP + ' "' + jsCommand + '"')
    else:
        os.system('ssh -q -o StrictHostKeyChecking=no ' + jsUser + "@" + server + ".inmotionhosting.com")


#=== Secondary Functions =====================================================================================================
def bounceHandler(args):
    if(args.bounce):
        print("[TEST] Pinging: " + args.server)
        pingCommand = "ping -c1 -w2 " + args.server  + ".inmotionhosting.com 2>&1 > /dev/null"
        while(True):
            response = os.system(pingCommand)
            if(response == 0):
                break
        print("\t[SUCCESS] Server responding.")
        print("\t\t[+] Allowing 10 seconds for SSHD to come online")
        time.sleep(10)

def VPSHandler(args):
    if(isVPS(args.server)):
        if( not jsUser and not jsIP):
            print("[INVALID]")
            print("\t[!] No jumpstation credentials configured\n")
        else:
            if(args.gotoNode):
                if(args.jumpstation):
                    vpsJump(args.server, "n")
                else:
                    vpsDirectJump(args.server, "n")
            else:
                if(args.jumpstation):
                    vpsJump(args.server, "v")
                else:
                    vpsDirectJump(args.server, "v")
        return True
    else:
        return False

def dediHandler(args):
    if(isDedi(args.server)):
        if(not authUser and not authPW):
            print("[!] Invalid operation")
            print("\t[!] No cpJump credentials configured\n")
        else:
            if(args.noKey):
                dediKeylessJump(args.server,args.port)
            else:
                dediJump(args.server, args.port)
        return True
    else:
        return False

def sharedHandler(args):
    if(isShared(args.server)):
        if(not jsUser):
            print("[INVLAID]")
            print("\t[!] No jumpstation credentials configured")
        else:
            sharedJump(args.server, args.jumpstation)
        return True
    else:
        return False

def main(args):
    bounceHandler(args)
    if(args.gotoNode):
        print("\n\n[ACCESSING] Node")
    else:
        print("\n\n[ACCESSING] " + args.server + ":" + args.port)
    VPSSuccess = VPSHandler(args)
    DediSuccess = dediHandler(args)
    SharedSuccess = sharedHandler(args)
    if(not VPSSuccess and not DediSuccess and not SharedSuccess):
        print("[INVALID] Server name\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSH connection automation for shared, VPS, and dedicated servers")
    parser.add_argument("server")
    parser.add_argument('port', nargs='?', default='22')
    parser.add_argument("-n", "--node", help="Connect to the VPS node housing the container", action="store_true", dest='gotoNode', default=False)
    parser.add_argument("-k", "--keyless", help="Connect to a dedicated server without generating a new root key", action="store_true", dest='noKey', default=False)
    parser.add_argument("-b", "--bounce", help="Run a ping test, and then initate a connection once the server starts responding", action="store_true", dest='bounce', default=False)
    parser.add_argument("-j", "--jumpstation", help="Backup method to connect to a VPS, node, or shared server through jumpstation, should a direct method fail", action="store_true", dest='jumpstation', default=False)
    args = parser.parse_args()
    main(args)
