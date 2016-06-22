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

import json
from json import *

def serialize(data):
    return json.dumps(data,
        indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))
