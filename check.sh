#!/bin/bash

TIMEOUT=10
BOT="./bot"
OUR_BOT="./AI/bot"
SEED=42

if [ -f Bot.java ]; then
	TIMEOUT=20
	BOT="java Bot"
fi

make -f Makefile.checker

points=(10 15 20)
total=0
for i in $(seq 0 2); do
	echo -n "Verificam cu nivelul de inteligenta $i cu botul in pozitia 1:" 
	./server.py -t $TIMEOUT "$BOT B $SEED" "$OUR_BOT A $i $SEED" &>/dev/null
	rc=$?
	if [[ $rc == 61 ]]; then
		total=$(( ${points[$i]} + $total))
		echo "OK."
	else
		echo "Fail."
		rc=61
	fi
	rc=$[$rc - 60]
	cp viewer_log "viewer_log_${i}_${rc}"
	
	echo -n "Verificam cu nivelul de inteligenta $i cu botul in pozitia 2:" 
	./server.py -t $TIMEOUT "$OUR_BOT A $i $SEED" "$BOT B $SEED" &>/dev/null
	rc=$?
	if [[ $rc == 62 ]]; then
		total=$(( ${points[$i]} + $total))
		echo "OK." 
	else
		echo "Fail."
		rc=62
	fi
	rc=$[$rc - 60]
	cp viewer_log "viewer_log_${i}_${rc}"
	
done
echo "Punctaj total: $total"
echo "

---Viewer Logs---

"
for i in $(seq 0 2); do
	for j in $(seq 1 2); do
		echo "Inteligenta $i si pozitie $j"
		cat viewer_log_${i}_${j}
	done
done