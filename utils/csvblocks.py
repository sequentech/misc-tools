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

import os
try:
  from json_serialize import serialize
except:
  from utils.json_serialize import serialize
import csv
import argparse

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
        fcsv = csv.reader(f, delimiter=separator, quotechar='"')
        for line_number, orig_values in enumerate(fcsv, start = 1):
            # get values
            # to be safe, append some extra elements to the end of the list
            values = orig_values + ["" for _ in range(10)]
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
                        if 0 == len(str(values[1])):
                            print("WARNING: Empty form value for key %s at line %i" \
                                % (key, line_number))
                            print("         Line values: " + str(orig_values))
                elif current_block['type'] == "Table":
                    if headers == None:
                        # as we addeed some extra empty elements to the values,
                        # we use here split again
                        headers = orig_values
                    else:
                        for vindex, zipped_value in enumerate(zip(headers, values), start=1):
                            key = zipped_value[0]
                            value = zipped_value[1]
                            if len(key.strip()) > 0 and 0 == len(str(value)):
                                print("WARNING: Empty table value for key %s at line %i, table index %i" \
                                    % (key, line_number, vindex))
                                print("         Line values: " + str(orig_values))
                        current_block['values'].append(
                          dict((key.strip(), value)
                              for key, value in zip(headers, values) if len(key.strip()) > 0))

        if current_block is not None:
            ret.append(current_block)
        return ret

def __inc_eids(blocks, args):
    '''
    Increments election id
    '''
    blocks[0]['Id'] = str(int(blocks[0]['Id'])+args.inc)

def __custom(blocks, args):
    '''
    Executes a custom function, write it here
    '''
    pass

def blocks_to_json_file(path, blocks, args):
    '''
    Save some blocks to a json file
    '''
    path = path.replace(".csv", ".json")

    if args.verbose:
        print("saving %s" % path)

    with open(path, mode='w', encoding="utf-8", errors='strict') as f:
        f.write(serialize(blocks))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Applies changes to csv-block files or export it to json.')

    parser.add_argument('action',
        choices=[
          #'inc-eids',
          #'custom',
          'json-export'],
        help='action to execute')
    parser.add_argument('directory',
        type=str, help='directory containing the csv-block files')

    parser.add_argument('-v', '--verbose', help='be verbose',
        action='store_true')
    parser.add_argument('-s', '--separator',
        type=str, help='csv separator character', default=',')
    #parser.add_argument('--inc', type=int, default=1,
        #help=('Specifies how much should the id of the election be increased.' +
            #'Used together action "inc-eids"'))

    args = parser.parse_args()

    # directory should exist
    if not os.path.isdir(args.directory) or not os.access(args.directory, os.R_OK):
        print("directory doesn't exist or can't be read: %s" % args.directory)
        exit(2)

    # list files with read and write permissions on the directory
    files = sorted([name for name in os.listdir(args.directory)
        if os.path.isfile(os.path.join(args.directory, name)) and\
            os.access(args.directory, os.R_OK|os.W_OK)])

    # process each of the files with the specified action function and
    # overwrite it
    for name in files:
        file_path = os.path.join(args.directory, name)
        if not file_path.endswith("csv"):
            continue

        if args.verbose:
            print("processing %s" % name)

        blocks = csv_to_blocks(path=file_path, separator=args.separator)
        if args.action == 'json-export':
            blocks_to_json_file(path=file_path, blocks=blocks, args=args)
        #elif args.action in ['inc-eids', 'custom']:
            #{
              #"inc-eids": __inc_eids,
              #"custom": __custom
            #}[args.action](blocks, args)
            #blocks_to_csv_file(path=file_path, separator=args.separator, blocks=blocks)
