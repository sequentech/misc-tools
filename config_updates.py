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
import sys
import copy
import operator
import argparse
import requests
import traceback
import subprocess
import collections
from datetime import datetime, timedelta

from datadiff import diff

from utils.csvblocks import csv_to_blocks
from utils.json import serialize
from utils.tree import (edges2simpletree, list_edges, list_leaves, list_all,
                        get_list, get_ancestors)
from utils.hashed_changes import hash_question
from utils.deterministic_tar import deterministic_tar_open, deterministic_tar_add

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

def list_ids(config, changes_path, action, ids_path=None):
    '''
    Executes print actions related to the listing of election ids from the
    changes file. Available actions are 'tree', 'edges', 'leaves' and 'all'.
    '''
    changes = get_changes_config(changes_path)
    tree = get_changes_tree(changes)
    l = []

    def add_others(l, ids_path):
        other_ids = []
        with open(ids_path, mode='r', encoding="utf-8", errors='strict') as f:
            for line in f:
                line = line.strip()
                other_ids.append(line)

        l = list(set(other_ids + l))
        l.sort()
        return l

    if action == 'tree':
        print(serialize(tree))
        return
    elif action == 'leaves_ancestors':
        list_leaves(tree, l)
        l = add_others(l, ids_path)
        ancestors = dict()
        for election_id in l:
            ancestors[election_id] = get_ancestors(tree, election_id) + [election_id]
        for election_id in l:
            print(",".join(ancestors[election_id]))
        return

    if action == 'edges':
        list_edges(tree, l)
    elif action == 'leaves':
        list_leaves(tree, l)
    elif action == 'all_with_others':
        list_all(tree, l)
        l = add_others(l, ids_path)
    elif action == 'all':
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

def get_changes_func(func_name, module_path):
    '''
    gets a function by name from utils.changes module
    '''
    module = __import__(module_path, globals(), locals(), [func_name], 0)
    return getattr(module, func_name)


def check_change_applied(func_name, kwargs, election_id, election_config):
    '''
    Applies a function to an election config
    '''
    fargs = dict(election_config=election_config, election_id=election_id)
    if kwargs is not None:
        fargs.update(kwargs)
    get_changes_func(func_name, 'utils.prechanges_check')(**fargs)

def get_changes_chain_for_election_id(election_id, config, tree, node_changes):
    '''
    Gets a complete list of changes to apply to an election
    '''
    changes_chain = []
    # contains self
    ancestors = get_ancestors(tree, election_id) + [election_id]

    for ancestor_id in ancestors:
        changes_chain = changes_chain + node_changes[ancestor_id]
    return changes_chain, ancestors

def apply_elections_changes(config, elections_path, ancestors, election_id,
    election_changes):
    '''
    Apply changes to the given election
    '''
    election_config = get_election_config(elections_path, ancestors[0])
    mod_path = 'utils.apply_election_changes'
    for change in election_changes:
        kwargs = dict(change=change, election_config=election_config)
        try:
            get_changes_func(change['action'], mod_path)(**kwargs)
        except:
            print("Error processing election(%s) change(%s):" % (
                election_id, change['action']))
            traceback.print_exc()
    election_config['id'] = int(election_id)
    return election_config

def check_diff_changes(elections_path, election_id, calculated_election_config):
    election_config = get_election_config(elections_path, election_id)
    if serialize(election_config) != serialize(calculated_election_config):
        print("calculated election config differs for election %s. showing diff(config, calculated)" % election_id)
        print(diff(election_config, calculated_election_config))
        print(serialize(calculated_election_config))


def check_changes(config, changes_path, elections_path, ids_path):
    '''
    Checks that the configuration set
    '''
    # get changes and tree data
    changes = get_changes_config(changes_path)
    tree = get_changes_tree(changes)
    node_changes = get_node_changes(tree, changes)
    election_ids = get_list(tree, list_all)
    parse_parity_config(config)

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
    for election_id in election_ids:
        election_changes, ancestors = get_changes_chain_for_election_id(
            election_id, config, tree, node_changes)

        calculated_election = apply_elections_changes(
            config, elections_path, ancestors, election_id, election_changes)
        check_diff_changes(elections_path, election_id, calculated_election)

        # check that all final elections have been tagged with the sex
        if "agora_results_config_parity" in config:
            cfg = config["agora_results_config_parity"]
            names = dict([
                (i['answer_text'], i['is_woman'])
                for i in cfg['parity_list']
                if int(i['election_id']) == int(election_id)])

            if len(names) == 0:
                print("election %d not in the parity list")
                continue

            for question in calculated_election['questions']:
                for answer in question['answers']:
                    if answer['text'] not in names:
                        print("Answer '%s' from election '%d' not in parity list" % (
                            answer['text'], int(election_id)))

def apply_results_config_prechanges(func_name, kwargs, ancestors, election_id,
    election_config, results_config):
    '''
    Get the prechanges and apply them in results_config
    '''
    fargs = dict(
        election_config=election_config,
        election_id=election_id,
        ancestors=ancestors,
        results_config=results_config)
    if kwargs is not None:
        fargs.update(kwargs)
    get_changes_func(func_name, 'utils.prechanges_results')(**fargs)


def find_question_mappings(hashed_election_configs, ancestors, dest_question, dest_question_num):
    '''
    Given a hashed question, the ancestors and the configs of the ancestors,
    returns a list of found mappings, meaning, a list of places of locations
    where the same question hash has been found in the ancestors.

    Example return value:
    [
    {
      'source_election_id': 0,
      'source_question_num': 0,
      'source_question_title': "what?",
      'dest_question_num': 0,
      'dest_question_title': "what?",
    },
    ...
   ]
    '''
    q_mappings = []
    for ancestor in ancestors:
        election_config = hashed_election_configs[ancestor]['config']
        questions = election_config['questions']
        for question, question_num in zip(questions, range(len(questions))):
            if question['hash'] == dest_question['hash']:
                if question['title'] != dest_question['title']:
                    print("WARNING: question mapping for different titles: (source, dest) = ('%s', '%s')" % (
                        question['title'], dest_question['title']))
                q_mappings.append({
                    'source_election_id': int(ancestor),
                    'source_question_num': question_num,
                    'source_question_title': question['title'],
                    'dest_question_num': dest_question_num,
                    'dest_question_title': dest_question['title'],
                })
    return q_mappings


def find_answer_mappings(hashed_election_configs, ancestors, dest_answer, dest_question_num):
    '''
    Given an answer hash, the ancestors and the configs of the ancestors,
    returns a list of found mappings, meaning, a list of places of locations
    where the same answer hash has been found in the ancestors.

    Example return value:
    [
      {
        "source_election_id": 0,
        "source_question_num": 0,
        "source_answer_id": 1
        "source_answer_text": "whatever",
        "dest_question_num": 0,
        "dest_answer_id": 1
        "dest_answer_text": "whatever"
      },
      ...
    ]
    '''
    answer_mappings = []
    for ancestor in ancestors:
        election_config = hashed_election_configs[ancestor]['config']
        questions = election_config['questions']
        for question, question_num in zip(questions, range(len(questions))):
            for answer in question['answers']:
                if answer['hash'] == dest_answer['hash']:
                    if answer['text'] != dest_answer['text']:
                        print("WARNING: answer mapping for different texts: (source, dest) = ('%s', '%s')" % (
                            answer['text'], dest_answer['text']))
                    answer_mappings.append({
                        "source_election_id": int(ancestor),
                        "source_question_num": question_num,
                        "source_answer_id": answer['id'],
                        "source_answer_text": answer['text'],
                        "dest_question_num": dest_question_num,
                        "dest_answer_id": dest_answer['id'],
                        "dest_answer_text": dest_answer['text']
                    })
    return answer_mappings


def post_process_results_config(
    config,
    elections_path,
    ancestors,
    election_id,
    results_config,
    election_config,
    hashed_election_configs):
    '''
    Adds the election-specific results configuration to results_config
    '''
    questions = election_config['questions']

    # first check for size corrections
    if 'max_winners_mapping' in election_config:
        results_config.insert(0, [
            "agora_results.pipes.multipart.election_max_size_corrections",
            {"corrections": election_config['max_winners_mapping']}
        ])

    # check if multipart tallying needs to happen
    if len(ancestors) > 1:
        # the first element of the agora_results config (before the do_tallies)
        # should be a make_multipart with the list of ancestors
        results_config.insert(0, [
            "agora_results.pipes.multipart.make_multipart",
            {"election_ids": [int(ancestor) for ancestor in ancestors]}
        ])

        # fill the answers and questions mappings
        mappings = []
        qmappings = []
        for question, dest_question_num in zip(questions, range(len(questions))):
          qmappings = qmappings + find_question_mappings(
                hashed_election_configs, ancestors[:-1], question, dest_question_num)

          for answer in question['answers']:
            answer_mappings = find_answer_mappings(
                hashed_election_configs, ancestors[:-1], answer, dest_question_num)
            if len(answer_mappings) > 0:
                mappings = mappings + answer_mappings

        results_config.append([
            "agora_results.pipes.multipart.question_totals_with_corrections",
            {"mappings": qmappings}
        ])

        results_config.append([
            "agora_results.pipes.multipart.reduce_answers_with_corrections",
            {"mappings": mappings}
        ])

    # add sorting if needed
    if "agora_results_config_sorting" in config:
        results_config[:] = results_config + config["agora_results_config_sorting"]

    # add parity at the end
    if "agora_results_config_parity" in config:
        if config["agora_results_config_parity"]["method"] == "podemos_proportion_rounded_and_duplicates":
            cfg = config["agora_results_config_parity"]
            withdrawls = []
            if "tie_withdrawals" in election_config:
                withdrawls = election_config['tie_withdrawals'][str(election_id)]
            results_config.append([
                "agora_results.pipes.podemos.podemos_proportion_rounded_and_duplicates",
                {
                    "women_names":[
                        i['answer_text']
                        for i in cfg['parity_list']
                        if i['is_woman'] and int(i['election_id']) == int(election_id)],
                    "proportions": cfg["proportions"],
                    "withdrawed_candidates": withdrawls
                }
            ])
        elif config["agora_results_config_parity"]["method"] == "parity_zip_plurality_at_large":
            cfg = config["agora_results_config_parity"]
            results_config.append([
                "agora_results.pipes.parity.parity_zip_plurality_at_large",
                {
                    "women_names": cfg['parity_list']
                }
            ])


def apply_changes_hashing(
    election_id,
    election_config,
    election_changes,
    ancestors,
    elections_path):
    '''
    Applies the changes in the elections hashing the questions and answers in
    a reproducible them, to be able to later on backtrack the original answers
    and questions
    '''

    # first of all, hash all the questions and answers in a reproducible way
    questions = election_config['questions']
    for question, i in zip(questions, range(len(questions))):
        hash_question(question, ancestors[0], i)

    mod_path = 'utils.hashed_changes'
    for change in election_changes:
        kwargs = dict(change=change, election_config=election_config)
        try:
            get_changes_func(change['action'], mod_path)(**kwargs)
        except:
            print("Error processing election(%s) change(%s):" % (
                election_id, change['action']))
            traceback.print_exc()
    election_config['id'] = int(election_id)
    return election_config

def parse_parity_config(config):
    '''
    parses parity config
    '''
    if "agora_results_config_parity" in config:
        parity_list = []
        if config["agora_results_config_parity"]["method"] == "podemos_proportion_rounded_and_duplicates":
            path = config["agora_results_config_parity"]['sexes_tsv']
            with open(path, mode='r', encoding="utf-8", errors='strict') as f:
                for line in f:
                    line = line.strip()
                    election_id, sex, answer_text = line.split("\t")
                    parity_list.append(dict(
                        election_id=int(election_id.strip()),
                        is_woman=sex.strip() == 'M',
                        answer_text=answer_text
                    ))
        else:
            with open(path, mode='r', encoding="utf-8", errors='strict') as f:
                for line in f:
                    answer_text = line.strip()
                    parity_list.append(answer_text)
        config["agora_results_config_parity"]['parity_list'] = parity_list


def write_agora_results_files(config, changes_path, elections_path, ids_path):
    '''
    Checks that the configuration set
    '''
    # get changes and tree data
    changes = get_changes_config(changes_path)
    tree = get_changes_tree(changes)
    node_changes = get_node_changes(tree, changes)
    election_ids = get_list(tree, list_all)
    final_ids = get_list(tree, list_leaves)
    parse_parity_config(config)

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
    final_ids = list(set(final_ids + other_ids))
    final_ids.sort()

    election_ids = list(set(election_ids + other_ids))
    election_ids.sort()

    # calculate a configuration for each election, including middle steps, so
    # that later on the answers between election can be tracked and collected
    # by hash
    hashed_election_configs = dict()
    for election_id in election_ids:
        election_changes, ancestors = get_changes_chain_for_election_id(
            election_id, config, tree, node_changes)
        election_config = get_election_config(elections_path, ancestors[0])
        apply_changes_hashing(
          election_id,
          election_config,
          election_changes,
          ancestors,
          elections_path)
        hashed_election_configs[election_id] = dict(
            config=election_config,
            ancestors=ancestors
        )

    # iterate and process the results config for all final elections
    for election_id in final_ids:
        election_config = hashed_election_configs[election_id]['config']
        ancestors = hashed_election_configs[election_id]['ancestors']
        results_config = copy.deepcopy(config['agora_results_config'])

        # apply first global_prechanges
        for change, kwargs in config['global_prechanges']:
            apply_results_config_prechanges(
                change,
                kwargs,
                ancestors,
                election_id,
                election_config,
                results_config)

        post_process_results_config(
            config,
            elections_path,
            ancestors,
            election_id,
            results_config,
            election_config,
            hashed_election_configs)

        epath = os.path.join(elections_path, "%s.config.results.json" % election_id)
        with open(epath, mode='w', encoding="utf-8", errors='strict') as f:
            f.write(serialize(results_config))

def calculate_results(config, tree_path, elections_path, check):
    '''
    Launches agora-results for those elections that do have a tally
    '''
    cfg_res_postfix = '.config.results.json'
    ids_w_res_config = [
        int(f.replace(cfg_res_postfix, ''))
        for f in os.listdir(elections_path)
        if os.path.isfile(os.path.join(elections_path, f)) and f.endswith(cfg_res_postfix)]

    with open(tree_path, mode='r', encoding="utf-8", errors='strict') as f:
        tree = [[int(a.strip()) for a in line.strip().split(",")] for line in f]

    priv_path = config["agora_elections_private_datastore_path"]
    for eids in tree:
        # check for config file
        last_id = eids[-1]
        if last_id not in ids_w_res_config:
            print("eids = %s, no res config for %d, passing" % (json.dumps(eids), last_id))
            continue

        # check for tallies
        tallies = []
        for eid in eids:
            tally_path = os.path.join(priv_path, str(eid), 'tally.tar.gz')
            ids_path = os.path.join(priv_path, str(eid), 'ids')
            if not os.path.isfile(ids_path):
                print("eids = %s, eid %d has not even ids, passing" % (json.dumps(eids), eid))
            if not os.path.isfile(tally_path):
                print("eids = %s, eid %d has no tally (yet?), passing" % (json.dumps(eids), eid))
                break
            tallies.append(tally_path)
        if len(tallies) != len(eids):
            continue

        print("eids = %s: calculating results.. " % json.dumps(eids), end="")

        # got the tallies, the config file --> calculate results
        def create_results(last_id, cfg_res_postfix, elections_path, bin_path, oformat, only_check=False):
            cmd = "%s -t %s -c %s -s -o %s" % (
                bin_path,
                " ".join(tallies),
                os.path.join(elections_path, str(last_id) + cfg_res_postfix),
                oformat)
            if only_check:
                print(cmd)
                cmd = cmd.replace("-s ", "")
            print(oformat, end=' ')
            if only_check:
                subprocess.check_call(cmd, stderr=sys.stderr, shell=True)
                return
            f_path = os.path.join(elections_path, str(last_id) + ".results." + oformat)
            with open(f_path, mode='w', encoding="utf-8", errors='strict') as f:
                subprocess.check_call(cmd, stdout=f, stderr=sys.stderr, shell=True)

        bin_path = config['agora_results_bin_path']
        create_results(last_id, cfg_res_postfix, elections_path, bin_path, "json", only_check=check)
        if not check:
            create_results(last_id, cfg_res_postfix, elections_path, bin_path, "tsv")
            create_results(last_id, cfg_res_postfix, elections_path, bin_path, "pretty")
        print()

def count_votes(config, tree_path):
    '''
    Counts votes per election id and in total
    '''
    priv_path = config["agora_elections_private_datastore_path"]

    with open(tree_path, mode='r', encoding="utf-8", errors='strict') as f:
        tree = [[int(a.strip()) for a in line.strip().split(",")] for line in f]

    total_votes = 0
    for eids in tree:
        last_id = eids[-1]

        # check for ids
        n_votes = []
        for eid in eids:
            ids_path = os.path.join(priv_path, str(eid), 'ids')
            if not os.path.isfile(ids_path):
                print("eids = %s, eid %d has not even ids, passing" % (json.dumps(eids), eid))
                n_votes.append(None)
                continue
            n_votes2 = 0
            with open(ids_path, mode='r', encoding="utf-8", errors='strict') as f:
                n_votes2 = len(json.loads(f.read()))
            n_votes.append(n_votes2)
            total_votes += n_votes2
        print("%s = %s" % (json.dumps(eids), json.dumps(n_votes)))
    print("total votes: %d" % total_votes)

def tar_tallies(config, tree_path, elections_path, tallies_path):
    '''
    Tars the tallies conveniently
    '''
    priv_path = config["agora_elections_private_datastore_path"]

    with open(tree_path, mode='r', encoding="utf-8", errors='strict') as f:
        tree = [[int(a.strip()) for a in line.strip().split(",")] for line in f]

    def can_read_file(f):
      return os.access(f, os.R_OK) and os.path.isfile(f)

    def check_files(paths, eids):
        for path in paths:
            if not can_read_file(path):
                print("eids = %s, has no %s, passing" % (
                    json.dumps(eids), path))
                return False
        return True


    total_votes = 0
    for eids in tree:
        last_id = eids[-1]

        # check all needed files are there
        paths = [
            os.path.join(elections_path, "%d.results.json" % last_id),
            os.path.join(elections_path, "%d.config.results.json" % last_id)
        ] + [
            os.path.join(priv_path, str(eid), 'tally.tar.gz')
            for eid in eids
        ]
        if not check_files(paths, eids):
            continue

        # create tar
        tar_path = os.path.join(tallies_path, "%d.tar" % last_id)
        print("creating %s .." % tar_path)
        tar = deterministic_tar_open(tar_path, "w")

        arc_names = ["results.json", "config.json"] + ["%d.tar.gz" % i for i in range(len(eids))]
        for path, arc_name in zip(paths, arc_names):
            deterministic_tar_add(tar, path, arc_name)
        tar.close()

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
        help='tsv file with the changes')

    parser.add_argument(
        '-e',
        '--elections-path',
        help='directory where the elections configuration should be')

    parser.add_argument(
        '-t',
        '--tree-path',
        help='file generated with print_leaves_ancestors_ids')

    parser.add_argument(
        '-i',
        '--ids-path',
        help='path to the file with all the election ids, one per line',
        default=None)

    parser.add_argument(
        '-T',
        '--tallies-path',
        help='path where to save the tallies',
        default=None)

    parser.add_argument(
        '-a',
        '--action',
        help='action to execute',
        choices=[
            'print_tree_ids',
            'print_edges_ids',
            'print_leaves_ids',
            'print_leaves_ancestors_ids',
            'print_all_ids',
            'print_all_with_others_ids',
            'download_elections',
            'check_changes',
            'write_agora_results_files',
            'calculate_results',
            'check_results',
            'count_votes',
            'tar_tallies'],
        required=True)

    args = parser.parse_args()

    if not os.access(args.config_path, os.R_OK):
        print("config_path: can't read %s" % args.config_path)
        exit(2)
    if not os.path.isfile(args.config_path):
        print("config_path: not a file %s" % args.config_path)
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
    elif args.action == 'print_edges_ids':
        list_ids(config, args.changes_path, action="edges")
    elif args.action == 'print_leaves_ids':
        list_ids(config, args.changes_path, action="leaves")
    elif args.action == 'print_leaves_ancestors_ids':
        list_ids(config, args.changes_path, action="leaves_ancestors", ids_path=args.ids_path)
    elif args.action == 'print_all_ids':
        list_ids(config, args.changes_path, action="all")
    elif args.action == 'print_all_with_others_ids':
        list_ids(config, args.changes_path, action="all_with_others", ids_path=args.ids_path)
    elif args.action == 'download_elections':
        elections_path_check(os.W_OK)
        download_elections(config, args.changes_path, args.elections_path, args.ids_path)
    elif args.action == 'check_changes':
        elections_path_check(os.R_OK)
        check_changes(config, args.changes_path, args.elections_path, args.ids_path)
    elif args.action == 'calculate_results':
        calculate_results(config, args.tree_path, args.elections_path, check=False)
    elif args.action == 'check_results':
        calculate_results(config, args.tree_path, args.elections_path, check=True)
    elif args.action == 'tar_tallies':
        tar_tallies(config, args.tree_path, args.elections_path, args.tallies_path)
    elif args.action == 'count_votes':
        count_votes(config, args.tree_path)
    elif args.action == 'write_agora_results_files':
        elections_path_check(os.W_OK)
        write_agora_results_files(config, args.changes_path, args.elections_path, args.ids_path)
