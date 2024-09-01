import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://default:1DWbvKocPrp0@ep-plain-union-a2rcbea6-pooler.eu-central-1.aws.neon.tech:5432/verceldb?sslmode=require'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False