#!/usr/bin/env python3

# This file is part of tally-pipes.
# Copyright (C) 2014-2021  Sequent Tech Inc <legal@sequentech.io>

# tally-pipes is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# tally-pipes  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with tally-pipes.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup

setup(
    name='misc-tools',
    version='6.1.6',
    author='Sequent Tech Inc',
    author_email='legal@sequentech.io',
    packages=[],
    scripts=[],
    url='http://github.com/sequentech/misc-tools/',
    license='AGPL-3.0',
    description='sequent tools',
    long_description=open('README.md').read(),
    install_requires=[
        'SQLAlchemy==1.3.0',
        'argparse==1.2.1',
        'datadiff==1.1.6',
        'prettytable==0.7.2',
        'requests==2.20.0',
        'pyminizip==0.2.4'
    ]
)
