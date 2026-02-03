#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QIcon>
#include <QDir>
#include <QStandardPaths>
#include "CanvasItem.h"
#include "ProjectModel.h"
#include "PreferencesManager.h"
#include "IconProvider.h"

int main(int argc, char *argv[])
{
    // High DPI support
    #if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
        QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    #endif

    QGuiApplication app(argc, argv);
    app.setOrganizationName("ArtFlowStudio");
    app.setApplicationName("ArtFlow Pro");

    // Registro del componente de dibujo nativo
    qmlRegisterType<CanvasItem>("ArtFlow", 1, 0, "QCanvasItem");
    
    QQmlApplicationEngine engine;
    engine.addImageProvider(QLatin1String("icons"), new IconProvider());
    
    // Inyectar managers globales
    ProjectModel projectModel;
    PreferencesManager preferencesManager;
    
    engine.rootContext()->setContextProperty("nativeProjectModel", &projectModel);
    engine.rootContext()->setContextProperty("preferencesManager", &preferencesManager);

    // Carga de la App desde Recursos (.qrc)
    const QUrl url(QStringLiteral("qrc:/qml/main_pro.qml"));
    
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated,
                     &app, [url](QObject *obj, const QUrl &objUrl) {
        if (!obj && url == objUrl)
            QCoreApplication::exit(-1);
    }, Qt::QueuedConnection);

    engine.load(url);

    return app.exec();
}
