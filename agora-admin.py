#!/usr/bin/env python3

import argparse
import json
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

AUTH = ({'username': 'admin', 'password': 'admin'}, 0) # auth, event
#AUTH = ({'email': 'test@test.com', 'password': 'test'}, 16)

AUTHAPI = 'http://localhost:8000/api/'
AGORA_ELECTION = 'http://localhost:4000/api/'


def loadJson(filename):
    f = open(filename, 'r')
    data = json.load(f)
    f.close()
    return data


def login(auth):
    """ Login and return the neccesary headers """
    global headers
    req = requests.post(AUTHAPI + 'auth-event/%d/login/' % auth[1], json=auth[0])
    if req.status_code != 200:
        print(req.text)
        exit()
    auth_token = json.loads(req.text)['auth-token']
    headers={'AUTH': auth_token}
    return headers


def getperm(obj_type, perm, obj_id=None):
    """ Check if the user have permission """
    global headers
    perms = {"object_type": obj_type, "permission": perm}
    if obj_id:
        perms['object_id'] = obj_id
    req = requests.post(AUTHAPI + 'get-perms/', json=perms, headers=headers)
    if req.status_code != 200 or not json.loads(req.text)['permission-token']:
        print(req.text)
        exit()
    return True


def createAuthevent(config):
    """
    Create auth-event with the configuration in json format.
    Return the id of created authevent.
    """
    global headers
    req = requests.post(AUTHAPI + 'auth-event/', json=config,
            headers=headers)
    if req.status_code != 200:
        print(req.text)
        exit()
    aeid = json.loads(req.text)['id']
    return aeid


def addCensus(aeid, census):
    """
    Add census to authevent.
    Return ok if added correct or the user errors if added wrong.
    """
    global headers
    req = requests.post(AUTHAPI + 'auth-event/%d/census/' % aeid, json=census,
            headers=headers)
    if req.status_code != 200:
        print(req.text)
        exit()
    msg = json.loads(req.text)
    return msg


def statusAuthevent(aeid, status):
    """
    Change status of auth-event.
    Return ok if change correct or error if not status changed.
    """
    global headers
    req = requests.post(AUTHAPI + 'auth-event/%d/%s/' % (aeid, status),
            headers=headers)
    if req.status_code == 200:
        return True
    else:
        print(req.text)
        return False


if __name__ == "__main__":

    def check_positive_id(value):
        ivalue = int(value)
        if ivalue < 0:
             raise argparse.ArgumentTypeError("%s is an invalid positive id value" % value)
        return ivalue

    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--create",
            help="path to the dir containing config json.")
    parser.add_argument("--start", type=check_positive_id,
            help="id authevent for start")
    parser.add_argument("--stop", type=check_positive_id,
            help="id authevent for stop")

    args = parser.parse_args()

    if args.create:
        ae = args.create + ".json"
        census = args.create + ".census.json"
        config = args.create + ".config.json"

        json_ae = loadJson(ae)
        json_census = loadJson(census)
        json_config = loadJson(config)

        headers = login(AUTH)
        getperm(obj_type="AuthEvent", perm="create")
        aeid = createAuthevent(json_config)
        print("Created auth-event with id ", aeid)
        msg = addCensus(aeid, json_census)
        print("Added census.")

    elif args.start:
        headers = login(AUTH)
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.start)
        statusAuthevent(args.start, 'start')
    elif args.stop:
        headers = login(AUTH)
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.stop)
        statusAuthevent(args.stop, 'stop')
    else:
        print(args)
