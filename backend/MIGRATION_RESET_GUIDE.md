# Django Migration Reset Guide

## Complete Reset (Start from Scratch)

### ⚠️ WARNING
**This will delete ALL data in your database!**
Make sure you have backups if needed.

---

## Method 1: Automated Script

Run the provided script:

```bash
cd /Users/eason/Documents/HW\ Project/deepsight-all/DeepSight-Django/backend
./reset_migrations.sh
```

---

## Method 2: Manual Step-by-Step

### Step 1: Delete All Migration Files

```bash
cd /Users/eason/Documents/HW\ Project/deepsight-all/DeepSight-Django/backend

# Delete all migration files (keeps __init__.py)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete

# Delete migration cache files
find . -path "*/migrations/*.pyc" -delete
find . -path "*/migrations/__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

### Step 2: Drop the Database

**For SQLite:**
```bash
rm db.sqlite3
```

**For PostgreSQL:**
```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
DROP DATABASE your_database_name;
CREATE DATABASE your_database_name;
\q
```

**For MySQL:**
```bash
# Connect to MySQL
mysql -u root -p

# In MySQL prompt:
DROP DATABASE your_database_name;
CREATE DATABASE your_database_name;
exit;
```

### Step 3: Create Fresh Migrations

```bash
# Make migrations for each app in order
python manage.py makemigrations users
python manage.py makemigrations notebooks
python manage.py makemigrations reports
python manage.py makemigrations podcast
python manage.py makemigrations conferences

# Or all at once:
python manage.py makemigrations
```

### Step 4: Apply Migrations

```bash
python manage.py migrate
```

### Step 5: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

---

## Method 3: Keep Database Structure, Reset Migrations Only

If you want to reset migrations but keep your database structure:

### Step 1: Fake unapply all migrations

```bash
# Unapply each app's migrations
python manage.py migrate users zero --fake
python manage.py migrate notebooks zero --fake
python manage.py migrate reports zero --fake
python manage.py migrate podcast zero --fake
python manage.py migrate conferences zero --fake
```

### Step 2: Delete migration files

```bash
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
```

### Step 3: Recreate and fake-apply migrations

```bash
# Create new migrations
python manage.py makemigrations

# Fake-apply them (since tables already exist)
python manage.py migrate --fake-initial
```

---

## Verification

After reset, verify everything is working:

```bash
# Check migration status
python manage.py showmigrations

# Check database tables
python manage.py dbshell
# Then run: \dt (PostgreSQL) or SHOW TABLES; (MySQL)

# Run development server
python manage.py runserver
```

---

## Common Issues

### Issue: "No migrations to apply"
**Solution:** Make sure you ran `makemigrations` before `migrate`

### Issue: "Table already exists"
**Solution:** Either drop the database completely or use `--fake-initial` flag

### Issue: Migration dependency errors
**Solution:** Create migrations in the correct order:
1. users
2. notebooks
3. reports (depends on notebooks)
4. podcast (depends on notebooks)
5. conferences (independent)

---

## Backup Before Reset

If you need to backup data first:

```bash
# For SQLite
cp db.sqlite3 db.sqlite3.backup

# For PostgreSQL
pg_dump -U postgres your_database > backup.sql

# For MySQL
mysqldump -u root -p your_database > backup.sql
```

## Restore from Backup

```bash
# For SQLite
cp db.sqlite3.backup db.sqlite3

# For PostgreSQL
psql -U postgres your_database < backup.sql

# For MySQL
mysql -u root -p your_database < backup.sql
```
