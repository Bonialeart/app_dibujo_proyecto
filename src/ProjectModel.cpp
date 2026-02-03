#include "ProjectModel.h"
#include <QDir>
#include <QStandardPaths>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDebug>
#include <algorithm>

ProjectModel::ProjectModel(QObject *parent)
    : QAbstractListModel(parent)
{
}

int ProjectModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid()) return 0;
    return m_projects.size();
}

QVariant ProjectModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_projects.size())
        return QVariant();

    const auto &project = m_projects[index.row()];

    switch (role) {
    case NameRole: return project.name;
    case PathRole: return project.path;
    case PreviewRole: return project.preview;
    case TypeRole: return project.type;
    case DateRole: return project.date;
    case ThumbnailsRole: return project.thumbnails;
    default: return QVariant();
    }
}

QHash<int, QByteArray> ProjectModel::roleNames() const
{
    QHash<int, QByteArray> roles;
    roles[NameRole] = "name";
    roles[PathRole] = "path";
    roles[PreviewRole] = "preview";
    roles[TypeRole] = "type";
    roles[DateRole] = "date";
    roles[ThumbnailsRole] = "thumbnails";
    return roles;
}

void ProjectModel::refresh(const QString &dirPath)
{
    QString targetPath = dirPath;
    if (targetPath.isEmpty()) {
        targetPath = QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation) + "/ArtFlowProjects";
    }

    QDir dir(targetPath);
    if (!dir.exists()) {
        dir.mkpath(".");
    }

    beginResetModel();
    m_projects.clear();

    QFileInfoList entries = dir.entryInfoList(QDir::Dirs | QDir::Files | QDir::NoDotAndDotDot, QDir::Time);

    for (const QFileInfo &info : entries) {
        if (info.fileName().endsWith(".json") && info.isFile()) continue;

        ProjectEntry entry;
        entry.name = info.fileName();
        entry.path = info.absoluteFilePath();
        entry.date = info.lastModified();
        entry.type = info.isDir() ? "folder" : "drawing";
        entry.preview = "";

        if (info.isDir()) {
            // Check for meta.json
            QFile metaFile(info.absoluteFilePath() + "/meta.json");
            if (metaFile.open(QIODevice::ReadOnly)) {
                QJsonDocument doc = QJsonDocument::fromJson(metaFile.readAll());
                if (doc.isObject()) {
                    QJsonObject obj = doc.object();
                    if (obj.contains("type")) entry.type = obj["type"].toString();
                    if (obj.contains("title")) entry.name = obj["title"].toString();
                }
            }

            // Scan for thumbnails
            QDir subDir(info.absoluteFilePath());
            QStringList filters;
            filters << "*.png" << "*.jpg" << "*.jpeg" << "*.aflow";
            QFileInfoList subFiles = subDir.entryInfoList(filters, QDir::Files, QDir::Time);
            
            for (int i = 0; i < qMin(3, (int)subFiles.size()); ++i) {
                QString path = subFiles[i].absoluteFilePath();
                if (path.endsWith(".aflow")) {
                    // Extract preview path (assuming system extractor works as before)
                    QString tempPath = QDir::tempPath() + "/ArtFlowPreviews/" + subFiles[i].fileName() + ".png";
                    entry.thumbnails << "file:///" + tempPath;
                } else {
                    entry.thumbnails << "file:///" + path;
                }
            }
            if (!entry.thumbnails.isEmpty()) entry.preview = entry.thumbnails[0];
        } else {
            // It's a file
            if (info.fileName().endsWith(".aflow")) {
                QString tempPath = QDir::tempPath() + "/ArtFlowPreviews/" + info.fileName() + ".png";
                entry.preview = "file:///" + tempPath;
            } else if (info.fileName().endsWith(".png") || info.fileName().endsWith(".jpg")) {
                entry.preview = "file:///" + info.absoluteFilePath();
            }
        }

        m_projects.append(entry);
    }

    endResetModel();
}
