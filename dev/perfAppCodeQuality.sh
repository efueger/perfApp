#!/bin/bash -eu

export bestRate="9.95"

cd `dirname $0`

# A minimum set of coding rules are imposed to insure code quality and consistency
#
# Coding rules:
# 1. space policy: use space (not tab), respect PEP space policy
# 2. names for functions, classes, variables: use "thisName" instead of "this_name" as it is shorter
# 3. allow line length to be up to 120 characters long
# 4. allow a bit a flexibility: --max-args=7 (self + 6 args)
# 5. duplicate code: avoid false positive with --min-similarity-lines --ignore-imports --ignore-docstrings
# 6. generate .pylintrc for python static analysis (codeclimate through github)

pylint --variable-rgx="[a-z]*([A-Z][a-z]*)*"                             \
       --method-rgx="[a-z]*([A-Z][a-z]*)*"                               \
       --module-rgx="[a-z]*([A-Z][a-z]*)*"                               \
       --function-rgx="[a-z]*([A-Z][a-z]*)*"                             \
       --argument-rgx="[a-z]*([A-Z][a-z]*)*"                             \
       --class-rgx="[a-z]*([A-Z][a-z]*)*"                                \
       --class-attribute-rgx="[a-z]*([A-Z][a-z]*)*"                      \
       --attr-rgx="[a-z]*([A-Z][a-z]*)*"                                 \
       --max-locals=20                                                   \
       --max-line-length=120                                             \
       --min-similarity-lines=6 --ignore-imports=y --ignore-docstrings=n \
       --max-args=7                                                      \
       --generate-rcfile > ../.pylintrc

pylint --rcfile=../.pylintrc ../*.py ../py*/*.py ../usc/*/*.py | tee perfAppCodeQuality.log
if [ "$(\grep "Your code has been rated" perfAppCodeQuality.log | wc -l)" -ne "1" ]; then exit 1; fi

export rate=$(\grep "Your code has been rated" perfAppCodeQuality.log | awk '{print $7;}')
export rate=${rate%"/10"}

echo ""
echo "head of perfAppCodeQuality.log :"
echo "================================"
echo ""
head perfAppCodeQuality.log

echo ""
echo "rate: ${rate}, best rate: $bestRate"

echo ""
export check="python -c \"from __future__ import print_function; print(False if "$rate" < "$bestRate" else True)\""
export check=$(eval $check)
if [ "$?" -ne "0" ]; then exit 1; fi
if [ "$check" == "False" ]; then
  echo "do NOT commit: respect coding rules before committing (insure code quality and consistency)"
  exit 1
fi

echo "you can commit"
