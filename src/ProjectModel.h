#ifndef PROJECTMODEL_H
#define PROJECTMODEL_H

#include <QAbstractListModel>
#include <QVector>
#include <QString>
#include <QDateTime>

struct ProjectEntry {
    QString name;
    QString path;
    QString preview;
    QString type; // "drawing" or "folder"
    QDateTime date;
    QStringList thumbnails;
};

class ProjectModel : public QAbstractListModel
{
    Q_OBJECT

public:
    enum ProjectRoles {
        NameRole = Qt::UserRole + 1,
        PathRole,
        PreviewRole,
        TypeRole,
        DateRole,
        ThumbnailsRole
    };

    explicit ProjectModel(QObject *parent = nullptr);

    // Métodos obligatorios de QAbstractListModel
    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

    // Acción para escanear archivos
    Q_INVOKABLE void refresh(const QString &dirPath);

private:
    QVector<ProjectEntry> m_projects;
};

#endif // PROJECTMODEL_H
