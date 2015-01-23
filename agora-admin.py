#!/usr/bin/env python3

import argparse
import os
import json
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

ADMIN_CONFIG = None
KHMAC = None

def loadJson(filename):
    '''Load json file'''
    f = open(filename, 'r', encoding="utf-8", errors='strict')
    data = json.load(f)
    f.close()
    return data

def request_post(url, *args, **kwargs):
    print("POST %s" % url)
    req = requests.post(url, *args, **kwargs)
    print(req.status_code, req.text)
    return req

def login():
    """ Login and return the neccesary headers """
    global headers
    base_url = ADMIN_CONFIG['authapi']['url']
    event_id = ADMIN_CONFIG['authapi']['event-id']
    credentials = {
        "username": ADMIN_CONFIG['authapi']['username'],
        "password": ADMIN_CONFIG['authapi']['password']
    }
    req = request_post(base_url + 'auth-event/%d/authenticate/' % event_id,
        data=json.dumps(credentials))
    if req.status_code != 200:
        exit(1)
    auth_token = req.json()['auth-token']
    headers={'AUTH': auth_token}
    return headers


def getperm(obj_type, perm, obj_id=None):
    """ Check if the user have permission """
    global headers
    global KHMAC
    base_url = ADMIN_CONFIG['authapi']['url']
    perms = {"object_type": obj_type, "permission": perm}
    if obj_id:
        perms['object_id'] = obj_id
    req = request_post(base_url + 'get-perms/', data=json.dumps(perms), headers=headers)
    if req.status_code != 200 or not req.json()['permission-token']:
        exit(1)
    KHMAC = req.json()['permission-token']
    return True


def createAuthevent(config):
    """
    Create auth-event with the configuration in json format.
    Return the id of created authevent.
    """
    global headers
    base_url = ADMIN_CONFIG['authapi']['url']
    req = request_post(base_url + 'auth-event/', data=json.dumps(config),
        headers=headers)
    if req.status_code != 200:
        exit(1)
    aeid = req.json()['id']
    return aeid


def addCensus(aeid, census):
    """
    Add census to authevent.
    Return ok if added correct or the user errors if added wrong.
    """
    global headers
    base_url = ADMIN_CONFIG['authapi']['url']
    req = request_post(base_url + 'auth-event/%d/census/' % aeid, data=json.dumps(census),
            headers=headers)
    if req.status_code != 200:
        exit()
    msg = req.json()
    return msg


def statusAuthevent(aeid, status):
    """
    Change status of auth-event.
    Return ok if change correct or error if not status changed.
    """
    global headers
    base_url = ADMIN_CONFIG['authapi']['url']
    req = request_post(base_url + 'auth-event/%d/%s/' % (aeid, status),
            headers=headers)
    if req.status_code == 200:
        return True
    else:
        return False

def send_auth_codes():
    '''
    Sends auth codes to the census
    '''
    global headers
    base_url = ADMIN_CONFIG['authapi']['url']
    payload = {
        "message": ADMIN_CONFIG['authapi']['auth_code_message']
    }
    req = request_post(base_url + 'auth-event/%d/census/send_auth/' % aeid,
            headers=headers, data=json.dumps(payload))

def createElection(config, aeid):
    '''
    Create election on agora-elections
    '''
    global KHMAC
    base_url = ADMIN_CONFIG['agora_elections_base_url']
    headers = {'content-type': 'application/json', 'Authorization': KHMAC}
    url = '%selection/%d' % (base_url, aeid)
    r = request_post(url, data=json.dumps(config), headers=headers)
    if r.status_code != 200:
        exit(1)

if __name__ == "__main__":

    def check_positive_id(value):
        ivalue = int(value)
        if ivalue < 0:
             raise argparse.ArgumentTypeError("%s is an invalid positive id value" % value)
        return ivalue

    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--create",
            help="path to the dir containing json configuration.")
    parser.add_argument("-C", "--config", required=True,
            help="path to the agora-admin configuration file.")
    parser.add_argument("--start", type=check_positive_id,
            help="id authevent for start")
    parser.add_argument("--stop", type=check_positive_id,
            help="id authevent for stop")
    parser.add_argument("--send-auth-codes", type=check_positive_id,
            help="id authevent for sending auth codes")

    args = parser.parse_args()

    if not os.access(args.config, os.R_OK):
      print("can't read %s" % args.config)
      exit(1)

    ADMIN_CONFIG = loadJson(args.config)

    if args.create:
        if not os.path.isdir(args.create):
            print("--create must bea a directory")
            exit(1)

        fids = [fname.replace(".census.json", "")
            for fname in os.listdir(args.create)
            if fname.endswith(".census.json")]

        headers = login()
        for fid in fids:
            ae = fid + ".json"
            census = fid + ".census.json"
            config = fid + ".config.json"

            json_ae = loadJson(os.path.join(args.create, ae))
            json_census = loadJson(os.path.join(args.create, census))
            json_config = loadJson(os.path.join(args.create, config))

            getperm(obj_type="AuthEvent", perm="create")
            aeid = createAuthevent(json_config)
            print("Created auth-event with id ", aeid)
            msg = addCensus(aeid, json_census)
            print("Added census.")
            getperm(obj_type="AuthEvent", perm="edit", obj_id=aeid)
            json_ae['id'] = aeid
            createElection(json_ae, aeid)

    elif args.start:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.start)
        statusAuthevent(args.start, 'start')
    elif args.stop:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.stop)
        statusAuthevent(args.stop, 'stop')
    elif args.send_auth_codes:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.send_auth_codes)
        sned_auth_codes(args.send_auth_codes)
    else:
        print(args)
