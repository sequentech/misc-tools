# -*- coding: utf-8 -*-
#
# This file is part of agora-tools.
# Copyright (C) 2013,2015 Eduardo Robles Elvira <edulix AT agoravoting DOT com>

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

import os
import time
import tarfile

MAGIC_TIMESTAMP = 1394060400

def deterministic_tar_open(tally_path, mode="w", timestamp=MAGIC_TIMESTAMP):
    '''
    open tarfile setting cwd so that the header of the
    tarfile doesn't contain the full path, which would make the tally.tar.gz
    not deterministic as it might vary from authority to authority
    '''
    cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(tally_path))
        import time
        old_time = time.time
        time.time = lambda: MAGIC_TIMESTAMP
        tar = tarfile.open(os.path.basename(tally_path), mode)
    finally:
        time.time = old_time
        os.chdir(cwd)
    timestamp = MAGIC_TIMESTAMP
    return tar

def deterministic_tarinfo(tfile, filepath, arcname, timestamp=MAGIC_TIMESTAMP, uid=1000, gid=100):
    '''
    Creates a tarinfo with some fixed data
    '''
    tarinfo = tfile.gettarinfo(filepath, arcname)
    tarinfo.uid = uid
    tarinfo.gid = gid
    tarinfo.mode = 0o755 if tarinfo.isdir() else 0o644
    tarinfo.uname = ""
    tarinfo.gname = ""
    tarinfo.mtime = timestamp
    return tarinfo

def deterministic_tar_add(tfile, filepath, arcname, timestamp=MAGIC_TIMESTAMP, uid=1000, gid=100):
    '''
    tries its best to do a deterministic add of the file
    '''
    tinfo = deterministic_tarinfo(tfile, filepath, arcname, timestamp,
        uid, gid)
    if tinfo.isreg():
         with open(filepath, "rb") as f:
            tfile.addfile(tinfo, f)
    else:
        tfile.addfile(tinfo)

    if os.path.isdir(filepath):
        l = os.listdir(filepath)
        l.sort() # sort or it won't be deterministic!
        for subitem in l:
            newpath = os.path.join(filepath, subitem)
            newarcname = os.path.join(arcname, subitem)
            deterministic_tar_add(tfile, newpath, newarcname, timestamp, uid,
                gid)
