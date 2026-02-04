#ifndef ICONPROVIDER_H
#define ICONPROVIDER_H

#include <QQuickImageProvider>
#include <QIcon>
#include <QPainter>
#include <QDir>
#include <QCoreApplication>
#include <QSvgRenderer>
#include <QFile>

class IconProvider : public QQuickImageProvider
{
public:
    IconProvider() : QQuickImageProvider(QQuickImageProvider::Pixmap) {}

    QPixmap requestPixmap(const QString &id, QSize *size, const QSize &requestedSize) override
    {
        QString fileName = id;
        if (!fileName.endsWith(".svg") && !fileName.endsWith(".png")) {
            fileName += ".svg";
        }

        QString path = QCoreApplication::applicationDirPath() + "/assets/icons/" + fileName;
        if (!QFile::exists(path)) {
            path = "d:/app_dibujo_proyecto/assets/icons/" + fileName;
        }
        if (!QFile::exists(path)) {
            path = "assets/icons/" + fileName;
        }
        
        int w = requestedSize.width() > 0 ? requestedSize.width() : 64;
        int h = requestedSize.height() > 0 ? requestedSize.height() : 64;
        QPixmap pixmap(w, h);
        pixmap.fill(Qt::transparent);

        if (QFile::exists(path)) {
            if (path.endsWith(".svg")) {
                QSvgRenderer renderer(path);
                QPainter painter(&pixmap);
                renderer.render(&painter);
            } else {
                pixmap.load(path);
            }
        } else {
            // Fallback: draw a basic circle or placeholder
            QPainter painter(&pixmap);
            painter.setRenderHint(QPainter::Antialiasing);
            painter.setPen(QPen(Qt::white, 1));
            painter.drawEllipse(w/4, h/4, w/2, h/2);
        }

        if (size) *size = pixmap.size();
        return pixmap;
    }
};

#endif // ICONPROVIDER_H
