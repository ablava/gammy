#!/usr/bin/env python

"""
Simple script to manage Google users 
via GAM tool. A properly installed and
configured GAM (https://github.com/jay0lee/GAM)
is required for operation. You will need to adjust
the script to your GA stu/acad/admin org structure
(search for .university.edu in the code).

Usage: 
    python gammy -f input.json -o output.csv

Options:
    -h --help
    -f --file	Input file (required)
    -o --out	Output file (required)

Environment specific script constants are stored in this 
config file: gammy_settings.py
    
Input:

Input file is expected to be in JSON format (e.g. input.json).
with these 10 required data fields:
{
    "useractions": [
        {
            "action": "create",
            "username": "testuserj",
            "newusername": "testuserj",
            "loginDisabled": "False",
            "UDCid": 1554943643675475475437,
            "givenName": "John",
            "fullName": "John The Testuser",
            "sn": "Testuser",
            "primO": "Biology",
            "userPassword": "initial password"
        }
    ] 
}
where action can be create/update/delete and newusername is same old one 
or a new value if renaming the user.

Output:

Output file (e.g. output.csv) will have these fields:

action, username, result (ERROR/SUCCESS: reason)

Logging:

Script creates a detailed gammy.log

All errors are also printed to stdout.

Author: C. Reitsma
With help from: A. Ablovatski
Based on the o365.py script by: A. Ablovatski
Email: ablovatskia@denison.edu
Date: 02/22/2017
"""

from __future__ import print_function
import time
import sys
import traceback
import json
import csv
import argparse
import logging
import httplib
import urllib
import hashlib
from io import TextIOWrapper, BytesIO
sys.path.append('/usr/local/gam')
from gam import *

def main(argv):
    """This is the main body of the script"""

    # Setup the log file
    logging.basicConfig(
        filename='gammy.log',level=logging.DEBUG, 
        format='%(asctime)s, %(levelname)s: %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S')

    # Get constants from this settings file
    config_file = 'gammy_settings.py'
    
    if not readConfig(config_file):
        logging.error("unable to parse the settings file")
        sys.exit()
    
    # Parse script arguments
    parser = argparse.ArgumentParser()                                               

    parser.add_argument("--file", "-f", type=str, required=True, 
                        help="Input JSON file with user actions and params")
    parser.add_argument("--out", "-o", type=str, required=True, 
                        help="Output file with results of GApps user actions")

    try:
        args = parser.parse_args()
        
    except SystemExit:
        logging.error("required arguments missing - " \
                        "provide input and output file names")
        sys.exit()

    # Read input from json file
    in_file = args.file
    # Write output to csv file
    out_file = args.out
    
    try:
        f_in = open(in_file, 'rb')
        logging.info("opened input file: {}".format(in_file))
        f_out = open(out_file, 'wb')
        logging.info("opened output file: {}".format(out_file))
        reader = json.load(f_in)
        writer = csv.writer(f_out)
        writer.writerow(['action','username','result'])

        for row in reader["useractions"]:
            result = ''
            # Select what needs to be done
            if row["action"] == 'create':
                result = create(str(row["username"]), 
                                str(row["givenName"]), 
                                str(row["sn"]), 
                                str(row["primO"]), str(row["userPassword"]))
            elif row["action"] == 'update':
                result = update(str(row["username"]), str(row["newusername"]), 
                                str(row["loginDisabled"]), 
                                str(row["givenName"]), str(row["fullName"]), 
                                str(row["sn"]), str(row["primO"]))
            elif row["action"] == 'delete':
                result = delete(str(row["username"]))
            else:
                print("ERROR: unrecognized action: {}".format(row["action"]))
                logging.error("unrecognized action: {}".format(row["action"]))
                result = "ERROR: Unrecognized action."
            
            # Write the result to the output csv file
            writer.writerow([row["action"], row["username"], result])
            
    except IOError:
        print("ERROR: Unable to open input/output file!")
        logging.critical("file not found: {} or {}".format(in_file, out_file))
        
    except Exception as e:
        traceb = sys.exc_info()[-1]
        stk = traceback.extract_tb(traceb, 1)
        fname = stk[0][3]
        print("ERROR: unknown error while processing line '{}': " \
                "{}".format(fname,e))
        logging.critical("unknown error while processing line '{}': " \
                "{}".format(fname,e))
        
    finally:
        f_in.close()
        logging.info("closed input file: {}".format(in_file))
        f_out.close()
        logging.info("closed output file: {}".format(out_file))
        
    return


def create(username, givenName, sn, ou, userPassword):
    """This function adds users to GApps
       Assume "unsuspend" if action=create and SUSPENDED=True"""
       
    # Check if any of the parameters are missing
    params = locals()
    
    for _item in params:
        if str(params[_item]) == "":
            print("ERROR: unable to create user {} because {} is missing " \
                    "a value".format(username, _item))
            logging.error("unable to create user {} because {} is missing " \
                            "a value".format(username, _item))
            result = "ERROR: Missing an expected input value for " + _item \
                        + " in input file."
            return result

    # Do a quick check if the user already exists
    if findUser(username):
        print("ERROR: cannot create user - user already exists: {}" \
                .format(username))
        logging.error("cannot create user - user already exists: {}" \
                .format(username))
        result = "ERROR: username already taken!"
        
        if SUSPENDED:
            # If user exists and suspended - unsuspend
            command = ["gam","update","user",username,"suspended","off"]
            
            if getUserType(username) == 'STU':
                command.extend(["org","/students.denison.edu"])
            else:
                org = "/" + lookupDivision(ou)
                command.extend(["org",org])
            
            unsuspendresult = GAM(command)
            
            if unsuspendresult:
                print('command: ',' '.join(command))
                print("ERROR: Could not unsuspend user {} in GApps: {}" \
                            .format(username,GERR))
                logging.error("GApps unsuspend failed for user: {}: {}" \
                            .format(username,GERR))
                result = "ERROR: could not unsuspend GApps user."
            else:
                print("SUCCESS: user {} unsuspended in GApps".format(username))
                logging.info("user {} unsuspended in GApps".format(username))
                result = "SUCCES: User unsuspended in GApps."
                
        return result

    # User does not exists - create
    try:
        # Create password hash
        h = hashlib.sha1()
        h.update(userPassword)
        hhex = h.hexdigest()
        
        # Build GAM command and pass it to GAM
        command = ["gam","create","user",username,"firstname",
                    givenName,"lastname",sn,"password",hhex,"sha"]
        
        if getUserType(username) == 'STU':
            command.extend(["org","/students.university.edu"])
        else:
            org = "/" + lookupDivision(ou)
            command.extend(["org",org])
            
        result = GAM(command)

    except Exception as e:
        print('command: ',' '.join(command))
        print("ERROR: Could not add user {} to GApps: {}".format(username,e))
        logging.error("GApps add failed for user: {}: {}" \
                            .format(username,e))
        result = "ERROR: could not create GApps user."
        return result

    if result:
        print('command: ',' '.join(command))
        print("ERROR: Could not add user {} to GApps: {}" \
                            .format(username,GERR))
        logging.error("GApps add failed for user: {}: {}" \
                            .format(username,GERR))
        result = "ERROR: could not create GApps user."
        return result
        
    else:
        print("SUCCESS: user {} added to GApps".format(username))
        logging.info("user {} added to GApps".format(username))
        result = "SUCCESS: User added to GApps."
        
        # Wait 10s for user to be fully created
        # and enable IMAP
        sys.stdout.flush()
        time.sleep(10)
        # Enbale IMAP
        enableImap(username)
        
        return result


def update(username, newusername, loginDisabled, givenName, fullName, sn, ou):
    """This function
          renames users if username != newusername
          sets the user organization
          suspends users if loginDisable == "True" """
    
    # Check if any of the arguments are missing
    params = locals()
    
    for _item in params:
        if str(params[_item]) == "":
            print("ERROR: unable to update user {} because {} is missing " \
                    "a value".format(username, _item))
            logging.error("unable to update user {} because {} is missing " \
                            "a value".format(username, _item))
            result = "ERROR: Missing an expected input value for " \
                        + _item + " in input file."
            return result

    # Do a quick check if the user already exists
    if not findUser(username):
        print("user does not exist in GApps: {}".format(username))
        logging.info("user does not exist in GApps: {}".format(username))
        result = "ERROR: user could not be found in GApps!"
        return result
    
    try:
        # Build GAM command and pass it to GAM
        command = ["gam","update","user",username]
        
        if username != newusername:
            command.extend(["firstname",givenName,"lastname",
                            sn,"username",newusername])
        if loginDisabled == "True":
            command.extend(["suspended","on"])
        if getUserType(username) == 'STU':
            command.extend(["org","/students.university.edu"])
        else:
            org = "/" + lookupDivision(ou)
            command.extend(["org",org])

        result = GAM(command)

    except Exception as e:
        print('command: ',' '.join(command))
        print("ERROR: unknown error while updating GApps user {}: {}" \
                        .format(username,e))
        logging.error("unknown error while updating GApps user {}: {}" \
                        .format(username,e))
        result = "ERROR: Could not update GApps user."
        return result

    if result:
        print('command: ',' '.join(command))
        print("ERROR: Could not update user {} from GApps: {}" \
                        .format(username,GERR))
        logging.error("GApps update failed for user: {}: {}" \
                        .format(username,GERR))
        result = "ERROR: could not update GApps user."
        return result
    else:
        print("SUCCESS: user {} updated in GApps".format(username))
        logging.info("user {} updated in GApps".format(username))
        result = "SUCCESS: User updated in GApps."
        return result


def delete(username):
    """This function deletes a user"""

    # Check if the argument is missing
    if str(username) == "":
        print("ERROR: unable to delete user because username argument " \
                "is missing a value")
        logging.error("unable to delete user because username argument " \
                        "is missing a value")
        result = "ERROR: Missing an expected input value for username " \
                    "in input file."
        return result

    if not findUser(username):
        print("user does not exist in GApps: {}".format(username))
        logging.info("user does not exist in GApps: {}".format(username))
        result = "ERROR: user not found in GApps!"
        return result
        
    try:
        # Build GAM command and pass it to GAM
        command = ["gam","delete","user",username]
        
        result = GAM(command)

    except Exception as e:
        print('command: ',' '.join(command))
        print("ERROR: unknown error while deleting GApps user: {}".format(e))
        logging.error("unknown error while deleting GApps user {}: {}" \
                        .format(username,e))
        result = "ERROR: Could not delete GApps user."
        return result
    
    if result:
        print('command: ',' '.join(command))
        print("ERROR: Could not delete user {} from GApps: {}" \
                        .format(username,GERR))
        logging.error("GApps delete failed for user: {}: {}" \
                        .format(username,GERR))
        result = "ERROR: could not delete GApps user."
        return result
    else:
        print("SUCCESS: user {} deleted from GApps".format(username))
        logging.info("user {} deleted from GApps".format(username))
        result = "SUCCESS: User deleted from GApps."
        return result


def readConfig(config_file):
    """Function to import the config file"""
    
    if config_file[-3:] == ".py":
        config_file = config_file[:-3]
    gammysettings = __import__(config_file, globals(), locals(), [])
    
    # Read settings and set globals
    try: 
        global GSUITEDOMAIN
        global STUPATTERN

        GSUITEDOMAIN = gammysettings.GSUITEDOMAIN
        STUPATTERN = gammysettings.STUPATTERN

        global GERR
        global GOUT
        GERR = "standard error"
        GOUT = "standard output"

    # Create primOU-> GA org translation dictionary
        global deptDivision
        deptDivision = {}
        deptDivision['Admissions'] = 'admin.university.edu'
        deptDivision['Art'] = 'academic.university.edu'
        deptDivision['Cinema'] = 'academic.university.edu'
        deptDivision['Grounds And Roads'] = 'admin.universityn.edu'
        deptDivision['Theatre'] = 'academic.university.edu'
        deptDivision['Womens and Gender Studies'] = 'academic.university.edu'
        
    except Exception as e:
        logging.error("unable to parse GApps settings file")
        print("ERROR: unable to parse the GApps settings file: {}".format(e))
        return False
        
    return True


def getUserType(username):
    """ Function to determine the type of a user"""

    if STUPATTERN in username:
        userType = "STU"
    else:
        userType = "EMP"

    return userType


def findUser(username):
    """Do a quick check if the user already exists"""
    
    global SUSPENDED
    SUSPENDED = False
    
    command = ["gam","info","user",username]
    result = GAM(command)
#    print("findUser err: {}".format(GERR))
#    print("findUser out: {}".format(GOUT))
    if result:
        print("No user {} in GApps - {}".format(username,result))
        logging.info("No user {} in GApps: {}".format(username,result))
        return False
    else:
        for item in GOUT.split("\n"):
            if "Suspended" in item:
                if "False" in item:
                    SUSPENDED = False
                if "True" in item:
                    SUSPENDED = True

        print("user {} found in GApps - {}".format(username,result))
        logging.info("found user {} in GApps: {}".format(username,result))
        return True


def GAM(command):
    """redirect stderr,stdout 
    while processing gam commands 
    to global variables: GERR,GOUT """
    
    global GERR
    global GOUT
    
    current_stderr = sys.stderr
    current_stdout = sys.stdout
    fake_stderr = StringIO.StringIO()
    fake_stdout = StringIO.StringIO()
    
    try:
        sys.stderr = fake_stderr
        sys.stdout = fake_stdout
        result = ProcessGAMCommand(command)

    finally:
        sys.stderr = current_stderr
        sys.stdout = current_stdout
        GERR = fake_stderr.getvalue().strip() # read output
        GOUT = fake_stdout.getvalue().strip() # read output
        fake_stderr.close()
        fake_stdout.close()
#        print("GAM err: {}".format(GERR))
#        print("GAM out: {}".format(GOUT))

#    print("GAM res: {}\n command: {}".format(result,' '.join(command)))
    return result

    
def lookupDivision(ou):
    """ This function looks up
    division based on HR-provided ou"""

    # Lookup the division by ou
    division = deptDivision.get(ou, '')

    return division


def enableImap(username):
    """This function enables IMAP"""

    # Do a quick check if the user already exists
    if not findUser(username):
        print("user does not exist in GApps - can't enable IMAP: {}" \
                    .format(username))
        logging.info("user does not exist in GApps - can't enable IMAP: {}" \
                    .format(username))
        return

    try:
        # Build GAM command and pass it to GAM
        command = ["gam","user",username,"imap","on"]
        
        result = GAM(command)

    except Exception as e:
        print('command: ',' '.join(command))
        print("ERROR: unknown error while enabling IMAP on user {}: {}" \
                        .format(username,e))
        logging.error("unknown error while enabling IMAP on user {}: {}" \
                        .format(username,e))
        return

    if result:
        print('command: ',' '.join(command))
        print("ERROR: Could not enable IMAP user {}: {}".format(username,GERR))
        logging.error("Enable IMAP failed for user: {}: {}" \
                        .format(username,GERR))
        return
        
    else:
        print("SUCCESS: user {} has IMAP enabled".format(username))
        logging.info("user {} has IMAP enabled".format(username))
        return
        
        
if __name__ == "__main__":
    main(sys.argv)
