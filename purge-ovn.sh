#!/bin/bash
set +x #echo on

#systemctl stop vse_datapath.service
input="ovn-services.txt"
while read  word _
do
  systemctl stop "$word"
  systemctl disable "$word"
  printf '%s\n' "$word"
done < "$input"