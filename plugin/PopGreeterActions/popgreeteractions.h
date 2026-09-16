#ifndef POPGREETERACTIONS_H
#define POPGREETERACTIONS_H

#include <QList>
#include <QObject>

// Exposes two things to the greeter QML:
//
// - A single, narrowly-scoped privileged action: reverting the active
//   display manager back to cosmic-greeter. It shells out to
//   `sudo <exact script path>` - the sudoers.d rule installed alongside
//   this plugin grants the `sddm` user NOPASSWD execution of that one
//   script and nothing else.
//
// - A `reveal` property shared across every PopGreeterActions instance
//   in this process (a static behind the property, not per-object
//   state). sddm-greeter runs one process with one QML engine per
//   screen, so each screen's Main.qml gets its own instance; without
//   this, the login card's background reveal would only ever animate
//   on whichever screen the user is typing on. Setting `reveal` on any
//   instance notifies all of them, so every screen's background stays
//   in sync.
class PopGreeterActions : public QObject {
    Q_OBJECT
    Q_PROPERTY(qreal reveal READ reveal WRITE setReveal NOTIFY revealChanged)

public:
    explicit PopGreeterActions(QObject *parent = nullptr);
    ~PopGreeterActions() override;

    Q_INVOKABLE bool revertToCosmic();

    qreal reveal() const;
    void setReveal(qreal value);

signals:
    void revealChanged();

private:
    static const char *const kRevertScript;
    static qreal s_reveal;
    static QList<PopGreeterActions *> s_instances;
};

#endif // POPGREETERACTIONS_H
