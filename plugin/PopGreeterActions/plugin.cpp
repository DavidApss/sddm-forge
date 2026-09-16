#include "plugin.h"
#include "popgreeteractions.h"

#include <qqml.h>

void PopGreeterActionsPlugin::registerTypes(const char *uri) {
    Q_ASSERT(QLatin1String(uri) == QLatin1String("PopGreeterActions"));
    qmlRegisterType<PopGreeterActions>(uri, 1, 0, "PopGreeterActions");
}
