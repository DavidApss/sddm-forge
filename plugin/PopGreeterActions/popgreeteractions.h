#ifndef POPGREETERACTIONS_H
#define POPGREETERACTIONS_H

#include <QObject>

// Exposes a single, narrowly-scoped privileged action to the greeter QML:
// reverting the active display manager back to cosmic-greeter. It shells
// out to `sudo <exact script path>` - the sudoers.d rule installed
// alongside this plugin grants the `sddm` user NOPASSWD execution of
// that one script and nothing else.
class PopGreeterActions : public QObject {
    Q_OBJECT

public:
    explicit PopGreeterActions(QObject *parent = nullptr);

    Q_INVOKABLE bool revertToCosmic();

private:
    static const char *const kRevertScript;
};

#endif // POPGREETERACTIONS_H
