#include "popgreeteractions.h"

#include <QProcess>
#include <QDebug>
#include <qnumeric.h>

const char *const PopGreeterActions::kRevertScript =
    "/usr/local/sbin/pop-revert-to-cosmic.sh";

qreal PopGreeterActions::s_reveal = 0.0;
QList<PopGreeterActions *> PopGreeterActions::s_instances;

PopGreeterActions::PopGreeterActions(QObject *parent) : QObject(parent) {
    s_instances.append(this);
}

PopGreeterActions::~PopGreeterActions() {
    s_instances.removeAll(this);
}

qreal PopGreeterActions::reveal() const {
    return s_reveal;
}

void PopGreeterActions::setReveal(qreal value) {
    if (qFuzzyCompare(s_reveal + 1.0, value + 1.0)) {
        return;
    }
    s_reveal = value;
    for (PopGreeterActions *instance : qAsConst(s_instances)) {
        emit instance->revealChanged();
    }
}

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
