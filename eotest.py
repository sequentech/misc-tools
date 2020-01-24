#!/usr/bin/env python3

# This file is part of agora-tools.
# Copyright (C) 2014-2020  Agora Voting SL <contact@nvotes.com>

# agora-tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tools  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tools.  If not, see <http://www.gnu.org/licenses/>.

import requests
import ssl
from requests.adapters import HTTPAdapter
import json
import time
import random

from functools import partial
from base64 import urlsafe_b64encode

from http.server import (
    BaseHTTPRequestHandler, 
    HTTPServer, 
    SimpleHTTPRequestHandler
)
from socketserver import ThreadingMixIn
import threading

import subprocess

import argparse
import sys
import __main__
from argparse import RawTextHelpFormatter

from datetime import datetime
import hashlib
import codecs
import traceback

import os.path
import os

PK_TIMEOUT = 60*10 # with three authorities 60 secons was not enough
TALLY_TIMEOUT = 3600*6 # 6 hours should be enough for what we do :-P
CERT = '/srv/certs/selfsigned/cert.pem'
KEY = '/srv/certs/selfsigned/key-nopass.pem'
CALIST = '/srv/certs/selfsigned/calist'
DATA_DIR = "/srv/eotest/data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

os.chdir(DATA_DIR)

# configuration
localPort = 8000
node = '/usr/bin/node'

class RejectAdapter(HTTPAdapter):
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        raise Exception('Policy set to reject connection to ' + request.url)

def getPeerPkg(mypeerpkg):
    if mypeerpkg is None:
        mypeerpkg = subprocess.check_output(["/usr/bin/eopeers", "--show-mine"])
    if isinstance(mypeerpkg, bytes):
        return json.loads(mypeerpkg.decode("utf-8"))
    else:
        return mypeerpkg

def getTallyData(mypeerpkg):
    mypeerpkg = getPeerPkg(mypeerpkg)
    localServer = mypeerpkg["hostname"]
    return {
        # 'election_id': electionId,
        "callback_url": "https://" + localServer + ":" + str(localPort) + "/receive_tally",
        "votes_url": "https://" + localServer + ":" + str(localPort) + "/",
        "votes_hash": "ni:///sha-256;"
    }


def _apiUrl(path, pkg):
    '''
    Given a full api (without the initial '/') path and a package dict, returns
    a well formed url
    '''
    return "https://%(hostname)s:%(port)d/%(path)s" % dict(
        hostname=pkg["hostname"],
        port=pkg.get("port", 5000),
        path=path
    )

def grabAuthData(eopeers_dir, mypeerpkg, eopeers):
    mypeerpkg = getPeerPkg(mypeerpkg)

    if not os.path.isdir(eopeers_dir):
        print("%s is not a directory" % eopeers_dir)
        exit(1)

    l = os.listdir(eopeers_dir)
    if len(l) == 0:
        print("%s is an empty directory" % eopeers_dir)
        print("one authority")
        #exit(1)

    auths_data = [mypeerpkg]
    for fname in os.listdir(eopeers_dir):
        path = os.path.join(eopeers_dir, fname)
        with open(path, 'r') as f:
            auths_data.append(json.loads(f.read()))

    if eopeers is not None:
        if mypeerpkg['hostname'] not in eopeers:
            eopeers.append(mypeerpkg['hostname'])
        auths_data = [auth for auth in auths_data if auth['hostname'] in eopeers]
        hostnames = [a['hostname'] for a in auths_data]
        if len(hostnames) != len(eopeers):
            not_found = str(list(set(eopeers) - set(hostnames)))
            print("some peers were not found: %s" % not_found)
            exit(1)

    print("\nusing the following authorities:")
    i = 1
    ret_data = []
    for auth in auths_data:
        ret_data.append({
            "name": "Auth%d" %i,
            "orchestra_url": _apiUrl("api/queues", auth),
            "ssl_cert": auth["ssl_certificate"]
        })
        if i == 1:
            print(" 1. %s (this is us, acting as orchestra "
                  "director)" % auth['hostname'])
        else:
            print(" %d. %s" % (i, auth['hostname']))
        i += 1
    print("\n")
    return ret_data

def getStartData(eopeers_dir, mypeerpkg, eopeers):
    mypeerpkg = getPeerPkg(mypeerpkg)
    return {
        "callback_url": "https://" + mypeerpkg["hostname"] + ":" + str(localPort) + "/key_done",
        "title": "Test election",
        "description": "election description",
        'presentation': {},
        "questions": [{
            "title": "Who Should be President?",
            "tally_type": "plurality-at-large",
            "randomize_answer_order": True,
            'num_winners': 1,
            "answer_total_votes_percentage": "over-total-valid-votes",
            'layouy': 'plurality',
            "answers": [
                {
                    'details': '',
                    'text': 'Alice',
                    'id': 0,
                    'category': '',
                    'sort_order': 0,
                    'urls': [],
                },
                {
                  'id': 1,
                  'category': '',
                  'sort_order': 1,
                  'urls': [],
                  'text': 'Bob'
                }
            ],
            "max": 1, "min": 0
        }],
        "start_date": "2013-12-06T18:17:14.457000",
        "end_date": "2013-12-09T18:17:14.457000",
        "authorities": grabAuthData(eopeers_dir, mypeerpkg, eopeers)
    }

# code

# thread signalling
cv = threading.Condition()

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        print("> HTTP GET received " + self.path)
        if(self.path == "/exit"):
            self.send_response(204)
            self.end_headers()
            print("> HTTP GET sent response")
            cv.acquire()
            cv.done = True
            cv.notify()
            cv.release()
        else:
            SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        print("> HTTP POST received " + self.path + " (" + str(length) + ")")
        raw = self.rfile.read(length).decode('utf-8')
        data = json.loads(raw)

        # print(data)
        self.send_response(200)
        self.end_headers()
        print("> HTTP POST sent response")
        cv.acquire()
        cv.done = True
        cv.data = data
        cv.notify()
        cv.release()

# misc\utils.py
BUF_SIZE = 10*1024
def hash_file(file_path):
    '''
    Returns the hexdigest of the hash of the contents of a file, given the file
    path.
    '''
    hash = hashlib.sha256()
    f = open(os.path.join(DATA_DIR, file_path), 'rb')
    for chunk in iter(partial(f.read, BUF_SIZE), b''):
        hash.update(chunk)
    f.close()
    return urlsafe_b64encode(hash.digest()).decode('utf-8')


def writeVotes(votesData, fileName):
    # forms/election.py:save
    votes = []
    for vote in votesData:
        data = {
            "proofs": [],
            "choices": [],
            "issue_date": str(datetime.now())
        }

        q_answer = vote['question0']
        data["proofs"].append(dict(
            commitment=q_answer['commitment'],
            response=q_answer['response'],
            challenge=q_answer['challenge']
        ))
        data["choices"].append(dict(
            alpha=q_answer['alpha'],
            beta=q_answer['beta']
        ))

        votes.append(data)

    # tasks/election.py:launch_encrypted_tally
    with codecs.open(os.path.join(DATA_DIR, fileName), encoding='utf-8', mode='w+') as votes_file:
        for vote in votes:
            # votes_file.write(json.dumps(vote['data'], sort_keys=True) + "\n")
            votes_file.write(json.dumps(vote, sort_keys=True) + "\n")


def startServer(port):
    import ssl
    print("> Starting server on port " + str(port))
    server = ThreadingHTTPServer(('', port), RequestHandler)
    server.socket = ssl.wrap_socket(server.socket, certfile=CERT, keyfile=KEY, server_side=True)
    thread = threading.Thread(target = server.serve_forever, daemon=True)
    thread.start()

def startElection(electionId, url, data):
    session = requests.sessions.Session()
    session.mount('http://', RejectAdapter())
    data['id'] = int(electionId)
    print("> Creating election %s" % electionId)
    cv.done = False
    r = session.request('post', url, data=json.dumps(data), verify=CALIST, cert=(CERT, KEY))
    print("> " + str(r))

def waitForPublicKey():
    start = time.time()
    cv.acquire()
    cv.wait(PK_TIMEOUT)
    pk = ''
    if(cv.done):
        diff = time.time() - start
        try:
            pk = cv.data['session_data'][0]['pubkey']
            print("> Election created " + str(diff) + " sec, public key is")
            print(pk)
        except:
            print("* Could not retrieve public key " + str(cv.data))
            print(traceback.print_exc())
    else:
        print("* Timeout waiting for public key")
    cv.release()

    return pk

def doTally(electionId, url, data, votesFile, hash):
    session = requests.sessions.Session()
    session.mount('http://', RejectAdapter())
    data['votes_url'] = data['votes_url'] + votesFile
    data['votes_hash'] = data['votes_hash'] + hash
    data['election_id'] = int(electionId)
    # print("> Tally post with " + json.dumps(data))
    print("> Requesting tally..")
    cv.done = False
    r = session.request('post', url, data=json.dumps(data), verify=CALIST, cert=(CERT, KEY))
    print("> " + str(r))
    if r.status_code == 400:
        print("> error:" + str(r.text))

def waitForTally():
    start = time.time()
    cv.acquire()
    cv.wait(TALLY_TIMEOUT)
    ret = ''
    if(cv.done):
        diff = time.time() - start
        # print("> Received tally data (" + str(diff) + " sec) " + str(cv.data))
        print("> Received tally data " + str(diff) + " sec")
        if('tally_url' in cv.data['data']):
            ret = cv.data['data']
    else:
        print("* Timeout waiting for tally")
    cv.release()

    return ret

def downloadTally(url, electionId):
    session = requests.sessions.Session()
    session.mount('http://', RejectAdapter())
    fileName = electionId + '.tar.gz'
    path = os.path.join(DATA_DIR, fileName)
    print("> Downloading to %s" % path)
    with open(path, 'wb') as handle:
        request = session.request('get',url, stream=True, verify=CALIST, cert=(CERT, KEY))

        for block in request.iter_content(1024):
            if not block:
                break

            handle.write(block)






''' driving functions '''

def create(args):
    electionId = args.electionId
    startServer(localPort)
    mypeerpkg = getPeerPkg(args.mypeerpkg)
    startData = getStartData(args.eopeers_dir, args.mypeerpkg, args.peers)
    startUrl = _apiUrl("public_api/election", mypeerpkg)
    startElection(electionId, startUrl, startData)
    publicKey = waitForPublicKey()
    pkFile = 'pk' + electionId

    if(len(publicKey) > 0):
        print("> Saving pk to " + pkFile)
        with codecs.open(os.path.join(DATA_DIR, pkFile), encoding='utf-8', mode='w+') as votes_file:
            votes_file.write(json.dumps(publicKey))
    else:
        print("No public key, exiting..")
        exit(1)

    return pkFile

def encrypt(args):
    electionId = args.electionId
    pkFile = 'pk' + electionId
    votesFile = args.vfile
    votesCount = args.vcount
    ctexts = 'ctexts' + electionId
    # encrypting with vmnd
    if(args.vmnd):
        vmnd = "/usr/bin/vmnd.sh"
        vmndFile = os.path.join(DATA_DIR, "vmndCtexts" + electionId)
        if(votesCount == 0):
            votesCount = 10
        subprocess.call([vmnd, electionId, str(votesCount), vmndFile])
        if (os.path.isfile(vmndFile)):
            with open(vmndFile, 'r') as content_file:
                lines = content_file.readlines()
            votes = []

            for line in lines:
                fields = {}
                lineJson = json.loads(line)
                lineJson["commitment"] = "foo"
                lineJson["response"] = "foo"
                lineJson["challenge"] = "foo"
                fields["question0"] = lineJson
                votes.append(fields)

            writeVotes(votes, ctexts)

        else:
            print("Could not read vmnd votes file " + vmndFile)
            exit(1)
    else:
        print("> Encrypting votes (" + votesFile + ", pk = " + pkFile + ", " + str(votesCount) + ")..")
        pkPath = os.path.join(DATA_DIR, pkFile)
        votesPath = os.path.join(DATA_DIR, votesFile)
        # if not present in data dir, use current directory
        if not (os.path.isfile(votesPath)):
            votesPath = votesFile
        if(os.path.isfile(pkPath)) and (os.path.isfile(votesPath)):
            output, error = subprocess.Popen([node, "encrypt.js", pkPath, votesPath, str(votesCount)], stdout = subprocess.PIPE).communicate()

            print("> Received Nodejs output (" + str(len(output)) + " chars)")
            parsed = json.loads(output)


            print("> Writing file to " + ctexts)
            writeVotes(parsed, ctexts)
        else:
            print("No public key or votes file, exiting..")
            exit(1)

def tally(args):
    if(args.command[0] == "tally"):
        startServer(localPort)

    electionId = args.electionId

    ctexts = 'ctexts' + electionId
    # need hash
    hash = hash_file(ctexts)
    print("> Votes hash is " + hash)
    tallyData = getTallyData(args.mypeerpkg)
    mypeerpkg = getPeerPkg(args.mypeerpkg)
    tallyUrl = _apiUrl('public_api/tally', mypeerpkg)
    doTally(electionId, tallyUrl, tallyData, ctexts, hash)
    tallyResponse = waitForTally()

    if('tally_url' in tallyResponse):
        print("> Downloading tally from " + tallyResponse['tally_url'])
        downloadTally(tallyResponse['tally_url'], electionId)
    else:
        print("* Tally not found in http data")

def full(args):
    electionId = args.electionId

    pkFile = create(args)

    if(os.path.isfile(os.path.join(DATA_DIR, pkFile))):
        encrypt(args)
        tally(args)
    else:
        print("No public key, exiting..")

def main(argv):
    if not (os.path.isdir(DATA_DIR)):
        print("> Creating data directory")
        os.makedirs(DATA_DIR)
    parser = argparse.ArgumentParser(description='EO testing script', formatter_class=RawTextHelpFormatter)
    parser.add_argument('command', nargs='+', default='full', help='''create: creates an election
encrypt <electionId>: encrypts votes
tally <electionId>: launches tally
full: does the whole process''')
    parser.add_argument('--eopeers-dir', help='directory with the eopeers packages to use as authorities', default = '/etc/eopeers/')
    parser.add_argument('--peers', nargs='+', default=None, help='list of authorities to pair with. defaults to all of them')
    parser.add_argument('--mypeerpkg', help='path to my peer package. if empty, calls to eopeers --show-mine', default = None)
    parser.add_argument('--vfile', help='json file to read votes from', default = 'votes.json')
    parser.add_argument('--vcount', help='number of votes to generate (generates duplicates if more than in json file)', type=int, default = 0)
    parser.add_argument('--vmnd', action='store_true', help='encrypts with vmnd')
    args = parser.parse_args()
    command = args.command[0]
    if hasattr(__main__, command):
        if(command == 'create') or (command == 'full'):
            args.electionId = str(random.randint(100, 10000))
        elif(len(args.command) == 2):
            args.electionId = args.command[1]
        else:
            parser.print_help()
            exit(1)
        eval(command + "(args)")
    else:
        parser.print_help()

if __name__ == "__main__":
    main(sys.argv[1:])
