#ifndef PREFERENCESMANAGER_H
#define PREFERENCESMANAGER_H

#include <QObject>
#include <QSettings>
#include <QColor>
#include <QStandardPaths>
#include <QDir>

class PreferencesManager : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString themeMode READ themeMode WRITE setThemeMode NOTIFY settingsChanged)
    Q_PROPERTY(QString themeAccent READ themeAccent WRITE setThemeAccent NOTIFY settingsChanged)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY settingsChanged)

public:
    explicit PreferencesManager(QObject *parent = nullptr) : QObject(parent) {
        QString dataPath = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        QDir().mkpath(dataPath);
        m_settings = new QSettings(dataPath + "/user_preferences.ini", QSettings::IniFormat, this);
    }

    QString themeMode() const { return m_settings->value("theme_mode", "Dark").toString(); }
    void setThemeMode(const QString &mode) { m_settings->setValue("theme_mode", mode); emit settingsChanged(); }

    QString themeAccent() const { return m_settings->value("theme_accent", "#6366f1").toString(); }
    void setThemeAccent(const QString &accent) { m_settings->setValue("theme_accent", accent); emit settingsChanged(); }

    QString language() const { return m_settings->value("language", "es").toString(); }
    void setLanguage(const QString &lang) { m_settings->setValue("language", lang); emit settingsChanged(); }

signals:
    void settingsChanged();

private:
    QSettings *m_settings;
};

#endif // PREFERENCESMANAGER_H
