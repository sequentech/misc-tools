# -*- coding: utf-8 -*-
#
# This file is part of agora-tools.
# Copyright (C) 2014-2016  Agora Voting SL <agora@agoravoting.com>

# agora-tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tools  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tools.  If not, see <http://www.gnu.org/licenses/>.

def map_question_maximums_and_winners(election_config, election_id, ancestors,
    mapping, **kwargs):
    '''
    given an election config, checks that the mapping has been applied
    '''
    from_list, to_list = zip(*mapping)
    reverse_mapping = [(b, a) for a, b in mapping]
    reverse_mapping_dict = dict(reverse_mapping)
    first_election_id = ancestors[0]
    for question in election_config['questions']:
        # if this is a question susceptible to have been changed, add the
        # size changes
        if question['max'] not in to_list:
            continue

        if 'modified_sizes' not in question:
            question['modified_sizes'] = dict()
            election_config['max_winners_mapping'] = mapping

        modified_sizes = question['modified_sizes']
        max_size = max(question['max'], reverse_mapping_dict[question['max']])
        if first_election_id in modified_sizes:
          max_size = max(max_size, modified_sizes[first_election_id][1])
        modified_sizes[first_election_id] = [question['min'], max_size]
