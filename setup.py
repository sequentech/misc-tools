#!/usr/bin/env python3

# This file is part of agora-results.
# Copyright (C) 2014-2021  Agora Voting SL <contact@nvotes.com>

# agora-results is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-results  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-results.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup

setup(
    name='agora-tools',
    version='20.2.0',
    author='Agora Voting SL',
    author_email='contact@nvotes.com',
    packages=[],
    scripts=[],
    url='http://github.com/agoravoting/agora-tools/',
    license='AGPL-3.0',
    description='agora tools',
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
