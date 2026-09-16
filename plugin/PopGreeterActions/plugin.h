#ifndef POPGREETERACTIONS_PLUGIN_H
#define POPGREETERACTIONS_PLUGIN_H

#include <QQmlExtensionPlugin>

class PopGreeterActionsPlugin : public QQmlExtensionPlugin {
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)

public:
    void registerTypes(const char *uri) override;
};

#endif // POPGREETERACTIONS_PLUGIN_H
