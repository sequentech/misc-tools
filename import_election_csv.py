#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of agora-api.
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
import copy
import sys
import codecs
import re
import os
import operator
import argparse
from datetime import datetime, timedelta


def csv_to_blocks(path, separator=",", strip_values=True):
    '''
    Converts a CSV file into a list of dictionaries provided that the CSV
    follows a specific format. The output is a list of blocks such that:

    - Blocks are separated by lines that start with the separator character
    - There are different kinds of blocks:
       1. Forms. The first line of a block has a title that starts with '#'.
          In the following lines, the first field is the key and the other
          fields are the values.

          CSV Example:

          #Some Title
          Some Key,Some value
          Other Key,Some other value

          That will be converted into a dictionary:
          {
            "type": "Form",
            "title": "Some Title",
            values: {
              "Some Key": "Some value",
              "Other key": "Some other value"
            }
          }

       2. Tables. The first line of a black has a title that starts with '@'.
          The second line has the column header titles, and the following lines
          are the rows.


          CSV Example:

          @Table Title
          Name,Date,Description,Other column
          Foo,12/12/12,Whatever,
          Bar,,yeah,things

          That will be converted into a dictionary:
          {
            "type": "Table",
            "title": "Table Title",
            "values": [
              {
                "Name": "Foo",
                "Date": "12/12/12",
                "Description": "Whatever",
                "Other column": ""
              },
              {
                "Name": "Bar",
                "Date": "",
                "Description": "yeah",
                "Other column": "things"
              },
            ]
          }
    '''
    ret = []
    current_block = None
    new_block_flag = True
    headers = None

    with open(path, mode='r', encoding="utf-8", errors='strict') as f:
        # main loop
        for line in f:
            # get values
            # to be safe, append some extra elements to the end of the list
            values = line.split(separator) + ["" for _ in range(10)]
            if strip_values:
                values = [val.strip() for val in values]


            # check for new blocks
            if new_block_flag:
                title = values[0]
                if title.startswith("#"):
                  new_block_flag = False
                  if current_block is not None:
                      ret.append(current_block)

                  current_block = dict(
                    type="Form",
                    title=title[1:],
                    values=dict()
                  )

                elif title.startswith("@"):
                  headers = None
                  new_block_flag = False
                  if current_block is not None:
                      ret.append(current_block)

                  current_block = dict(
                    type="Table",
                    title=title[1:],
                    values=[]
                  )

            # set new block flag if needed
            elif len(list(filter(lambda x: len(x) != 0, values))) == 0:
                new_block_flag = True

            # process blocks
            elif current_block is not None:
                if current_block["type"] == "Form":
                    key = values[0].strip()
                    if len(key) != 0:
                        current_block['values'][key] = values[1]
                elif current_block['type'] == "Table":
                    if headers == None:
                        # as we addeed some extra empty elements to the values,
                        # we use here split again
                        headers = line.split(separator)
                    else:
                        current_block['values'].append(
                          dict((key.strip(), value)
                              for key, value in zip(headers, values) if len(key.strip()) > 0))

        if current_block is not None:
            ret.append(current_block)
        return ret

def serialize(data):
    return json.dumps(data,
        indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))

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
            "layout": q["Layout"],
            "max": int(q["Maximum choices"]),
            "min": int(q["Minimum choices"]),
            "num_winners": int(q["Number of winners"]),
            "title": q["Title"],
            "randomize_answer_order": q["Randomize options order"] == "TRUE",
            "tally_type": q["Voting system"],
            "answer_total_votes_percentage": q["Totals"],
            "answers": [
              {
                  "id": int(answer["Id"]),
                  "category": answer["Category"],
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
            assert answ['id'] == answ['sort_order']

        questions.append(data)


    start_date = datetime.strptime(election["Start date time"], "%d/%m/%Y %H:%M")
    ret = config
    ret.update({
        "id": int(election['Id']) + add_to_id,
        "title": election['Title'],
        "description": election['Description'],
        "layout": election['Layout'],
        "presentation": {
            "share_text": election['Share Text'],
            "theme": election['Theme'],
            "urls": [],
            "theme_css": ""
        },
        "end_date": (start_date + timedelta(hours=int(election['Duration in hours']))).isoformat() + ".001",
        "start_date": start_date.isoformat() + ".001",
        "questions": questions
    })
    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts a CSV into the json to create an election.')
    parser.add_argument('-c', '--config-path', help='default config for the election')
    parser.add_argument('-i', '--input-path', help='input file or directory')
    parser.add_argument('-o', '--output-path', help='output file or directory')
    parser.add_argument('-a', '--add-to-id', type=int, help='add an int number to the id')

    args = parser.parse_args()

    if not os.access(args.input_path, os.R_OK):
      print("can't read %s" % args.input_path)
      exit(2)
    if not os.access(args.output_path, os.W_OK):
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

            blocks = csv_to_blocks(path=full_path, separator="\t")
            try:
                election = blocks_to_election(blocks, config, args.add_to_id)
                fname = fname.replace(str(election["id"] - args.add_to_id), str(election["id"]))
            except:
                print("malformed CSV")
                import traceback
                traceback.print_exc()

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
        blocks = csv_to_blocks(path=args.input_path, separator="\t")

        print(serialize(blocks))

        try:
            election = blocks_to_election(blocks, config)
        except:
            print("malformed CSV")
            import traceback
            traceback.print_exc()
            exit(3)

        print(serialize(election))

        with open(args.output_path, mode='w', encoding="utf-8", errors='strict') as f:
            f.write(serialize(election))
