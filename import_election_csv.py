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
import csv
import os
import copy
import operator
import argparse
from datetime import datetime, timedelta

from utils.csvblocks import csv_to_blocks
from utils.json import serialize

BASE_ELECTION = {
    "id": -1,
    "title": "",
    "description": "",
    "layout": "",
    "presentation": {
        "share_text": "",
        "theme": 'default',
        "urls": [],
        "theme_css": ""
    },
    "end_date": "",
    "start_date": "",
    "questions": []
}

BASE_QUESTION = {
    "description": "",
    "layout": 'simple',
    "max": 1,
    "min": 0,
    "num_winners": 1,
    "title": "",
    "randomize_answer_order": True,
    "tally_type": "plurality-at-large",
    "answer_total_votes_percentage": "over-total-votes",
    "answers": []
}

BASE_ANSWER = {
    "id": -1,
    "category": '',
    "details": "",
    "sort_order": -1,
    "urls": [],
    "text": ""
}

def blocks_to_election(blocks, config, add_to_id=0):
    '''
    Parses a list of blocks into an election
    '''

    # convert blocks into a more convenient structure
    election = blocks[0]['values']
    blocks.pop(0)
    questions = []
    for question, options in zip(blocks[0::2], blocks[1::2]):
        q = question['values']
        q['options'] = options['values']

        data = {
            "description": q["Description"],
            "layout": q.get("Layout", 'simple'),
            "max": int(q["Maximum choices"]),
            "min": int(q["Minimum choices"]),
            "num_winners": int(q["Number of winners"]),
            "title": q["Title"],
            "randomize_answer_order": q["Randomize options order"] == "TRUE",
            "tally_type": q.get("Voting system", "plurality-at-large"),
            "answer_total_votes_percentage": q["Totals"],
            "answers": [
              {
                  "id": int(answer["Id"]),
                  "category": answer.get("Category", ''),
                  "details": "",
                  "sort_order": index,
                  "urls": [],
                  "text": answer['Text'],
              }
              for answer, index in zip(q['options'], range(len(q['options'])))
              if len("".join(answer.values())) > 0
            ]
        }
        # check answers
        assert len(data['answers']) == len(set(map(operator.itemgetter('text'), data['answers'])))
        data['max'] = min(data['max'], len(data['answers']))
        data['num_winners'] = min(data['num_winners'], len(data['answers']))
        for answ in data['answers']:
            try:
               assert answ['id'] == answ['sort_order']
            except:
               print(answ)


        questions.append(data)


    start_date = datetime.strptime(election["Start date time"], "%d/%m/%Y %H:%M:%S")
    ret = config
    ret.update({
        "id": int(election['Id']) + add_to_id,
        "title": election['Title'],
        "description": election['Description'],
        "layout": election.get('Layout', ''),
        "presentation": {
            "share_text": election.get('Share Text', ''),
            "theme": election.get('Theme', 'default'),
            "urls": [],
            "theme_css": ""
        },
        "end_date": (start_date + timedelta(hours=int(election['Duration in hours']))).isoformat() + ".001",
        "start_date": start_date.isoformat() + ".001",
        "questions": questions
    })
    return ret

def form_to_elections(path, separator, config, add_to_id):
    '''
    Converts the google forms into election configurations
    '''
    election_funcs = {
        "Título": lambda d: ["title", d],
        "Descripción": lambda d: ["descripcion", d],
        "Comienzo": lambda d: ["start_date", datetime.strptime(d, "%m/%d/%Y %H:%M:%S").isoformat()+ ".001"],
        "Final": lambda d: ["end_date", datetime.strptime(d, "%m/%d/%Y %H:%M:%S").isoformat()+ ".001"],
    }
    census_key = "Censo"
    more_keys = {
        "¿Más preguntas?": lambda v: "No" not in v
    }
    question_options_key = "Opciones"
    question_funcs = {
        "Título": lambda d: ["title", d],
        "Descripción": lambda d: ["description", d],
        "Número de ganadores": lambda d: ["num_winners", int(d)],
        "Número máximo de opciones": lambda d: ["max", int(d)],
        "Número mínimo de opciones": lambda d: ["min", int(d)],
        "Orden aleatorio": lambda d: ["randomize_answer_order", d == "Aleatorio"],
        "Resultados":  lambda d: ["answer_total_votes_percentage", "over-total-votes" if d == "Sobre votos totales" else "over-total-valid-votes"]
    }

    elections = []
    with open(path, mode='r', encoding="utf-8", errors='strict') as f:
        fcsv = csv.reader(f, delimiter=',', quotechar='"')
        keys = fcsv.__next__()
        for values in fcsv:
            if len(values) == 0:
                continue

            question_num = -1
            election = copy.deepcopy(BASE_ELECTION)
            election['id'] = add_to_id + len(elections)
            question = None

            for key, value, index in zip(keys, values, range(len(values))):
                if question_num == -1 and key not in more_keys.keys() and key in election_funcs.keys():
                    dest_key, dest_value =  election_funcs[key](value)
                    election[dest_key] = dest_value
                elif key == census_key:
                    election['census'] = value.split("\n")
                    question_num += 1
                    question = copy.deepcopy(BASE_QUESTION)
                elif question_num >= 0 and key in question_funcs.keys():
                    dest_key, dest_value =  question_funcs[key](value)
                    question[dest_key] = dest_value
                elif question_num >= 0 and key == question_options_key:
                    options = value.strip().split("\n")
                    question['answers'] = [{
                        "id": opt_id,
                        "category": '',
                        "details": '',
                        "sort_order": opt_id,
                        "urls": [],
                        "text": opt
                    }
                    for opt, opt_id in zip(options, range(len(options)))]
                elif question_num >= 0 and key in more_keys.keys():
                    question_num += 1
                    election['questions'].append(question)
                    question = copy.deepcopy(BASE_QUESTION)

                    if not more_keys[key](value):
                        elections.append(election)
                        break
    return elections

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts a CSV into the json to create an election.')
    parser.add_argument('-c', '--config-path', help='default config for the election')
    parser.add_argument('-i', '--input-path', help='input file or directory')
    parser.add_argument('-o', '--output-path', help='output file or directory')
    parser.add_argument('-a', '--add-to-id', type=int, help='add an int number to the id', default=0)
    parser.add_argument(
        '-f', '--format',
        choices=['tsv-blocks', 'csv-google-forms'],
        default="tsv-blocks",
        help='output file or directory')


    args = parser.parse_args()

    if not os.access(args.input_path, os.R_OK):
      print("can't read %s" % args.input_path)
      exit(2)
    if os.path.isdir(args.output_path) and not os.access(args.output_path, os.W_OK):
      print("can't write to %s" % args.output_path)
      exit(2)
    if not os.access(args.config_path, os.R_OK):
      print("can't read %s" % args.config_path)
      exit(2)

    config = None
    with open(args.config_path, mode='r', encoding="utf-8", errors='strict') as f:
        config = json.loads(f.read())

    if os.path.isdir(args.input_path) and os.path.isdir(args.output_path):
        for fname in os.listdir(args.input_path):
            full_path = os.path.join(args.input_path, fname)
            if os.path.isdir(full_path):
                continue

            try:
                blocks = csv_to_blocks(path=full_path, separator="\t")
                election = blocks_to_election(blocks, config, args.add_to_id)
                fname = fname.replace(str(election["id"] - args.add_to_id), str(election["id"]))
            except:
                print("malformed CSV, %s" % fname)
                import traceback
                traceback.print_exc()
                continue

            with open(
                    os.path.join(args.output_path, fname.replace(".tsv", ".config.json")),
                    mode='w',
                    encoding="utf-8",
                    errors='strict') as f:
                f.write(serialize(election))

            if config.get('agora_results_config', None) is not None:
                with open(
                        os.path.join(args.output_path, fname.replace(".tsv", ".config.results.json")),
                        mode='w',
                        encoding="utf-8",
                        errors='strict') as f:
                    f.write(serialize(config['agora_results_config']))
    else:

        try:
            if args.format == "tsv-blocks":
                blocks = csv_to_blocks(path=args.input_path, separator="\t")
                election = blocks_to_election(blocks, config, args.add_to_id)

                print(serialize(election))

                with open(args.output_path, mode='w', encoding="utf-8", errors='strict') as f:
                    f.write(serialize(election))
            else:
                if not os.path.isdir(args.output_path):
                    print("output path must be a directory")
                    exit(2)

                elections = form_to_elections(path=args.input_path,
                                              separator="\t",
                                              config=config,
                                              add_to_id=args.add_to_id)
                for election in elections:
                    fpath = os.path.join(args.output_path, "%d.census.json" % election["id"])
                    with open(fpath, mode='w', encoding="utf-8", errors='strict') as f:
                        f.write(serialize(election['census']))
                    del election['census']

                    fpath = os.path.join(args.output_path, "%d.json" % election["id"])
                    with open(fpath, mode='w', encoding="utf-8", errors='strict') as f:
                        f.write(serialize(election))
        except:
            print("malformed CSV")
            import traceback
            traceback.print_exc()
            exit(3)
