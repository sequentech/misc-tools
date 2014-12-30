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
