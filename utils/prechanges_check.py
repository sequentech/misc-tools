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

def map_question_maximums_and_winners(election_config, election_id, mapping):
    '''
    given an election config, checks that the mapping has been applied
    '''
    from_list, to_list = zip(*mapping)
    for question in election_config['questions']:
        try:
            assert question['max'] not in from_list
            assert question['num_winners'] not in from_list
        except:
            print("ERROR: election id = %s question '%s' has max = %d & num_winners = %d" % (
                election_id, question['title'], question['max'], question['num_winners']))
