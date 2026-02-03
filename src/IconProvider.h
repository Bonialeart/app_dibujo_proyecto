#ifndef ICONPROVIDER_H
#define ICONPROVIDER_H

#include <QQuickImageProvider>
#include <QIcon>
#include <QPainter>
#include <QDir>
#include <QCoreApplication>

class IconProvider : public QQuickImageProvider
{
public:
    IconProvider() : QQuickImageProvider(QQuickImageProvider::Pixmap) {}

    QPixmap requestPixmap(const QString &id, QSize *size, const QSize &requestedSize) override
    {
        QString path = QCoreApplication::applicationDirPath() + "/assets/icons/" + id;
        if (!QFile::exists(path)) {
            // Try relative to source dir if building locally
            path = "d:/app_dibujo_proyecto/assets/icons/" + id;
        }
        if (!QFile::exists(path)) {
            path = "assets/icons/" + id;
        }
        
        QPixmap pixmap;
        if (QFile::exists(path)) {
            pixmap.load(path);
        } else {
            // Fallback: draw a basic icon
            pixmap = QPixmap(requestedSize.width() > 0 ? requestedSize.width() : 64, 
                             requestedSize.height() > 0 ? requestedSize.height() : 64);
            pixmap.fill(Qt::transparent);
            QPainter painter(&pixmap);
            painter.setRenderHint(QPainter::Antialiasing);
            painter.setPen(Qt::white);
            painter.drawRect(2, 2, pixmap.width()-4, pixmap.height()-4);
        }

        if (size) *size = pixmap.size();
        return pixmap;
    }
};

#endif // ICONPROVIDER_H
