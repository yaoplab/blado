# Bladɔ — Installation sur Windows 11

## Prérequis

- **Python 3.11+** : https://www.python.org/downloads/
- **PostgreSQL 16+** : https://www.postgresql.com/download/windows/
- **Git** (optionnel) : https://git-scm.com/download/win

## Installation rapide (depuis GitHub)

```bash
# 1. Cloner le projet
git clone https://github.com/yaoplab/blado.git
cd blado

# 2. Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer PostgreSQL
#    - Créer une base bladodb sur le port 55515
#    - Éditer BladoCommon/bladocommon/config.ini si besoin

# 5. Exécuter le schéma DB
psql -h 127.0.0.1 -p 55515 -U postgres -d bladodb -f sql/init_blado.sql
psql -h 127.0.0.1 -p 55515 -U postgres -d bladodb -f sql/seed_metallurgie.sql
psql -h 127.0.0.1 -p 55515 -U postgres -d bladodb -f sql/seed_agenda.sql

# 6. Créer l'utilisateur admin
psql -h 127.0.0.1 -p 55515 -U postgres -d bladodb -c "INSERT INTO blado_user (email, password, full_name, role) VALUES ('admin@blado.local', '<SHA256>', 'Administrateur', 'RH') ON CONFLICT DO NOTHING;"

# 7. Lancer
python -m Blado
```

## Compilation en .exe (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --name Blado --onefile --windowed --add-data "BladoCommon;BladoCommon" --add-data "phibuilder;phibuilder" --add-data "photos;photos" Blado/__main__.py
```

L'exécutable sera dans `dist/Blado.exe`.

## Configuration PostgreSQL

Modifier `BladoCommon/bladocommon/config.ini` :

```ini
[IntranetDatabase]
Host=127.0.0.1
Port=55515
DB=bladodb
User=postgres
Pass=postgres
```

## Login par défaut

- Email : `admin@blado.local`
- Mot de passe : `admin123`
