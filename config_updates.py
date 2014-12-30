#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of agora-tools.
# Copyright (C) 2014 Eduardo Robles Elvira <edulix AT agoravoting DOT com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import operator
import argparse
import requests
import collections
from datetime import datetime, timedelta

from utils.csvblocks import csv_to_blocks
from utils.json import serialize
from utils.tree import (edges2simpletree, list_edges, list_leaves, list_all,
                        get_list)

def get_changes_tree(changes):
    '''
    Given the changes configuration, generates a simple dict based tree
    with the ids of the changed elections
    '''
    def get_parent(value):
        return value['election_id']

    def get_child(value):
        return value.get('new_election_id', None)

    edges = [(get_parent(val), get_child(val)) for val in changes]
    return edges2simpletree(edges)

def get_changes_config(changes_path):
    '''
    Given the path of the changes configuration
    '''
    blocks = csv_to_blocks(path=changes_path, separator="\t")
    return blocks[0]['values']

def get_node_changes(tree, changes):
    '''
    Given the election changes list and the election ids tree, create a dictionary
    with the key being the ids of the election, and the value the list of
    changes for that election with respect with the parent, extracted from
    the changes list in order.
    '''
    node_changes = collections.defaultdict(list)
    for change in changes:
        key = change.get('new_election_id')
        if key in [None, '']:
            key = change['election_id']
        node_changes[key].append(change)
    return node_changes

def list_ids(config, changes_path, action):
    '''
    Executes print actions related to the listing of election ids from the
    changes file. Available actions are 'tree', 'edges', 'leaves' and 'all'.
    '''
    changes = get_changes_config(changes_path)
    tree = get_changes_tree(changes)

    if action == 'tree':
      print(serialize(tree))
      return

    l = []
    if action == "edges":
        list_edges(tree, l)
    if action == "leaves":
        list_leaves(tree, l)
    else:
        list_all(tree, l)

    l.sort()
    for election_id in l:
        print(election_id)

def download_elections(config, changes_path, elections_path, ids_path):
    '''
    Download the configuration for the elections listed in the changes
    '''
    changes = get_changes_config(changes_path)
    tree = get_changes_tree(changes)
    election_ids = get_list(tree, list_all)

    other_ids = []
    if ids_path is not None:
        with open(ids_path, mode='r', encoding="utf-8", errors='strict') as f:
            for line in f:
                line = line.strip()
                other_ids.append(line)
    else:
        print("WARNING: ids_path not supplied")

    # join both list of ids, removing duplicates
    election_ids = list(set(election_ids + other_ids))
    # sort list, just to be ordered (not really needed)
    election_ids.sort()

    headers = {'content-type': 'application/json'}
    base_url = config['agora_elections_base_url']

    # retrieve and save each election config
    for election_id in election_ids:
        url = '%s/election/%s' % (base_url, election_id.strip())
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            print(r.status_code, r.text)
            raise Exception('Invalid status code: %d for election_id = %s' % (r.status_code, election_id))

        epath = os.path.join(elections_path, "%s.config.json" % election_id)
        with open(epath, mode='w', encoding="utf-8", errors='strict') as f:
            f.write(r.text)

def get_election_config(elections_path, election_id):
    '''
    boilerplate for getting election config
    '''
    election_path = os.path.join(elections_path, "%s.config.json" % election_id)
    with open(election_path, mode='r', encoding="utf-8", errors='strict') as f:
        election_config = json.loads(json.loads(f.read())["payload"]['configuration'])
        return election_config

def get_changes_func(func_name):
    '''
    gets a function by name from utils.changes module
    '''
    module = __import__(
        "utils.changes", globals(), locals(),
        [func_name], 0)
    return getattr(module, func_name)


def check_change_applied(func_name, kwargs, election_id, election_config):
    '''
    Applies a function to an election config
    '''
    fargs = dict(election_config=election_config, election_id=election_id)
    if kwargs is not None:
        fargs.update(kwargs)
    get_changes_func(func_name)(**fargs)

# TODO
def get_changes_chain_for_election_id(election_id, config, tree, node_changes):
    return None

# TODO
def check_diff_changes(election_changes, election_id, tree):
    pass

def check_changes(config, changes_path, elections_path, ids_path):
    '''
    Checks that the configuration set
    '''
    # get changes and tree data
    changes = get_changes_config(changes_path)
    tree = get_changes_tree(changes)
    node_changes = get_node_changes(tree, changes)
    election_ids = get_list(tree, list_all)

    # get all the ids
    other_ids = []
    if ids_path is not None:
        with open(ids_path, mode='r', encoding="utf-8", errors='strict') as f:
            for line in f:
                line = line.strip()
                other_ids.append(line)
            # add to the tree the id as a root leave if not present
            if line not in election_ids:
                tree[line] = dict()
    else:
        print("WARNING: ids_path not supplied")

    # join both list of ids, removing duplicates, and sorting the list
    election_ids = list(set(election_ids + other_ids))
    election_ids.sort()

    # check first global_prechanges
    for election_id in election_ids:
        election_config = get_election_config(elections_path, election_id)
        for change, kwargs in config['global_prechanges']:
            check_change_applied(change, kwargs, election_id, election_config)

    # check the remaining changes
    #for election_id in election_ids:
        #election_changes = get_changes_chain_for_election_id(
            #election_id, config, tree, node_changes)
        #check_diff_changes(election_changes, election_id, tree)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Helps doing configuration updates.')
    parser.add_argument(
        '-c',
        '--config-path',
        help='default config for the election',
        required=True)
    parser.add_argument(
        '-C',
        '--changes-path',
        help='tsv file with the changes',
        required=True)

    parser.add_argument(
        '-e',
        '--elections-path',
        help='directory where the elections configuration should be')

    parser.add_argument(
        '-i',
        '--ids-path',
        help='path to the file with all the election ids, one per line',
        default=None)

    parser.add_argument(
        '-a',
        '--action',
        help='action to execute',
        choices=[
            'print_tree_ids',
            'print_edges_ids',
            'print_leaves_ids',
            'print_all_ids',
            'download_elections',
            'check_changes',
            'print_agora_elections_commands',
            'write_agora_results_files'],
        required=True)

    args = parser.parse_args()

    if not os.access(args.changes_path, os.R_OK):
        print("changes_path: can't read %s" % args.changes_path)
        exit(2)
    if not os.path.isfile(args.changes_path):
        print("changes_path: not a file %s" % args.changes_path)
        exit(2)
    if not os.access(args.config_path, os.R_OK):
        print("config_path: can't read %s" % args.config_path)
        exit(2)
    if not os.path.isfile(args.config_path):
        print("config_path: not a file %s" % args.config_path)
        exit(2)
    if not os.access(args.ids_path, os.R_OK):
        print("ids_path: can't read %s" % args.ids_path)
        exit(2)
    if not os.path.isfile(args.ids_path):
        print("ids_path: not a file %s" % args.ids_path)
        exit(2)

    config = None
    with open(args.config_path, mode='r', encoding="utf-8", errors='strict') as f:
        config = json.loads(f.read())

    def elections_path_check(acces_check):
        if not os.path.isdir(args.elections_path):
            print("elections_path: %s is not a directory" % args.elections_path)
            exit(2)
        if not os.access(args.elections_path, acces_check):
            print("elections_path: can't read %s" % args.elections_path)
            exit(2)

    if args.action == 'print_tree_ids':
        list_ids(config, args.changes_path, action="tree")
    if args.action == 'print_edges_ids':
        list_ids(config, args.changes_path, action="edges")
    if args.action == 'print_leaves_ids':
        list_ids(config, args.changes_path, action="leaves")
    if args.action == 'print_all_ids':
        list_ids(config, args.changes_path, action="all")
    if args.action == 'download_elections':
        elections_path_check(os.W_OK)
        download_elections(config, args.changes_path, args.elections_path, args.ids_path)
    if args.action == 'check_changes':
        elections_path_check(os.R_OK)
        check_changes(config, args.changes_path, args.elections_path, args.ids_path)
    elif args.action == 'print_agora_elections_commands':
        pass
    elif args.action == 'write_agora_results_files':
        elections_path_check(os.W_OK)
