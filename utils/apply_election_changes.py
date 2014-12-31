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

def change_question_max(change, election_config, **kwargs):
    '''
    changes the question max and number of winners for a given question.
    Doesn't entail a new election_id
    '''
    question_num = int(change['question_number'].strip())
    new_question_max = int(change['new_question_max'].strip())

    question = election_config['questions'][question_num]
    question['max'] = question['num_winners'] = new_question_max

def remove_candidate(change, election_config, **kwargs):
    '''
    Removes a candidate, shifting all the other candidates. Entails a new
    election_id
    '''
    election_id = int(change['election_id'].strip())
    question_num = int(change['question_number'].strip())
    candidature_id = int(change['candidature_id'].strip())
    new_candidature_text = change['new_candidature_text'].strip()
    new_candidature_category = change['new_candidature_category'].strip()

    question = election_config['questions'][question_num]
    # create a copy to be able to remove elements in the list while looping
    answer_list_copy = question['answers'][:]
    found = False
    for answer in answer_list_copy:
        if not found and answer['id'] == candidature_id:
            # check for safety
            try:
                assert answer['text'] == new_candidature_text
            except:
                print("remove_candidate: candidate(%d) in question(%s) in election(%d) found with category = '%s' instead of '%s'" % (
                    candidature_id, question['title'], election_id, answer['text'], new_candidature_text))
                return
            try:
                assert answer['category'] == new_candidature_category
            except:
                print("remove_candidate: candidate(%d) in question(%s) in election(%d) found with text = '%s' instead of '%s'" % (
                    candidature_id, question['title'], election_id, answer['text'], new_candidature_text))
                return
            found = True
            question['answers'].remove(answer)
        elif found:
            answer['id'] = answer['id'] - 1
            answer['sort_order'] = answer['sort_order'] - 1

    if not found:
        print("remove_candidate: candidate(%d) in question(%s) in election(%d) not found" % (
            candidature_id, question['title'], election_id))

def add_candidate(change, election_config, **kwargs):
    '''
    Adds a candidate with a certain id, shifting all the existing candidates with
    ids that are equal or bigger.
    '''

    election_id = int(change['election_id'].strip())
    question_num = int(change['question_number'].strip())
    new_candidature_id = int(change['new_candidature_id'].strip())
    new_candidature_text = change['new_candidature_text'].strip()
    new_candidature_category = change['new_candidature_category'].strip()

    question = election_config['questions'][question_num]
    # create a copy to be able to remove elements in the list while looping
    answer_list_copy = question['answers'][:]
    if new_candidature_id > len(answer_list_copy):
        print("add_candidate: new_candidature_id > len(answer_list_copy) [%d > %d] in election(%d)" % (
            new_candidature_id, len(answer_list_copy), election_id))
        return

    new_answ = {
        "category": new_candidature_category,
        "details": "",
        "id": new_candidature_id,
        "sort_order": new_candidature_id,
        "text": new_candidature_text,
        "urls": []
    }

    pos = None
    for answer in answer_list_copy:
        if pos is None and answer['id'] == new_candidature_id:
            pos = question['answers'].index(answer)
            answer['id'] = answer['id'] + 1
            answer['sort_order'] = answer['sort_order'] + 1
        elif pos is not None:
            answer['id'] = answer['id'] + 1
            answer['sort_order'] = answer['sort_order'] + 1

    # if pos is not found, must be an append
    if pos is None:
        assert new_candidature_id == len(answer_list_copy)
        pos = len(answer_list_copy)

    question['answers'].insert(pos, new_answ)

def change_category(change, election_config, **kwargs):
    '''
    Change the category of a set of candidates. New election neeed.
    '''
    election_id = int(change['election_id'].strip())
    question_num = int(change['question_number'].strip())
    new_candidature_category = change['new_candidature_category'].strip()

    # a dictonary with the keys being the affected candidate ids and the values
    # the status (if the candidature has been found and fixed or not, False by
    # default)
    candidatures_found_status = dict([
      (int(i.strip()), False)
      for i in change['candidature_id'].strip().split(',')])

    question = election_config['questions'][question_num]
    # create a copy to be able to remove elements in the list while looping
    answer_list_copy = question['answers'][:]

    for answer in answer_list_copy:
        if answer['id'] in candidatures_found_status.keys():
            answer['category'] = new_candidature_category
            candidatures_found_status[answer['id']] = True

    for cand_id, found in candidatures_found_status.items():
        if not found:
            print("change_category: candidate(%d) in question(%s) in election(%d) not found" % (
                cand_id, question['title'], election_id))

def add_question(change, election_config, **kwargs):
    '''
    adds a new question to the election at the end of the list of questions
    '''

    election_id = int(change['election_id'].strip())
    pos = int(change['question_number'].strip())
    election_config['questions'].insert(pos, {
        "answer_total_votes_percentage": change['new_question_answer_total_votes_percentage'].strip(),
        "answers": [],
        "description": change['new_question_description'].strip(),
        "layout": change['new_question_layout'].strip(),
        "max": int(change['new_question_max'].strip()),
        "min": int(change['new_question_min'].strip()),
        "num_winners": int(change['new_question_num_winners'].strip()),
        "randomize_answer_order": change['new_question_randomize_answer_order'].strip() == 'TRUE',
        "tally_type": change['new_question_tally_type'].strip(),
        "title": change['new_question_title'].strip()
    })


def move_candidate(change, election_config, **kwargs):
    '''
    move a candidate position. As we are just checking election config we don't
    have to bother with results, so we can just apply move as a remove + add
    '''
    change_remove = {
        "action": "remove_candidate",
        "election_id": change['election_id'],
        "question_number": change['question_number'],
        "candidature_id": change['candidature_id'],
        "new_candidature_text": change['new_candidature_text'],
        "new_candidature_category": change['new_candidature_category']
    }

    # fix if the add is affected by the remove
    new_id = int(change['new_candidature_id'].strip())
    if int(change['candidature_id']) < new_id:
        new_id = new_id - 1

    change_add = {
        "action": "add_candidate",
        "election_id": change['election_id'],
        "question_number": change['question_number'],
        "new_candidature_id": str(new_id),
        "new_candidature_text": change['new_candidature_text'],
        "new_candidature_category": change['new_candidature_category']
    }
    remove_candidate(change_remove, election_config, **kwargs)
    add_candidate(change_add, election_config, **kwargs)

def new_election(change, election_config, **kwargs):
    '''
    we need to do nothing, it's a no-op change in this case as it's a shinny new
    election
    '''
    pass

def noop(change, election_config, **kwargs):
    '''
    noop, used to add a link between two elections without any change
    '''
    pass
