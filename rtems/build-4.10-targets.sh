#! /bin/sh

if [ $# -ne 1 ]; then
  echo "error: no prefix provided"
  exit 1
fi

targets="arm avr bfin h8300 lm32 m32c m32r m68k mips powerpc sh sparc"

log="rtems4.10-build-tools-results.txt"

echo "RTEMS 4.10 Build Results $(date)" > ${log}

for t in ${targets}
do
  ../source-builder/sb-set-builder --log=l-${t}.txt \
                                   --prefix=$1 \
                                   --target=${t}-rtems4.10 \
                                   rtems-tools-4.10
  if [ $? -eq 0 ]; then
    echo "${t}-rtems4.10 passed" >> ${log}
  else
    echo "${t}-rtems4.10 FAILED" >> ${log}
  fi
done
