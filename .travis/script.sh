#!/bin/bash

set -e

if which pylint3 >/dev/null; then
  pylint='pylint3'
else
  pylint='pylint'
fi

${pylint} \
    --extension-pkg-whitelist=dbus.mainloop.pyqt5,PyQt5 \
    -E \
    --disable=unsubscriptable-object \
    src/*.py
