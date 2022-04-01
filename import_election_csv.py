#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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

import json
import csv
import os
import copy
import operator
import argparse
from datetime import datetime, timedelta

from utils.csvblocks import csv_to_blocks
from utils.json_serialize import serialize


def iget(d, key, default):
    '''
    Ignore-case get

    This function makes a dict.get but there's no need for the key to be
    exactly the same as the key in the dict. Before the real **get** we
    look into the dict keys and find for this key ignoring the case so the
    key param can differ from the dict key in lower or upper cases.

    :param d: this is the dict to search in
    :param key: this is the key to search
    :param default: this is the default value to return if key isn't in the
    dict
    '''

    real_key = key
    keyl = key.lower()
    for k in d.keys():
        if k.lower() == keyl:
            real_key = k
    return d.get(real_key, default)


BASE_ELECTION = {
    "id": -1,
    "title": "",
    "description": "",
    "layout": "",
    "presentation": {
        "share_text": [
        {
          "network": "Twitter",
          "button_text": "",
          "social_message": "I have just voted in election __URL__, you can too! #sequent"
        },
        {
          "network": "Facebook",
          "button_text": "",
          "social_message": "__URL__"
        }
      ],
        "theme": 'default',
        "urls": [],
        "theme_css": "",
        "extra_options": {}
    },
    "end_date": "",
    "start_date": "",
    "real": True,
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
    "extra_options": {},
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

def parse_int(s):
    return int(s)

def parse_list(s):
    return s.split(",")

def parse_bool(s):
    return s == "TRUE"

def parse_extra(q):
  val = dict(
      (key.replace("extra: ", ""), value)
      for key, value in q.items() if key.startswith("extra: ")
  )
  if "success_screen__hide_download_ballot_ticket" in val:
      val["success_screen__hide_download_ballot_ticket"] = parse_bool(
          val["success_screen__hide_download_ballot_ticket"]
      )
  if "shuffle_category_list" in val:
      val["shuffle_category_list"] = parse_list(val["shuffle_category_list"])
  if "shuffle_categories" in val:
      val["shuffle_categories"] = parse_bool(val["shuffle_categories"])
  if "shuffle_all_options" in val:
      val["shuffle_all_options"] = parse_bool(val["shuffle_all_options"])
  if "select_all_category_clicks" in val:
      val["select_all_category_clicks"] = parse_int(val["select_all_category_clicks"])
  if "answer_group_columns_size" in val:
      val["answer_group_columns_size"] = parse_int(val["answer_group_columns_size"])
  if "answer_columns_size" in val:
      val["answer_columns_size"] = parse_int(val["answer_columns_size"])

  return val

def blocks_to_election(blocks, config, add_to_id=0):
    '''
    Parses a list of blocks into an election
    '''

    # convert blocks into a more convenient structure
    election = blocks[0]['values']

    blocks.pop(0)
    questions = []

    def get_answer_id(answer):
        return answer['Id']

    def get_description(answer):
        return answer.get('Description', '').replace('\n', '<br/>')

    def get_url(key, value):
        if key in ['Gender', 'Tag', 'Support']:
            return "https://sequentech.io/api/%s/%s" % (key.lower(), value)
        elif value.startswith('http://') or value.startswith('https://'):
            return value.strip()

        return key + value.strip()

    for question, options in zip(blocks[0::2], blocks[1::2]):
        q = question['values']
        q['options'] = options['values']

        data = {
            "description": q.get("Description", ''),
            "layout": q.get("Layout", 'simple'),
            "max": int(q["Maximum choices"]),
            "min": int(q["Minimum choices"]),
            "num_winners": int(q["Number of winners"]),
            "title": q["Title"],
            "randomize_answer_order": parse_bool(q.get("Randomize options order", False)),
            "tally_type": q.get("Voting system", "plurality-at-large"),
            "answer_total_votes_percentage": q["Totals"],
            "extra_options": parse_extra(q),
            "answers": [
              {
                  "id": int(get_answer_id(answer)),
                  "category": answer.get("Category", ''),
                  "details": get_description(answer),
                  "sort_order": index,
                  "urls": [
                      {
                        'title': url_key,
                        'url': get_url(url_key, url_val)
                      }
                      for url_key, url_val in answer.items()
                      if url_key in ['Image URL', 'URL', 'Gender', 'Tag', 'Support'] and\
                          len(url_val.strip()) > 0
                  ],
                  "text": answer['Text'],
              }
              for answer, index in zip(q['options'], range(len(q['options'])))
              if len("".join(answer.values()).strip()) > 0
            ]
        }

        # check answers
        try:
          assert len(data['answers']) == len(set(list(map(operator.itemgetter('text'), data['answers']))))
        except Exception as e:
          print("duplicated options in question '%s':" % q["Title"])
          l = list(map(operator.itemgetter('text'), data['answers']))
          print(set([x for x in l if l.count(x) > 1]))
          raise e
        data['max'] = min(data['max'], len(data['answers']))
        data['num_winners'] = min(data['num_winners'], len(data['answers']))
        for answ in data['answers']:
            try:
               assert answ['id'] == answ['sort_order']
            except:
               print(answ)


        questions.append(data)

    def get_def(dictionary, key, default_value):
        if key not in dictionary or len(dictionary[key]) == 0:
            return default_value

        return dictionary[key]

    start_date = datetime.strptime("10/10/2015 10:10", "%d/%m/%Y %H:%M")
    if len(election["Start date time"]) > 0:
        try:
            start_date = datetime.strptime(election["Start date time"], "%d/%m/%Y %H:%M:%S")
        except:
            start_date = datetime.strptime(election["Start date time"], "%d/%m/%Y %H:%M")

    ret = {
        "id": int(election['Id']) + add_to_id,
        "authorities": config['authorities'],
        "director": config['director'],
        "title": election['Title'],
        "description": election['Description'],
        "layout": election.get('Layout', ''),
        "presentation": {
            "share_text": [
              {
                "network": "Twitter",
                "button_text": "",
                "social_message": election.get('Share Text', '')
              },
              {
                "network": "Facebook",
                "button_text": "",
                "social_message": "__URL__"
              }
            ],
            "theme": election.get('Theme', 'default'),
            "urls": [],
            "theme_css": "",
            "extra_options": parse_extra(election),
            "show_login_link_on_home": parse_bool(iget(election, 'login link on home', False)),
        },
        "end_date": (start_date + timedelta(hours=int(get_def(election, 'Duration in hours', '24')))).isoformat() + ".001",
        "start_date": start_date.isoformat() + ".001",
        "questions": questions,
        "real": True
    }
    return ret

def form_to_elections(path, separator, config, add_to_id):
    '''
    Converts the google forms into election configurations
    '''
    election_funcs = {
        "Título": lambda d: ["title", d],
        "Descripción": lambda d: ["description", d],
        "Comienzo": lambda d: ["start_date", datetime.strptime(d, "%m/%d/%Y %H:%M:%S").isoformat()+ ".001"],
        "Final": lambda d: ["end_date", datetime.strptime(d, "%m/%d/%Y %H:%M:%S").isoformat()+ ".001"],
    }
    census_key = "Censo"
    more_keys = {
        "¿Más preguntas?": lambda v: "No" not in v
    }
    auth_method = config['iam']['event_config']['auth_method']
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
    base_election = copy.deepcopy(BASE_ELECTION)
    base_election['director'] = config['director']
    base_election['authorities'] = config['authorities']
    with open(path, mode='r', encoding="utf-8", errors='strict') as f:
        fcsv = csv.reader(f, delimiter=',', quotechar='"')
        keys = fcsv.__next__()
        for values in fcsv:
            if len(values) == 0:
                continue

            question_num = -1
            election = copy.deepcopy(base_election)
            election['id'] = add_to_id + len(elections)
            question = None

            for key, value, index in zip(keys, values, range(len(values))):
                if question_num == -1 and key not in more_keys.keys() and key in election_funcs.keys():
                    dest_key, dest_value =  election_funcs[key](value)
                    election[dest_key] = dest_value
                elif key == census_key:
                    if auth_method == "sms":
                        election['census'] = [{"tlf": item} for item in value.split("\n")]
                    else: # email
                        election['census'] = [{"email": item} for item in value.split("\n")]
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
    parser.add_argument('-A', '--admin-format', help='use create format for sequent-admin instead of ballot-box', action="store_true")
    parser.add_argument('-a', '--add-to-id', type=int, help='add an int number to the id', default=0)
    parser.add_argument(
        '-f', '--format',
        choices=['csv-blocks', 'tsv-blocks', 'csv-google-forms'],
        default="csv-blocks",
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

    try:
        if args.format == "csv-blocks" or args.format == "tsv-blocks":
            separator = {
              "csv-blocks": ",",
              "tsv-blocks": "\t"
            }[args.format]
            extension = {
              "csv-blocks": ".csv",
              "tsv-blocks": ".tsv"
            }[args.format]

            if os.path.isdir(args.input_path):
                if not os.path.exists(args.output_path):
                    os.makedirs(args.output_path)
                i = 0
                files = sorted([name for name in os.listdir(args.input_path)
                            if os.path.isfile(os.path.join(args.input_path, name)) and name.endswith(extension)])
                for name in files:
                    print("importing %s" % name)
                    file_path = os.path.join(args.input_path, name)
                    blocks = csv_to_blocks(path=file_path, separator=separator)
                    election = blocks_to_election(blocks, config, args.add_to_id)
                    
                    if str(election['id']) + extension != name:
                        print("WARNING: election id %i doesn't match filename %s" % (election['id'], name))

                    if not args.admin_format:
                        output_path = os.path.join(args.output_path, str(election['id']) + ".config.json")
                    else:
                        output_path = os.path.join(args.output_path, str(i) + ".json")
                        auth_config_path = os.path.join(args.output_path, str(i) + ".config.json")
                        auth_config = config['iam']['event_config']
                        with open(auth_config_path, mode='w', encoding="utf-8", errors='strict') as f:
                            f.write(serialize(auth_config))

                        auth_census_path = os.path.join(args.output_path, str(i) + ".census.json")
                        census_config = config['iam'].get('census_data', [])
                        with open(auth_census_path, mode='w', encoding="utf-8", errors='strict') as f:
                            f.write(serialize(census_config))


                    with open(output_path, mode='w', encoding="utf-8", errors='strict') as f:
                        f.write(serialize(election))

                    if config.get('tally_pipes_config', None) is not None:
                        if not args.admin_format:
                            results_conf_path = os.path.join(args.output_path, str(election['id']) + ".config.results.json")
                        else:
                            results_conf_path = os.path.join(args.output_path, str(i) + ".config.results.json")
                        with open(
                                results_conf_path,
                                mode='w',
                                encoding="utf-8",
                                errors='strict') as f:
                            f.write(serialize(
                                dict(
                                    version="1.0",
                                    pipes=config['tally_pipes_config']
                                )
                            ))
                    i += 1
            else:
                blocks = csv_to_blocks(path=args.input_path, separator=separator)
                election = blocks_to_election(blocks, config, args.add_to_id)

                if str(election['id']) + extension != os.path.basename(args.input_path):
                    print("WARNING: election id %i doesn't match filename %s" % (election['id'], os.path.basename(args.input_path)))

                with open(args.output_path, mode='w', encoding="utf-8", errors='strict') as f:
                    f.write(serialize(election))
        else:
            if not os.path.exists(args.output_path):
                os.makedirs(args.output_path)
            elif not os.path.isdir(args.output_path):
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

                fpath = os.path.join(args.output_path, "%d.config.json" % election["id"])
                with open(fpath, mode='w', encoding="utf-8", errors='strict') as f:
                    f.write(serialize(config['iam']['event_config']))
    except:
        print("malformed CSV")
        import traceback
        traceback.print_exc()
        exit(3)
