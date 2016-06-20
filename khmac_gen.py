##!/usr/bin/env python3

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

import argparse
import hashlib
import time
import hmac

def get_auth_khmac(secret, userid, obj_type, obj_id, perm):
    message = ":".join([
        userid,
        obj_type,
        obj_id,
        perm,
        str(int(time.time()))])
    return get_khmac(secret, message)

def get_khmac(secret, message):
    code = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
        ).hexdigest()
    return 'khmac:///sha-256;%s/%s' % (code, message)

def main():
    parser = argparse.ArgumentParser(
      description='Keyed Hash-based Message Authentication Code URIs generator')
    parser.add_argument('-s', '--secret')
    parser.add_argument('-u', '--userid', default=None)
    parser.add_argument('-ot', '--object-type', default=None)
    parser.add_argument('-oi', '--object-id', default=None)
    parser.add_argument('-p', '--permission', default=None)
    parser.add_argument('-m', '--message', default=None)
    args = parser.parse_args()

    if args.message is not None:
        print(get_khmac(args.secret, args.message))

    elif args.userid is not None or args.object_type is not None or\
            args.object_id is not None:
        khmac = get_auth_khmac(
            args.secret,
            args.userid,
            args.object_type,
            args.object_id,
            args.permission)
        print(khmac)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
