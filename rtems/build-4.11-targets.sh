#! /bin/sh

if [ $# -ne 1 ]; then
  echo "error: no prefix provided"
  exit 1
fi

targets="arm avr bfin h8300 m32c m32r m68k mips powerpc sh sparc"
bad_targets="lm32"

log="rtems4.11-build-tools-results.txt"

echo "RTEMS 4.11 Build Results $(date)" > ${log}

for t in ${targets}
do
  ../source-builder/sb-set-builder --log=l-${t}.txt \
                                   --prefix=$1 \
                                   --target=${t}-rtems4.11 \
                                   rtems-tools-4.11
  if [ $? -eq 0 ]; then
    echo "${t}-rtems4.11 passed" >> ${log}
  else
    echo "${t}-rtems4.11 FAILED" >> ${log}
  fi
done
