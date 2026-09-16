TEMPLATE = lib
TARGET = popgreeteractionsplugin
QT += qml
CONFIG += plugin c++11
CONFIG -= qt_import_plugins

SOURCES += plugin.cpp popgreeteractions.cpp
HEADERS += plugin.h popgreeteractions.h

target.path = $$[QT_INSTALL_QML]/PopGreeterActions
qmldir.files = qmldir
qmldir.path = $$[QT_INSTALL_QML]/PopGreeterActions

INSTALLS += target qmldir
