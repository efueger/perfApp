#!/bin/bash -eu

# TODO : when xenial will be supported by TravisCI (less problems with updated version of perf-tools ?)
#  the problem is that from trusty, one need to upgrade to get updated software versions => kernel upgrade => for perf-tools to be OK, need to reboot the VM !... :D
#  - TODO-1 : add events in json for PERF-REPORT / LIBPFM4 (last try, perf-record KO + errors of type "events not handled")
#  - TODO-2 : do not allow "No data available" error (needed as perf-top can not handled ARITH on travis ubuntu)
#  - TODO-3 : allow only 1 empty log for perf-top runs
#  - TODO-4 : do not allow "No result available" error (perf-stat KO)

function checkConf {
  if [ "$(\grep -c "Configuring" $1)" -ne "$2" ]; then
    echo "$(\grep "Configuring" $1)";
    echo "KO: bad config ($1, $2, $(\grep -c "Configuring" $1))";
    return 1;
  fi
  if [ "$(\grep -c "is mapped to" $1)" -ne "$3" ]; then
    echo "$(\grep "is mapped to" $1)";
    echo "KO: bad mapping ($1, $3, $(\grep -c "is mapped to" $1))";
    return 1;
  fi

  if [ "$(\grep "Can not check" $1 | wc -l)" -ge "1" ]; then echo "KO: bad config check ($1)"; return 1; fi
  if [ "$(\grep "Can not get" $1 | wc -l)" -ge "1" ]; then echo "KO: bad config get ($1)"; return 1; fi
  if [ "$(\grep "Can not find" $1 | wc -l)" -ge "1" ]; then
    cat ./tmp/libpfm*/examples/showevtinfo.log;
    echo "KO: bad config find ($1)";
    return 1;
  fi

  if [ "$(find ./tmp -name showevtinfo.log | wc -w)" -ne "1" ]; then echo "KO: bad showevtinfo.log"; return 1; fi
  if [ "$(find ./tmp -name check_events_*.log | wc -w)" -lt "1" ]; then echo "KO: bad check_events*.log"; return 1; fi
  for log in $(find ./tmp -name showevtinfo.log) $(find ./tmp -name check_events_*.log)
  do
    echo "Checking conf $log"
    if [ "$(cat "$log" | wc -l)" -le "3" ]; then echo "KO: bad $log"; return 1; fi
  done
  return 0
}

function checkWatch {
  if [ "$(\grep -c "Watching" $1)" -ne "$2" ]; then
    echo "$(\grep "Watching" $1)";
    echo "KO: bad nb watchs ($1, $2, $(\grep -c "Watching" $1))";
    return 1;
  fi

  \grep "Watching" $1 | while read -r line;
  do
    log=$(echo "$line" | awk '{print $4}')
    if [[ "$log" == *"log" ]]; then
      if [ "$(find ./tmp -name "$log" | wc -w)" -gt "1" ]; then echo "KO: several watch $log"; return 1; fi
      logpath=$(find ./tmp -name "$log")
      echo "Checking watch $logpath"
      if [ "$(cat "$logpath" | wc -l)" -le "3" ]; then echo "KO: bad watch $logpath"; return 1; fi
    fi
  done
  return 0
}

function checkRun {
  if [ "$(\grep "has not been run" $1 | wc -w)" -ge "1" ]; then echo "KO: has-not-been-run in $1"; return 1; fi

  local perfTopUseCase=""         # Current perf-top use case run
  local perfTopEvt=""             # Current perf-top event
  local pidThdPerfTop=""          # PID-thread ID for each perf-top run
  local nbEmptyPerfTopPerEvt="0"  # Number of empty log for the current perf-top event
  local maxEmptyPerfTopPerEvt="0" # Maximum allowed number of empty logs
  \grep "Running" $1 | while read -r line;
  do
    log=$(echo "$line" | awk '{print $2}')
    if [[ "$log" == *"log"* ]]; then
      logpath=""
      if [ "$(find ./tmp -name "$log" | wc -w)" == "1" ]; then logpath=$(find ./tmp -name "$log"); fi
      if [ "$logpath" == "" ]; then echo "KO: $log not found"; return 1; fi

      if [[ "$log" == *"perf-top"* ]]; then # Some perf-top logs may be empty sometimes
        IFS='.' read -r -a logTokens <<< "$log"
        if [[ "${logTokens[0]}" != "$perfTopUseCase" ]] || [[ "${logTokens[2]}" != "$perfTopEvt" ]]; then
          perfTopUseCase="${logTokens[0]}"
          perfTopEvt="${logTokens[2]}"
          pidThdPerfTop=""          # Reset
          nbEmptyPerfTopPerEvt="0"  # Reset
          maxEmptyPerfTopPerEvt="0" # Reset
        fi
        if [[ "${logTokens[6]}" != "sh" ]] && [[ "$pidThdPerfTop" != *"${logTokens[6]}"* ]]; then
          pidThdPerfTop="$pidThdPerfTop.${logTokens[6]}"
          maxEmptyPerfTopPerEvt="$(($maxEmptyPerfTopPerEvt + 3))" # Allow up to 3 empty logs per pid - TODO-3
        fi

        if [ "$(\grep "Couldn't create thread/CPU maps: No such process" "$logpath" | wc -l)" -eq "1" ]; then
          nbEmptyPerfTopPerEvt="$(($nbEmptyPerfTopPerEvt + 1))"
          echo "Checking run $logpath, perf-top has not started ($nbEmptyPerfTopPerEvt/$maxEmptyPerfTopPerEvt)"
        fi
        if [ ! -s "$logpath" ]; then # The log is empty
          nbEmptyPerfTopPerEvt=$(($nbEmptyPerfTopPerEvt + 1))
          echo "Checking run $logpath, empty log ($nbEmptyPerfTopPerEvt/$maxEmptyPerfTopPerEvt)"
        fi
        if (($nbEmptyPerfTopPerEvt > $maxEmptyPerfTopPerEvt)); then
          echo "KO: bad empty log $logpath ($nbEmptyPerfTopPerEvt/$maxEmptyPerfTopPerEvt)";
          return 1;
        fi
        echo "Checking run $logpath OK"
        continue # For perf-top only, allow some problems to occur (empty logs, not started)
      fi

      if [ "$(cat "$logpath" | wc -l)" -le "3" ]; then echo "KO: bad run $logpath"; return 1; fi
      echo "Checking run $logpath OK"
    fi
  done

  if [ "$(\grep -c "Running" $1)" -ne "$2" ]; then
    if [ "$(\grep "\.perf-top\." $1 | wc -l)" -gt "0" ]; then # Not sure that number of perf-top runs will always be exactly the same
      return 0; # Can not know how much log perf-top will produce, can't check, return OK
    fi
    echo "$(\grep "Running" $1)";
    echo "KO: bad nb runs ($1, $2, $(\grep -c "Running" $1))";
    return 1;
  fi
  return 0
}

function checkAnalyse {
  if [ "$(\grep -c "Analysing" $1)" -ne "$2" ]; then
    echo "$(\grep "Analysing" $1)";
    echo "KO: bad nb analyses ($1, $2, $(\grep -c "Analysing" $1))";
    return 1;
  fi

  \grep "Analysing" $1 | while read -r line;
  do
    IFS=' ' read -r -a lineTokens <<< "$line"
    if [[ "${lineTokens[1]}" == "stream:" || "${lineTokens[1]}" == "stream2:" || \
          "${lineTokens[1]}" == "HPLinpack:" || "${lineTokens[1]}" == "NAS:" || "${lineTokens[1]}" == "Hydro:" || \
          "${lineTokens[1]}" == "iozone:" || "${lineTokens[1]}" == "IOR:" ]]; then
      if [ "${lineTokens[4]}" == "0.00" ]; then echo "KO: bad analyses max value"; return 1; fi
      if [ "${#lineTokens[@]}" -le "5" ]; then echo "KO: bad analyses max info"; return 1; fi
      echo "Checking ${lineTokens[1]} analyse OK"
    fi
  done
  return 0
}

function checkPlot {
  if [ "$(\grep -c "Plotting" $1)" -ne "$2" ]; then
    echo "$(\grep "Plotting" $1)";
    echo "KO: bad nb plots ($1, $2, $(\grep -c "Plotting" $1))";
    return 1;
  fi

  \grep "Plotting" $1 | while read -r line;
  do
    if [ "$line" == "Plotting benchmarks ..." ]; then continue; fi
    if [ "$line" == "Plotting HPLinpack ..." ]; then continue; fi
    if [ "$line" == "Plotting NAS ..." ]; then continue; fi
    if [ "$line" == "Plotting Hydro ..." ]; then continue; fi
    if [ "$line" == "Plotting stream ..." ]; then continue; fi
    if [ "$line" == "Plotting stream2 ..." ]; then continue; fi
    if [ "$line" == "Plotting iozone ..." ]; then continue; fi
    if [ "$line" == "Plotting IOR ..." ]; then continue; fi
    if [ "$line" == "Plotting pfaBandwidthBounded use case ..." ]; then continue; fi
    if [ "$line" == "Plotting pfaComputeBounded use case ..." ]; then continue; fi
    if [ "$line" == "Plotting pfaPython use case ..." ]; then continue; fi

    png=$(echo "$line" | awk '{print $2}')
    if [[ "$line" == "Plotting the roof line model"* ]]; then png="roofLineModel"; fi
    pngpath="./tmp/plt/$png.png"
    if [ ! -f "$pngpath" ]; then
      if [[ "$(\grep -c "No data available" $1)" -le "8" ]]; then
        echo "Checking plot $pngpath OK (no data available)" # TODO-2
        continue; # TODO-2 : allow 1 or 4 empty plots on travis ubuntu
      fi

      echo "KO: bad plot $pngpath";
      return 1;
    fi
    echo "Checking plot $pngpath OK"
  done
  return 0
}

function checkLog {
  if [ "$(\grep "KO" $1 | wc -w)" -ge "1" ]; then echo "KO: KO in $1"; return 1; fi
  if [ "$(\grep "[Mm]issing" $1 | wc -w)" -ge "1" ]; then echo "KO: missing in $1"; return 1; fi
  if [ "$(\grep "not available" $1 | wc -w)" -ge "1" ]; then echo "KO: not-available in $1"; return 1; fi
  if [ "$(\grep "not found" $1 | wc -w)" -ge "1" ]; then echo "KO: not-found in $1"; return 1; fi
  if [ "$(\grep "[Ee]rror" $1 | wc -w)" -ge "1" ]; then echo "KO: error in $1"; return 1; fi
  #if [ "$(\grep "No data available" $1 | wc -w)" -ge "1" ]; then echo "KO: no-data in $1"; return 1; fi # TODO-2
  #if [ "$(\grep "No result available" $1 | wc -w)" -ge "1" ]; then echo "KO: no-result in $1"; return 1; fi # TODO-4

  checkConf $1 $2 $3
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkWatch $1 $4
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkRun $1 $5
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkAnalyse $1 $6
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkPlot $1 $7
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  echo -e "$1 OK\n"
  return 0
}

function main {
  echo -e "\nTest: code quality\n"
  ./dev/perfAppCodeQuality.sh
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  echo -e "\nTest: help\n"
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json -h
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json check -h
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json bench -h
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json ucase -h
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.less.json plot -h
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  echo -e "\nTest: download option\n"
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json -d check
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json -d bench
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.more.json -d ucase
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  $PFA_COV ./perfApp.py -c ./dev/$1.less.json -d plot
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  if [ "$(ls -d ./tmp/libpfm* | wc -w)" -lt "1" ]; then echo "KO: bad libpfm download"; return 1; fi
  if [ "$(ls -d ./tmp/bench/BLAS* | wc -w)" -lt "1" ]; then echo "KO: bad BLAS download"; return 1; fi
  if [ "$(ls -d ./tmp/bench/hpl* | wc -w)" -lt "1" ]; then echo "KO: bad HPLinpack download"; return 1; fi
  if [ "$(ls -d ./tmp/bench/NPB* | wc -w)" -lt "1" ]; then echo "KO: bad NAS download"; return 1; fi
  if [ "$(ls -d ./tmp/bench/iozone* | wc -w)" -lt "1" ]; then echo "KO: bad iozone download"; return 1; fi
  if [ "$(ls -d ./tmp/bench/IOR/ior | wc -w)" -ne "1" ]; then echo "KO: bad IOR download"; return 1; fi
  if [ "$(ls -d ./tmp/bench/Hydro/Hydro | wc -w)" -ne "1" ]; then echo "KO: bad Hydro download"; return 1; fi
  if [ "$(ls ./tmp/bench/stream/stream.f | wc -w)" -ne "1" ]; then echo "KO: bad stream download"; return 1; fi
  if [ "$(ls ./tmp/bench/stream2/stream2.f | wc -w)" -ne "1" ]; then echo "KO: bad stream2 download"; return 1; fi

  echo -e "\nTest: check mode\n"
  stdbuf -oL -eL $PFA_COV ./perfApp.py -c ./dev/$1.more.json check 2>&1 | tee ./tmp/dev.check01.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.check01.log "60" "5" "0" "1" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -c ./dev/$1.less.json check 2>&1 | tee ./tmp/dev.check02.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.check02.log "72" "2" "0" "1" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  echo -e "\nTest: bench mode\n"
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 4 -c ./dev/$1.more.json bench -s 0.001 -q 2>&1 | tee ./tmp/dev.bench01.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.bench01.log "40" "0" "0" "239" "8" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 2 -c ./dev/$1.more.json bench -s 0.00001 -q -m 2>&1 | tee ./tmp/dev.bench02.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.bench02.log "40" "0" "0" "316" "8" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 2 -c ./dev/$1.less.json -f bench -s 0.0001 -b iozone 2>&1 | tee ./tmp/dev.bench03.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.bench03.log "52" "0" "0" "3" "2" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 4 -c ./dev/$1.less.json -f bench -u 2>&1 | tee ./tmp/dev.bench04.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.bench04.log "52" "0" "0" "0" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  # Reduce test size to reduce test time
  sed -i -e 's/1 2 80 2000/1 1 15 500/'                                                 ./tmp/usc/pfaBandwidthBounded/usc.json
  sed -i -e 's/1 2 4/1 2/'                                                              ./tmp/usc/pfaBandwidthBounded/usc.json
  sed -i -e 's/r g b/r g/'                                                              ./tmp/usc/pfaBandwidthBounded/usc.json
  sed -i -e 's/\^ \^ \^/^ ^/'                                                           ./tmp/usc/pfaBandwidthBounded/usc.json
  sed -i -e 's/"ARGS".*/"ARGS" : "1 1 15 500 | 1 1 15 500 | 1 1 15 500 | 1 1 15 500",/' ./tmp/usc/pfaComputeBounded/usc.json
  sed -i -e 's/200000000 200000000/50000000 50000000/'                                  ./tmp/usc/pfaPython/usc.json

  echo -e "\nTest: ucase mode\n"
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 4 -c ./dev/$1.more.json ucase -s 2>&1 | tee ./tmp/dev.ucase01.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.ucase01.log "102" "5" "0" "15" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 4 -c ./dev/$1.more.json -f ucase -u "pfa*" -r -m 2000 2>&1 | tee ./tmp/dev.ucase02.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.ucase02.log "60" "5" "0" "15" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 2 -c ./dev/$1.less.json -f ucase -u "pfaBandwidthBounded" -t -w -v 2>&1 | tee ./tmp/dev.ucase03.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.ucase03.log "59" "2" "8" "29" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -s -n 4 -c ./dev/$1.less.json -f ucase -u "pfaComputeBounded" -t 10 -w -v 2>&1 | tee ./tmp/dev.ucase04.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.ucase04.log "60" "2" "16" "93" "0" "0"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  if [ "$(find ./tmp -name *objdump.log | wc -w)" -ne "10" ]; then echo "KO: bad objdump nb"; return 1; fi
  for log in $(find ./tmp -name *objdump.log)
  do
    if [ ! -s "$log" ]; then # The log is empty
      echo "KO: bad objdump $log";
      return 1;
    fi
  done

  echo -e "\nTest: plot mode\n"
  stdbuf -oL -eL $PFA_COV ./perfApp.py -n 4 -c ./dev/$1.more.json plot -b -s 2>&1 | tee ./tmp/dev.plot01.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.plot01.log "40" "0" "0" "0" "0" "31"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -n 4 -c ./dev/$1.less.json plot -b NAS -s 2>&1 | tee ./tmp/dev.plot02.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.plot02.log "52" "0" "0" "0" "0" "5"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -n 2 -c ./dev/$1.less.json plot -u "*Bandwidth*" -r -t "t=02" -w "t=02" -m -a -v -s 2>&1 | tee ./tmp/dev.plot03.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.plot03.log "59" "2" "0" "1" "13" "9"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  stdbuf -oL -eL $PFA_COV ./perfApp.py -n 4 -c ./dev/$1.less.json -f plot -u "*Compute*" -r -t -w -m "pfb*" -a -v -s 2>&1 | tee ./tmp/dev.plot04.log
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi
  checkLog ./tmp/dev.plot04.log "102" "2" "0" "1" "49" "21"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  unset PFA_MLK
  echo -e "\nTest: failure\n" # Test failure fails !... And increase coverage
  echo "This code must NOT compile" >> ./tmp/usc/pfaFlopsCacheMisses.cpp
  $PFA_COV ./perfApp.py -n 2 -c ./dev/$1.less.json ucase -u "pfaBandwidthBounded"
  if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; return 1; fi

  return 0
}

cd `dirname $0`
cd ..

if [[ "$#" -lt "1" ]]; then
  echo "Missing argument : need to identify json (debian.i7-3687U, ubuntu14.iXeon, ...)"
  exit 0
fi

if ! test -v "PFA_MLK"; then
  export PFA_MLK="YES"
fi
if ! test -v "PFA_COV"; then
  export PFA_COV="python -m coverage run --parallel-mode"
fi
echo "INFO ENV : PFA_MLK = \"$PFA_MLK\", PFA_COV = \"$PFA_COV\""

if [[ "$#" == "2" && "$2" == "LOG" ]]; then # Save logs
  for log in $(ls ./tmp/dev.*0*.log)
  do
    echo "Update reference file $log ..."
    cp -f $log ./dev # Keep log !...
  done
  exit 0
fi

if [ -d ./tmp ]; then # Clean before testing
  if [ ! -d ./tmp.old ]; then mv -f ./tmp ./tmp.old; fi
  rm -fr ./tmp
fi
mkdir -p tmp
set +e # Unset before ping that may trigger errors if no network
ping -c 1 www.github.com > ./tmp/dev.ping.log 2>&1 # Work locally if no network available
set -e # Set after ping that may trigger errors if no network
if [ "$(\grep "failure" ./tmp/dev.ping.log | wc -w)" -gt "0" ]; then
  if [ ! -d ./tmp.old ]; then echo "KO: need internet access"; return 1; fi
  mkdir -p ./tmp/bench
  cp -fr ./tmp.old/bench/*.tgz    ./tmp/bench
  cp -fr ./tmp.old/bench/*.tar.gz ./tmp/bench
  cp -fr ./tmp.old/bench/*.tar    ./tmp/bench
  cp -fr ./tmp.old/bench/stream*  ./tmp/bench
  cp -fr ./tmp.old/bench/IOR      ./tmp/bench
  cp -fr ./tmp.old/bench/Hydro    ./tmp/bench
  cp -fr ./tmp.old/libpfm*.tar.gz ./tmp
fi

python -m coverage erase

STARTTIME=$(date +%s)
main $@
if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; exit 1; fi
ENDTIME=$(date +%s)

echo "Coverage"
python -m coverage combine --append
python -m coverage html --omit=*pympler* -d ./tmp/coverage
python -m coverage report --omit=*pympler*
if [ "$?" -ne "0" ]; then echo "KO: do NOT commit"; exit 1; fi
python -m coverage erase

echo ""
echo "OK (time $(($ENDTIME - $STARTTIME)) secs)"
