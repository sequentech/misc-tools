#!/usr/bin/env python3

# This file is part of misc-tools.
# Copyright (C) 2014-2016  Sequent Tech Inc <legal@sequentech.io>

# misc-tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# misc-tools  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with misc-tools.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import os
import json
import copy
import requests
from datetime import datetime
from importlib import import_module
from requests.auth import HTTPBasicAuth

ADMIN_CONFIG = None
KHMAC = None
PLUGINS = []

def load_plugins():
    files = os.listdir(os.path.dirname(__file__))
    for f in files:
        if f.startswith('plugin_'):
            PLUGINS.append(f.split('.')[0])

def loadJson(filename):
    '''Load json file'''
    f = open(filename, 'r', encoding="utf-8", errors='strict')
    data = json.load(f)
    f.close()
    return data

def request_get(url, *args, **kwargs):
    print("GET %s" % url)
    kwargs['verify'] = False
    req = requests.get(url, *args, **kwargs)
    print(req.status_code, req.text)
    return req

def request_post(url, *args, **kwargs):
    print("POST %s" % url)
    kwargs['verify'] = False
    req = requests.post(url, *args, **kwargs)
    print(req.status_code, req.text)
    return req

def request_delete(url, *args, **kwargs):
    print("DELETE %s" % url)
    kwargs['verify'] = False
    req = requests.delete(url, *args, **kwargs)
    print(req.status_code, req.text)
    return req

def login():
    """ Login and return the neccesary headers """
    global headers
    base_url = ADMIN_CONFIG['iam']['url']
    event_id = ADMIN_CONFIG['iam']['event-id']
    credentials = copy.deepcopy(ADMIN_CONFIG['iam']['credentials'])
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
    base_url = ADMIN_CONFIG['iam']['url']
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
    base_url = ADMIN_CONFIG['iam']['url']
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
    base_url = ADMIN_CONFIG['iam']['url']
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
    base_url = ADMIN_CONFIG['iam']['url']
    req = request_post(base_url + 'auth-event/%d/%s/' % (aeid, status),
            headers=headers)
    if req.status_code == 200:
        return True
    else:
        return False

def send_auth_codes(aeid, subject=None, msg=None):
    '''
    Sends auth codes to the census
    '''
    print("S", subject, msg)
    global headers
    base_url = ADMIN_CONFIG['iam']['url']
    payload = {}
    if subject:
        payload['subject'] = subject
    if msg:
        payload['msg'] = msg
    req = request_post(base_url + 'auth-event/%d/census/send_auth/' % aeid,
            headers=headers, data=json.dumps(payload))

def createElection(config, aeid):
    '''
    Create election on ballot-box
    '''
    global KHMAC
    base_url = ADMIN_CONFIG['ballot_box_base_url']
    headers = {'content-type': 'application/json', 'Authorization': KHMAC}
    url = '%selection/%d' % (base_url, aeid)
    # register
    r = request_post(url, data=json.dumps(config), headers=headers)
    if r.status_code != 200:
        exit(1)
    # create
    electionCommand(aeid, "create")


def electionCommand(aeid, command, method="POST", data=None):
    global KHMAC
    base_url = ADMIN_CONFIG['ballot_box_base_url']
    headers = {'content-type': 'application/json', 'Authorization': KHMAC}
    url = '%selection/%d/%s' % (base_url, aeid, command)
    method = request_post if method == "POST" else request_get
    data = data or {}
    r = method(url, data=json.dumps(data), headers=headers)
    if r.status_code != 200:
        exit(1)
    return r

if __name__ == "__main__":
    load_plugins()

    def check_positive_id(value):
        ivalue = int(value)
        if ivalue < 0:
             raise argparse.ArgumentTypeError("%s is an invalid positive id value" % value)
        return ivalue

    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--create",
            help="path to the dir containing json configuration.")
    parser.add_argument("-C", "--config", required=True,
            help="path to the sequent-admin configuration file.")
    parser.add_argument("--start", type=check_positive_id,
            help="id authevent for start")
    parser.add_argument("--stop", type=check_positive_id,
            help="id authevent for stop")
    parser.add_argument("--tally", type=check_positive_id,
            help="election id to tally")
    parser.add_argument("--calculate", type=check_positive_id,
            help="election id to calculate")
    parser.add_argument("--results", type=check_positive_id,
            help="election id to get")
    parser.add_argument("--publish", type=check_positive_id,
            help="election id to publish")
    parser.add_argument("--voters", type=check_positive_id,
            help="shows the election voters")
    parser.add_argument("--send-auth-codes", type=check_positive_id,
            help="id authevent for sending auth codes")
    parser.add_argument("--subject", help="subject used for send-auth-codes")
    parser.add_argument("-m", "--msg", help="message used for send-auth-codes")

    for plugin in PLUGINS:
        mod = import_module(plugin)
        for add_arg in mod.add_arguments:
            parser.add_argument(add_arg[0], **add_arg[1])

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

            # modify email title
            json_config['auth_method'] = ADMIN_CONFIG['iam']['event_config']['auth_method']
            json_config['auth_method_config'] = copy.deepcopy(ADMIN_CONFIG['iam']['event_config']['auth_method_config'])
            if "subject" in json_config['auth_method_config']:
                json_config['auth_method_config']['subject'] = json_config['auth_method_config']['subject'] % dict(
                    title=json_ae['title'])

            getperm(obj_type="AuthEvent", perm="create")

            aeid = createAuthevent(json_config)
            print("Created auth-event with id ", aeid)
            if len(json_census) > 0:
                msg = addCensus(aeid, json_census)
                print("Added census.")
            getperm(obj_type="AuthEvent", perm="edit", obj_id=aeid)
            json_ae['id'] = aeid
            createElection(json_ae, aeid)
    elif args.start:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.start)
        statusAuthevent(args.start, 'started')
        electionCommand(args.start, "start")
    elif args.stop:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.stop)
        statusAuthevent(args.stop, 'stopped')
        electionCommand(args.stop, "stop")
    elif args.send_auth_codes:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.send_auth_codes)
        send_auth_codes(args.send_auth_codes, args.subject, args.msg)
    elif args.tally:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.tally)
        electionCommand(args.tally, "tally")
    elif args.calculate:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.calculate)
        data = ADMIN_CONFIG['tally_pipes_config']
        electionCommand(args.calculate, "calculate-results", data=data)
    elif args.results:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.results)
        electionCommand(args.results, "results", method="GET")
    elif args.publish:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.publish)
        electionCommand(args.publish, "publish-results")
    elif args.voters:
        headers = login()
        getperm(obj_type="AuthEvent", perm="edit", obj_id=args.voters)
        r = electionCommand(args.voters, "voters", method="GET").json()
        voters = r['payload']

        headers = login()

        eid = args.voters
        base_url = ADMIN_CONFIG['iam']['url']
        url = '%sauth-event/%s/census/' % (base_url, eid)
        req = request_get(url, data=json.dumps({}), headers=headers)
        if req.status_code != 200:
            exit(1)
        response = req.json()
        census = response['users']

        print("\nVOTERS: ")
        for i in voters:
            print(census[i])
        print("\n")

    else:
        for plugin in PLUGINS:
            mod = import_module(plugin)
            func = mod.check_arguments(args, globals(), locals())
            if func:
                break
        if not func:
            print(args)
