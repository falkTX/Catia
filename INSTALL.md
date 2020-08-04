# INSTALL instructions for Catia

To install Catia, simply run as usual:  
```
make
sudo make install
```

You can run catia without installing it, by using instead: <br/>
```
make
./src/catia.py
```

Packagers can make use of the 'PREFIX' and 'DESTDIR' variable during install, like this: <br/>
```
make install PREFIX=/usr DESTDIR=/path/to/pkg/dir
```

## Build and Runtime Dependencies

The required build dependencies are:

 - PyQt5 (Py3 version)

On Debian and Ubuntu, use these commands to install all build dependencies:
```
sudo apt-get install python3-pyqt5 python3-pyqt5.qtsvg pyqt5-dev-tools
```

For additional a2jmidid integration you'll additionally need:

 - a2jmidid
 - python3-dbus
 - python3-dbus.mainloop.qt
