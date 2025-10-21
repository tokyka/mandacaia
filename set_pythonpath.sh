#!/bin/bash

path=$(pwd)
rst=$(ls -l app | grep ^d | awk '{print $9}')
#echo "${rst}"
#echo "${path}"
p=""
for i in $rst
do
   if [ "$i" == "__pycache__" ]; then
     continue
   fi
   if [ -z "$p" ]; then
     p=`echo -e $p$path'/'$i`
   else
     p=`echo -e $p':'$path'/'$i`
   fi
done
if [ -n "$p" ]; then
   p=`echo -e '"'$p':'$path'"'`
fi
if [[ $(readlink -f /proc/$(ps -o ppid:1= -p $$)/exe) != $(readlink -f "$SHELL") ]]
then 
   export PYTHONPATH="${path}"
   export FLASK_APP=app.py
   activate=`echo -e $path'/.venv/bin/activate'`
   source $activate
else
   echo
   echo "Execute: '. ./set_pythonpath.sh' ou 'source set_pythonpath.sh'"
   echo
   echo "Este script deve ser executado da forma exibida acima, para"
   echo "que as variáveis de ambiente sejam carregadas no shell corrente."
   echo
fi
