# Konfigurasi Database
# Copy file ini ke config.py dan sesuaikan dengan konfigurasi database Anda

# Database MySQL
DB_USERNAME = 'root'  # Ganti dengan username MySQL Anda
DB_PASSWORD = 'root'  # Ganti dengan password MySQL Anda
DB_HOST = 'localhost'  # Host database
DB_PORT = '3306'  # Port database
DB_NAME = 'plate_detection'  # Nama database

# Konfigurasi SQLAlchemy
SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
SQLALCHEMY_TRACK_MODIFICATIONS = False