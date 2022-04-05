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

import collections

def edges2simpletree(edges):
    '''
    Converts a list of edges in the form [(parent, child), (parent, child), ..]
    to a tree based on dicts

    Exaple:

    edges = [[1,2], [4,5], [3,4], [1,3], [1, None], [7, None]]
    print(json.dumps(edges2simpletree(edges), indent=1))

    prints:
    {
      "1": {
        "2": {},
        "3": {
          "4": {
            "5": {}
          }
        }
      },
      "7": {}
    }
    '''
    trees = collections.defaultdict(dict)

    for parent, child in edges:
        if child not in [None, '']:
          trees[parent][child] = trees[child]

    if len(edges) == 0:
        return {}

    parents, children = zip(*edges)
    roots = set(parents).difference(children)

    return {root: trees[root] for root in roots}

def get_list(tree, list_func):
    '''
    convenience function to call to the recursive functions list_edges,
    list_leaves or list_all without having to supply an empty base list of edges
    yourself.
    '''
    l = []
    list_func(tree, l)
    return l

def list_edges(tree, edges):
    '''
    Given a tree, traverses it and returns a list with the items that are not
    leaves, i.e. edges with at least one child.
    '''
    for key, val in tree.items():
        if len(val) > 0:
            edges.append(key)
            list_edges(val, edges)

def list_leaves(tree, edges):
    '''
    Given a tree, traverses it and returns a list with the items that are
    leaves, i.e. edges with no children.
    '''
    for key, val in tree.items():
        if len(val) == 0:
            edges.append(key)
        else:
            list_leaves(val, edges)

def list_all(tree, edges):
    '''
    Given a tree, return a list with all the leaves and edges
    '''
    for key, val in tree.items():
        edges.append(key)
        list_all(val, edges)

def get_ancestors(tree, edge, ancestors=[]):
    '''
    Given a tree and an edge, returns a list with the ancestors. The list is
    sorted so that the first ancestor is the root (no parent).
    '''
    for key, val in tree.items():
        if key == edge:
            return ancestors
        else:
            final_ancestors = get_ancestors(val, edge, ancestors + [key])
            if len(final_ancestors) > 0:
                return final_ancestors
    return []
