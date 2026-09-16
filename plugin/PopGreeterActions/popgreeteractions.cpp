#include "popgreeteractions.h"

#include <QProcess>
#include <QDebug>

const char *const PopGreeterActions::kRevertScript =
    "/usr/local/sbin/pop-revert-to-cosmic.sh";

PopGreeterActions::PopGreeterActions(QObject *parent) : QObject(parent) {}

bool PopGreeterActions::revertToCosmic() {
    // sudo -n: never prompt interactively. If the sudoers.d rule isn't
    // installed (or doesn't match exactly), this fails closed instead of
    // hanging the greeter on a password prompt nobody can answer.
    qint64 pid = 0;
    bool started = QProcess::startDetached(
        QStringLiteral("sudo"),
        {QStringLiteral("-n"), QString::fromLatin1(kRevertScript)},
        QString(),
        &pid
    );
    if (!started) {
        qWarning() << "PopGreeterActions: failed to start revert script";
    }
    return started;
}
