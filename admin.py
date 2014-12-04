#!/usr/bin/env python

import requests
import json
import time
import re

import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
import SocketServer
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
from prettytable import PrettyTable

from sqlalchemy import create_engine, select, func, text
from sqlalchemy import Table, Column, Integer, String, TIMESTAMP, MetaData, ForeignKey

PK_TIMEOUT = 60*10 # with three authorities 60 secons was not enough
TALLY_TIMEOUT = 3600*6 # 6 hours should be enough for what we do :-P
CERT = '/srv/certs/selfsigned/cert.pem'
KEY = '/srv/certs/selfsigned/key-nopass.pem'
ELECTIONS_DIR = 'elections'
node = '/usr/local/bin/node'

def get_local_hostport():
    me = subprocess.check_output(["./eopeers", "--show-mine"])
    pkg = json.loads(me)

    return pkg['hostname'], pkg['port']

def get_backend_config():
    path = os.path.join('..', 'config.json')
    with open(path, 'r') as f:
        config = json.loads(f.read())

    dbConnection = config['DbConnectString']
    def get_pair(l):
      if len(l[2]) > 0:
        return (l[0], l[2])
      elif len(l[1]) > 0:
        return (l[0], l[1])
      else:
        return (l[0], l[3])
    dbParams = dict([get_pair(l) for l in re.findall(r'(\S+)=(\'(.*)\'|"(.*)"|(\S+))', dbConnection)])
    config['db'] = dbParams

    return config

def votes_table():
    metadata = MetaData()
    votes = Table('votes', metadata,
        Column('id', Integer, primary_key=True),
        Column('vote', String),
        Column('vote_hash', String),
        Column('election_id', String),
        Column('voter_id', String),
        Column('ip', String),
        Column('created', TIMESTAMP),
        Column('modified', TIMESTAMP),
        Column('write_count', Integer)
    )
    return votes

def show_votes(result):
    def truncate(data):
        data = str(data)
        return (data[:20] + '..') if len(data) > 20 else data

    v = PrettyTable(['id', 'vote', 'vote_hash', 'election_id', 'voter_id', 'ip', 'created', 'modified', 'writes'])
    v.padding_width = 1
    for row in result:
        v.add_row(map(truncate, row))
    print v

def get_db_connection(dbCfg):
    engine = create_engine('postgresql+psycopg2://%s:%s@localhost/%s' % (dbCfg['user'], dbCfg['password'], dbCfg['dbname']))
    conn = engine.connect()

    return conn

def get_election_config(dir, eopeers_dir, force=False):
    path = os.path.join(ELECTIONS_DIR, dir)

    if not os.path.isdir(path):
        print("%s is not a directory" % path)
        exit(1)

    jsonPath = os.path.join(path, "config.json")
    if not os.path.isfile(jsonPath):
        print("%s is not a file" % jsonPath)
        exit(1)
    print("> loading config in %s" % jsonPath)
    with open(jsonPath, 'r') as f:
        config = json.loads(f.read())

    if not 'director' in config:
        print("director not found in config")
        exit(1)
    if not 'authorities' in config:
        print("authorities not found in config")
        exit(1)

    config['path'] = path
    config["authorities"] = config['authorities'].replace(' ','').split(',')

    # if id not present, use directory name
    if not 'election-id' in config:
        config['election-id'] = os.path.basename(os.path.normpath(dir))

    # authorities and director
    authorities = []
    try:
        auths_data = get_authdata(eopeers_dir, force)

        for auth in auths_data:
            if auth['hostname'] == config['director']:
                authorities.insert(0, auth)
            elif auth['hostname'] in config['authorities']:

                authorities.append(auth)

        # check that all requested authorities were found
        required = list(config['authorities'])
        required.append(config['director'])
        required = set(required)

        found = [a['hostname'] for a in authorities]
        if len(found) != len(required):
            not_found = str(required - set(found))
            print("some peers were not found: %s" % not_found)
            exit(1)

        config['auths'] = authorities

        # local host, port
        localHostname, localPort = get_local_hostport()
        config['local-hostname'] = localHostname
        config['local-port'] = localPort
    except:
        if force:
            print("get auth data failed. Forcing to continue")
        else:
            exit(1)

    return config

def get_tally_data(config):
    return {
        "election_id": config['election-id'],
        "callback_url": "http://" + config['local-hostname'] + ":" + str(config['local-port']) + "/receive_tally",
        "extra": [],
        "votes_url": "http://" + config['local-hostname'] + ":" + str(config['local-port']) + "/",
        "votes_hash": "sha512://"
    }


def _api_url(path, auth):
    '''
    Given a full api (without the initial '/') path and a package dict, returns
    a well formed url
    '''
    return "https://%(hostname)s:%(port)d/%(path)s" % dict(
        hostname=auth["hostname"],
        port=auth.get("port", 5000),
        path=path
    )

def get_authdata_for_post(config):
    i = 1
    ret_data = []
    print("\nusing the following authorities:")
    for auth in config['auths']:
        ret_data.append({
            "name": "Auth%d" %i,
            "orchestra_url": _api_url("api/queues", auth),
            "ssl_cert": auth["ssl_certificate"]
        })
        if i == 1:
            print(" 1. %s (this is the orchestra "
                  "director)" % auth['hostname'])
        else:
            print(" %d. %s" % (i, auth['hostname']))

        i += 1

    return ret_data

def get_authdata(eopeers_dir, force=False):
    if not os.path.isdir(eopeers_dir):
        print("%s is not a directory" % eopeers_dir)
        exit(1)

    l = os.listdir(eopeers_dir)
    if len(l) == 0:
        print("%s is an empty directory" % eopeers_dir)
        if not force:
            exit(1)

    auths_data = []
    for fname in os.listdir(eopeers_dir):
        path = os.path.join(eopeers_dir, fname)
        with open(path, 'r') as f:
            auths_data.append(json.loads(f.read()))

    return auths_data

def getStartData(config):
    return {
        "election_id": config['election-id'],
        "callback_url": "http://" + config['local-hostname'] + ":" + str(config['local-port']) + "/key_done",
        "is_recurring": config['is_recurring'],
        "extra": config['extra'],
        "title": config['title'],
        "url": config['url'],
        "description": config['description'],
        "questions_data": config['questions_data'],
        "voting_start_date": config['voting_start_date'],
        "voting_end_date": config['voting_end_date'],
        "authorities": get_authdata_for_post(config)
    }

# thread signalling
cv = threading.Condition()

class ThreadingHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        print("> HTTP received " + self.path)
        if(self.path == "/exit"):
            self.send_response(204)
            cv.acquire()
            cv.done = True
            cv.notify()
            cv.release()
        else:
            SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        print("> HTTP received " + self.path + " (" + str(length) + ")")
        raw = self.rfile.read(length).decode('utf-8')
        print(raw)
        data = json.loads(raw)

        self.send_response(200)
        cv.acquire()
        cv.done = True
        cv.data = data
        cv.notify()
        cv.release()

# misc\utils.py
BUF_SIZE = 10*1024
def hash_file(filePath):
    '''
    Returns the hexdigest of the hash of the contents of a file, given the file
    path.
    '''
    hash = hashlib.sha512()
    f = open(filePath, 'r')
    for chunk in f.read(BUF_SIZE):
        hash.update(chunk)
    f.close()
    return hash.hexdigest()

def write_node_votes(votesData, filePath):
    # forms/election.py:save
    votes = []
    for vote in votesData:
        data = {
            "a": "encrypted-vote-v1",
            "proofs": [],
            "choices": [],
            "voter_username": 'foo',
            "issue_date": str(datetime.now()),
            "election_hash": {"a": "hash/sha256/value", "value": "foobar"},
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
    # this is the format expected by eo, newline separated
    with codecs.open(filePath, encoding='utf-8', mode='w+') as votes_file:
        for vote in votes:
            votes_file.write(json.dumps(vote, sort_keys=True) + "\n")


def start_server(port):
    print("> Starting server on port %s" % str(port))
    server = ThreadingHTTPServer(('localhost', port),RequestHandler)
    thread = threading.Thread(target = server.serve_forever)
    thread.daemon = True
    thread.start()

def start_election(config, url, data):
    # data['election_id'] = electionId
    print("> Creating election " + config['election-id'])
    print(json.dumps(data))
    cv.done = False
    r = requests.post(url, data=json.dumps(data), verify=False, cert=(CERT, KEY))
    print("> " + str(r))

def wait_for_publicKey():
    start = time.time()
    cv.acquire()
    cv.wait(PK_TIMEOUT)
    pk = ''
    if(cv.done):
        diff = time.time() - start
        try:
            pk = [p['pubkey'] for p in cv.data['session_data']]
            print("> Election created (" + str(diff) + " sec), public key is")
            print(pk)
        except:
            print("* Could not retrieve public key " + str(cv.data))
            print traceback.print_exc()
    else:
        print("* Timeout waiting for public key")
    cv.release()

    return pk

def do_tally(config, url, data, votesFile, hash):
    data['votes_url'] = data['votes_url'] + config['path'] + "/" + votesFile
    data['votes_hash'] = data['votes_hash'] + hash
    # data['election_id'] = config['election-id']
    # print("> Tally post with " + json.dumps(data))
    print("> Requesting tally..")
    cv.done = False
    r = requests.post(url, data=json.dumps(data), verify=False, cert=(CERT, KEY))
    print("> " + str(r))

def wait_for_tally():
    start = time.time()
    cv.acquire()
    cv.wait(TALLY_TIMEOUT)
    ret = ''
    if(cv.done):
        diff = time.time() - start
        # print("> Received tally data (" + str(diff) + " sec) " + str(cv.data))
        print("> Received tally data (" + str(diff) + " sec)")
        if('tally_url' in cv.data['data']):
            ret = cv.data['data']
    else:
        print("* Timeout waiting for tally")
    cv.release()

    return ret

def download_tally(cfg, url, partial):
    tally_file = cfg['tally-file']
    if partial > 0:
      tally_file = tally_file + "." + str(partial)
    path = os.path.join(cfg['electionCfg']['path'], tally_file)
    print("> Downloading to %s" % path)
    with open(path, 'wb') as handle:
        request = requests.get(url, stream=True, verify=False, cert=(CERT, KEY))

        for block in request.iter_content(1024):
            if not block:
                break

            handle.write(block)




''' commands '''

def create(cfg, args):
    config = cfg['electionCfg']
    electionId = config['election-id']
    start_server(config['local-port'])
    startData = getStartData(config)
    startUrl = _api_url("public_api/election", config['auths'][0])
    print("> requesting election at %s" % startUrl)
    start_election(config, startUrl, startData)
    publicKey = wait_for_publicKey()
    pkFile = 'pk_' + electionId

    if(len(publicKey) > 0):
        print("> Saving pk to " + pkFile)
        with codecs.open(os.path.join(config['path'], pkFile), encoding='utf-8', mode='w+') as votes_file:
            votes_file.write(json.dumps(publicKey))
    else:
        print("No public key, exiting..")
        exit(1)

    return pkFile

def tally(cfg, args, do_start_server = True):
    config = cfg['electionCfg']
    partial = args.partial
    if do_start_server:
        start_server(config['local-port'])

    electionId = config['election-id']

    ctexts = cfg['ciphertexts']
    if partial > 0:
      ctexts = ctexts + "." + str(partial)
    ctextsPath = os.path.join(config['path'], ctexts)

    # need hash
    hash = hash_file(ctextsPath)
    print("> Votes hash is " + hash)
    tallyData = get_tally_data(config)
    tallyUrl = _api_url('public_api/tally', config['auths'][0])
    do_tally(config, tallyUrl, tallyData, ctexts, hash)
    tallyResponse = wait_for_tally()
    print(tallyResponse)

    if('tally_url' in tallyResponse):
        print("> Downloading tally from " + tallyResponse['tally_url'])
        download_tally(cfg, tallyResponse['tally_url'], partial)
    else:
        print("* Tally not found in http data")

def list_votes(cfg, args):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    # s = select([votes]).where(votes.c.election_id == cfg['electionCfg']['election-id'])
    s = select([votes]).where(votes.c.election_id == cfg['electionCfg']['election-id'])
    for filter in cfg['filters']:
        if "~" in filter:
            key, value = filter.split("~")
            s = s.where(getattr(votes.c, key).like(value))
        else:
            key, value = filter.split("==")
            s = s.where(getattr(votes.c, key) == (value))

    result = conn.execute(s)
    show_votes(result)

def count_votes(cfg, args):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    s = select([func.count(votes.c.id)]).where(votes.c.election_id == cfg['electionCfg']['election-id'])
    result = conn.execute(text("select count(*) from votes where id in (select distinct on (voter_id) id from votes where election_id in :ids order by voter_id, election_id desc)"), ids=tuple(args.command[1:]))
    row = result.fetchall()
    print(row[0][0])

# dumps votes in the format expected by eo
def dump_votes_eo(cfg, args):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    vs = conn.execute(text("select distinct on (voter_id) vote, voter_id, election_id from votes where election_id in :ids order by voter_id, election_id desc"), ids=tuple(args.command[1:])).fetchall()
    f = cfg['ciphertexts']
    path = os.path.join(cfg['electionCfg']['path'], f)
    votes_files = dict()
    max_size = args.max_count

    valid_votes = set()
    check_ids = (len(args.voter_ids_path) > 0)
    if check_ids:
        with codecs.open(args.voter_ids_path, encoding='utf-8', mode='r') as vip:
            for line in vip:
                valid_votes.add(line.strip())

    for election_id in args.command[1:]:
        path = os.path.join(ELECTIONS_DIR, election_id, 'ctexts_' + election_id)
        votes_files[election_id] = dict(
            total=0,
            filtered=0,
            partial=0,
            file=codecs.open(path, encoding='utf-8', mode='w+')
        )

    for vote in vs:
        meta = votes_files[vote['election_id']]

        # filter only for valid votes
        if check_ids:
            if not args.invalid and vote['voter_id'] not in valid_votes:
                meta["filtered"] += 1
                continue
            elif args.invalid and vote['voter_id'] in valid_votes:
                meta["filtered"] += 1
                continue

        meta['file'].write(vote['vote'] + "\n")
        meta["total"] += 1
        if max_size != 0 and meta['total'] % max_size == 0:
            meta['file'].close()
            meta['partial'] += 1
            path = os.path.join(ELECTIONS_DIR, election_id, 'ctexts_%s.%d' % (election_id, meta['partial']))
            meta['file'] = codecs.open(path, encoding='utf-8', mode='w+')
            print("creating partial for %s num %d" % (election_id, meta['partial']))

    total = 0
    filtered = 0
    for eid, meta in votes_files.items():
        total += meta['total']
        filtered += meta['filtered']
        print("> dumped %d votes to %s (%d filtered)" % (meta['total'], eid, meta['filtered']))
        meta['file'].close()
    print("> dumped %d votes in total (%d filtered)" % (total, filtered))


# prints voter ids
def print_voterids(cfg, args):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    vs = conn.execute(text("select distinct on (voter_id) vote, voter_id, election_id from votes where election_id in :ids order by voter_id, election_id desc"), ids=tuple(args.command[1:])).fetchall()
    f = cfg['ciphertexts']
    path = os.path.join(cfg['electionCfg']['path'], f)

    valid_votes = set()
    check_ids = (len(args.voter_ids_path) > 0)
    if check_ids:
        with codecs.open(args.voter_ids_path, encoding='utf-8', mode='r') as vip:
            for line in vip:
                valid_votes.add(line.strip())

    for vote in vs:
        # filter only for valid votes
        if check_ids:
            if vote['voter_id'] not in valid_votes:
                continue

        print(vote['voter_id'])


# dumps votes a format suitable for backup/restore
def dump_votes_full(cfg, args):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    s = select([votes]).where(votes.c.election_id == cfg['electionCfg']['election-id'])
    vs = conn.execute(s)
    data = []
    for vote in vs:
        data.append({
            'vote': vote[1],
            'vote_hash': vote[2],
            'election_id': vote[3],
            'voter_id': vote[4]
        })

    file = cfg['ciphertexts']
    path = os.path.join(cfg['electionCfg']['path'], file)
    with codecs.open(path, encoding='utf-8', mode='w+') as votes_file:
        votes_file.write(json.dumps(data, sort_keys=True))

    print("> dumped %d votes to %s" % (len(data), path))

def encrypt(cfg, args):
    config = cfg['electionCfg']
    electionId = config['election-id']
    pkFile = 'pk_' + electionId
    votesFile = cfg['plaintexts']
    votesCount = cfg['encrypt-count']
    ctexts = cfg['ciphertexts']

    print("> Encrypting votes (" + votesFile + ", pk = " + pkFile + ", " + str(votesCount) + ")..")
    pkPath = os.path.join(config['path'], pkFile)
    votesPath = os.path.join(config['path'], votesFile)
    ctextsPath = os.path.join(config['path'], ctexts)

    if(os.path.isfile(pkPath)) and (os.path.isfile(votesPath)):
        output, error = subprocess.Popen([node, "js/encrypt.js", pkPath, votesPath, str(votesCount)], stdout = subprocess.PIPE).communicate()

        print("> Received Nodejs output (" + str(len(output)) + " chars)")
        parsed = json.loads(output)

        print("> Writing file to " + ctextsPath)
        write_node_votes(parsed, ctextsPath)
    else:
        print("No public key or votes file, exiting..")
        exit(1)

def eotest(cfg, args):
    config = cfg['electionCfg']

    pkFile = create(cfg)

    if(os.path.isfile(os.path.join(config['path'], pkFile))):
        encrypt(cfg)
        tally(cfg, None, False)
    else:
        print("No public key, exiting..")

def list_elections(cfg, args):
    e = PrettyTable(['election id','director', 'authorities', 'pk', 'ctexts', 'tally'])
    elections = []
    for item in os.listdir(ELECTIONS_DIR):
        dir = os.path.join(ELECTIONS_DIR, item)
        if os.path.isdir(dir):
            jsonPath = os.path.join(dir, "config.json")
            if os.path.isfile(jsonPath):
                with open(jsonPath, 'r') as f:
                    config = json.loads(f.read())
                    if not 'election-id' in config:
                        config['election-id'] = os.path.basename(os.path.normpath(dir))

                    pkPath = os.path.join(dir, "pk_" + config['election-id'])
                    config['pk'] = os.path.isfile(pkPath)
                    ctextsPath = os.path.join(dir, "ctexts_" + config['election-id'])
                    config['ctexts'] = os.path.isfile(ctextsPath)
                    tallyPath = os.path.join(dir, config['election-id'] + ".tar.gz")
                    config['tally'] = os.path.isfile(tallyPath)

                    e.add_row([
                        config['election-id'],
                        config['director'],
                        config['authorities'],
                        config['pk'],
                        config['ctexts'],
                        config['tally']
                    ])

    print e

def console(cfg, args):
    conn = get_db_connection(cfg['backendCfg']['db'])
    import pdb; pdb.set_trace()

def reload_config(cfg, args):
    import hmac

    secret = cfg['backendCfg']['SharedSecret']
    message = 'admin:%d' % int(time.time())
    _hmac = hmac.new(str(secret), str(message), hashlib.sha256).hexdigest()
    auth = '%s:%s' % (message,_hmac)
    headers = {'content-type': 'application/json', 'Authorization': auth}
    url = 'http://localhost:%d/api/v1/ballotbox/reload-config' % args.ballotbox_port
    r = requests.post(url, data='{}', headers=headers)
    print(r.status_code)

def __load_votes_full(cfg):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    file = cfg['ciphertexts']
    path = os.path.join(cfg['electionCfg']['path'], file)
    with open(path, 'r') as f:
        vs = json.loads(f.read())

    conn.execute(votes.insert(), vs)
    print("> inserted %d votes" % len(vs))

def __load_node_votes(cfg):
    conn = get_db_connection(cfg['backendCfg']['db'])
    votes = votes_table()
    file = cfg['ciphertexts']
    path = os.path.join(cfg['electionCfg']['path'], file)
    with open(path, 'r') as f:
        # vs = f.readlines()
        vs = f.read().splitlines()

    vs = map(lambda v: {
        'vote': v,
        'vote_hash': hashlib.sha512(v).hexdigest(),
        'election_id': cfg['electionCfg']['election-id'],
        'voter_id': 'BOGUS' + hashlib.sha224(v).hexdigest()
    }, vs)
    conn.execute(votes.insert(), vs)
    print("> inserted %d votes" % len(vs))

def main(argv):
    parser = argparse.ArgumentParser(description='agora-api admin script', formatter_class=RawTextHelpFormatter)
    parser.add_argument('command', nargs='+', help='''create <election_dir>: creates an election
tally <election_dir>: launches tally
list_votes <election_dir>: list votes
list_elections: list elections (under ELECTIONS_DIR)
count_votes <election_dir> [<election_dir2> [<election_dir3> [..]]]: count votes
dump_votes_eo <election_dir> [<election_dir2> [<election_dir3> [..]]]: dumps votes ready for eo
print_voterids <election_dir> [<election_dir2> [<election_dir3> [..]]]: prints voter ids
dump_votes_full <election_dir>: dumps votes in local format
console <data>: executes a console
eotest <election_dir>: runs a full eo test cycle''')
    parser.add_argument('--eopeers-dir', help='directory with the eopeers packages to use as authorities', default = '/etc/eopeers/')
    parser.add_argument('--ciphertexts', help='file to write ciphertetxs (used in dump, load and encrypt)')
    parser.add_argument('--tally-file', help='the file to save the tally to (used with "tally")')
    parser.add_argument('--force', help='force to continue even if something strange happens, like /etc/eopeers doesnt exist',
                        action='store_true')
    parser.add_argument('--invalid', help='voter ids path are the invalid', action='store_true')
    parser.add_argument('--plaintexts', help='json file to read votes from when encrypting', default = 'votes.json')
    parser.add_argument('--encrypt-count', help='number of votes to encrypt (generates duplicates if more than in json file)', type=int, default = 0)
    parser.add_argument('-m', '--max-count', help='when creating doing a dump, maximum size of each dump part', type=int, default=0)
    parser.add_argument('-p', '--partial', help='partial of which to do the tally', type=int, default=-1)
    parser.add_argument('-f', '--filters', nargs='+', default=[], help="key==value(s) filters for queries (use ~ for like)")
    parser.add_argument('--voter-ids-path', nargs='?', default=[], help="Path to a file with valid voter ids for filtering")
    parser.add_argument('--ballotbox-port', help='the port that the ballotbox is listening on', type=int, default = 3000)
    args = parser.parse_args()
    command = args.command[0]
    if hasattr(__main__, command):
        backendConfig = get_backend_config()
        config = {
            "backendCfg": backendConfig
        }

        if command == "console":
            console(config, args)

        elif command not in ["list_elections", "reload_config"]:
            # election-specific commands
            if len(args.command) >= 2:
                electionConfig = get_election_config(args.command[1], args.eopeers_dir, args.force)
                config['electionCfg'] = electionConfig

                config['plaintexts'] = args.plaintexts
                config['encrypt-count'] = args.encrypt_count
                config['filters'] = args.filters
                if args.tally_file is None:
                    config['tally-file'] = electionConfig['election-id'] + '.tar.gz'
                else:
                    config['tally-file'] = args.tally_file

                if args.ciphertexts is None:
                    config['ciphertexts'] = 'ctexts_' + electionConfig['election-id']
                else:
                    config['ciphertexts'] = args.ciphertexts
            else:
                parser.print_help()
                exit(1)

        eval(command + "(config, args)")

    else:
        parser.print_help()

if __name__ == "__main__":
	main(sys.argv[1:])
