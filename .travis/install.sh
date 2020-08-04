#!/bin/bash

set -e

sudo apt-get install -y \
    pylint3 \
    python3-dbus.mainloop.pyqt5 \
    python3-pyqt5 python3-pyqt5.qtsvg python3-pyqt5.qtopengl \
    pyqt5-dev-tools \
    qtbase5-dev
