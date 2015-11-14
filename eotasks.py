#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of election-orchestra.
# Copyright (C) 2013,2015  Eduardo Robles Elvira <edulix AT wadobo DOT com>

# election-orchestra is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# election-orchestra  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with election-orchestra.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import argparse
from sqlalchemy.sql import text
from frestq.fscheduler import FScheduler
from frestq.utils import (list_messages, list_tasks, task_tree, show_task,
                    show_message, show_external_task, finish_task, get_tasks, get_external_task)

from prettytable import PrettyTable
import json


def get_election_path(path_type, election_id, *args):
    '''
    return an election public path. path_type is either 'private' or 'public'.
    '''
    data_path = app.config.get(path_type.upper() + '_DATA_PATH', '')
    election_path = os.path.join(data_path, str(election_id))
    return os.path.join(election_path, *args)

def allow_disjoint_multiple_tallies(election_id):
    '''
    Marks an election as to allow multiple tallies, although with a disjoint
    set of votes (no vote can be repeated).
    '''
    election_privpath = get_election_path('private', election_id)
    allow_disjoint_multiple_tallies_path = get_election_path('private',
        election_id, 'allow_disjoint_multiple_tallies')

    if not os.path.exists(election_privpath):
        print("election id='%s' not found in path '%s'" % (str(election_id), election_privpath))
    elif not os.path.exists(allow_disjoint_multiple_tallies_path):
        open(allow_disjoint_multiple_tallies_path, 'w').close()
    else:
        print("election id='%s' already has the allow_disjoint_multiple_tallies activated" % str(election_id))

def disallow_disjoint_multiple_tallies(election_id):
    '''
    Marks an election as to NOT allow multiple tallies.
    '''
    election_privpath = get_election_path('private', election_id)
    allow_disjoint_multiple_tallies_path = get_election_path('private',
        election_id, 'allow_disjoint_multiple_tallies')

    if not os.path.exists(election_privpath):
        print("election id='%s' not found in path '%s'" % (str(election_id), election_privpath))
    elif not os.path.exists(allow_disjoint_multiple_tallies_path):
        print("election id='%s' already has the allow_disjoint_multiple_tallies NOT activated" % str(election_id))
    else:
        os.unlink(allow_disjoint_multiple_tallies_path)

def reset_tally(election_id):
    '''
    Remove traces of previous tallies of the specified election so that a new
    fresh tally can be executed.
    '''
    election_privpath = get_election_path('private', election_id)
    delete_paths = [
        get_election_path('private',  election_id, 'allow_disjoint_multiple_tallies'),
        get_election_path('public', election_id, 'tally.tar.gz'),
        get_election_path('public', election_id,  'tally.tar.gz.sha256')
    ]

    # check that the election exists
    if not os.path.exists(election_privpath):
        print("election id='%s' not found in path '%s'" % (str(election_id), election_privpath))

    # remove files if they exist
    for dpath in delete_paths:
        if os.path.exists(dpath):
            os.unlink(dpath)

    # reset ballot list for this election, so that it's allowed to tally the
    # already tallied votes
    election = db.session.connection().execute(
      text("DELETE FROM ballot WHERE session_id IN (SELECT id FROM session WHERE election_id = :election_id)"),
      election_id=str(election_id))
    db.session.commit()

def print_task_list(tasks):
    table = PrettyTable(['small id', 'label', 'election', 'sender_url', 'created_date'])

    for task in tasks:
          election = task.input_data['Title']
          question = ''

          table.add_row([str(task.id)[:8], task.label, election, task.sender_url, task.created_date])

    print table

def print_task(task):
    table = PrettyTable(header=False)
    election = task.input_data['Title']
    if 'Question data' in task.input_data:
        question_data =  task.input_data['Question data']
        questions = ''
        for q in question_data:
            questions = questions + q['question'] + " "

    table.add_row(["small id", str(task.id)[:8]])
    table.add_row(["election", election])
    table.add_row(["label", task.label])

    if len(questions) > 0:
        table.add_row(["questions", questions.strip()])
    table.add_row(["sender_url",  task.sender_url])
    table.add_row(["created_date", task.created_date])

    print table

# local parser
parser = None
def process_parser(self, class_parser):
    parser = class_parser

    parser.add_argument("--list", help="list last tasks",
                        action="store_true")

    parser.add_argument("--show", help="show task")

    parser.add_argument("--show-full", help="show task detail")

    parser.add_argument("--accept", help="accept task")

    parser.add_argument("--reject", help="reject task")

    parser.add_argument("--allow-disjoint-multiple-tallies",
      action='store_true',
      help="Allow tallies of different subsets of votes. Specify election id with --election-id.")

    parser.add_argument("--disallow-disjoint-multiple-tallies",
      action='store_true',
      help="Allow tallies of different subsets of votes. Specify election id with --election-id.")

    parser.add_argument("--reset-tally",
      action='store_true', help="Reset tally, allowing a completely fresh tally to be done, even repeating ballots.")

    parser.add_argument("--election-id", help="Election id", type=str)

from frestq.frestq_app import FrestqApp
FrestqApp.process_parser = process_parser
from frestq.app import *
pargs = app.pargs
app.configure_app(config_object=__name__)

if pargs.list:
    target_pargs = parser.parse_args(["--tasks", "--filters", "task_type=external", "status=executing"])
    tasks = get_tasks(target_pargs)
    print_task_list(tasks)
elif pargs.allow_disjoint_multiple_tallies and pargs.election_id:
    allow_disjoint_multiple_tallies(pargs.election_id)
elif pargs.disallow_disjoint_multiple_tallies and pargs.election_id:
    disallow_disjoint_multiple_tallies(pargs.election_id)
elif pargs.reset_tally and pargs.election_id:
    print("reset_tally")
    reset_tally(pargs.election_id)
elif pargs.show:
    target_pargs = parser.parse_args(["--show-external", pargs.show])
    tasks = get_external_task(target_pargs)
    if not tasks:
        print "task %s not found" % pargs.show
    else:
        task = tasks[0]
        print_task(task)
elif pargs.show_full:
    target_pargs = parser.parse_args(["--show-external", pargs.show_full])
    tasks = get_external_task(target_pargs)
    if not tasks:
        print "task %s not found" % pargs.show
    else:
        task = tasks[0]
        print(json.dumps(tasks[0].input_data, indent=4))
elif pargs.accept:
    target_pargs = parser.parse_args(["--finish", pargs.accept, '{"status": "accepted"}'])
    finish_task(target_pargs)
elif pargs.reject:
    target_pargs = parser.parse_args(["--finish", pargs.reject, '{"status": "denied"}'])
    finish_task(target_pargs)
else:
    parser.print_help()
