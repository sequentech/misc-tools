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

add_arguments = [
        ['--plugins', {'action': 'store_true', 'help': 'Show too active plugins.'}]
]


def plugins(args):
    print("Active plugins:")
    for p in PLUGINS:
        print("* ", p)


def check_arguments(args, glo, loc):
    globals().update(glo)
    locals().update(loc)
    if args.plugins:
        plugins(args)
    else:
        return False
    return True
