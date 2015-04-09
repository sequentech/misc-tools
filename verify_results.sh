#!/bin/bash

export TMP_DIR=/tmp/orig
export AGORA_RESULTS_PATH=/home/agoraelections/agora-results
export BASE_TARS_URL=/srv/election-orchestra/server1/public/
export TARS_PATH=/home/agoraelections/tars
export TARFILE=$(realpath $1)
export VIRTUALENV=/home/agoraelections/.virtualenvs/agora-tools

if [ "$(whoami)" != "root" ]
then
  echo "execute as root!"
  exit 1
fi
source $VIRTUALENV/bin/activate

[ -d $TMP_DIR ] && rm -rf $TMP_DIR
[ -d $TARS_PATH ] || mkdir -p $TARS_PATH
mkdir $TMP_DIR
cd $TMP_DIR
tar zxf $TARFILE --transform='s/.*\///'
FILES=$(ls *.results.pretty | xargs -n1 basename | sed s/.results.pretty//g)

for i in $FILES
do
  # download if needed
  file ${TARS_PATH}/${i}.tar.gz | grep ': empty$'
  if [ $? == 0 ] || [ ! -f "${TARS_PATH}/${i}.tar.gz" ]
  then
    cp "${BASE_TARS_URL}/${i}/tally.tar.gz" "${TARS_PATH}/${i}.tar.gz"
    A=$?
    file ${TARS_PATH}/${i}.tar.gz | grep ': empty$'
    if [ $? == 0 ] || [ $A != 0 ]
    then
      echo "error copying the tarfile"
      exit 1
    fi
  fi

  echo "executing '$AGORA_RESULTS_PATH/agora-results -c $TMP_DIR/${i}.config.results.json -t ${TARS_PATH}/${i}.tar.gz -s -o pretty'.."

  $AGORA_RESULTS_PATH/agora-results -c ${i}.config.results.json -t "${TARS_PATH}/${i}.tar.gz" -s -o pretty > "${i}.results.mine.pretty"
  [ $? != 0 ] && echo "error executing previous command" && exit 1

  my_md5=$(md5sum "${i}.results.mine.pretty" | cut -b-32)
  other_md5=$(md5sum "${i}.results.pretty" | cut -b-32)
  if [ "$my_md5" != "$other_md5" ]
  then
    echo "election '${i}': md5sum mismatch: mine(${my_md5}) != theirs(${other_md5})"
    exit 1
  else
    echo "election '${i}': md5 ${my_md5} verified ${i}.results.pretty"
  fi
done

echo "SUCCESS! all files verified"