import config
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS

# Inisialisasi database
db = SQLAlchemy(app)

# Model untuk tabel deteksi plat nomor
class LicensePlate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    prefix = db.Column(db.String(5), nullable=True)
    numbers = db.Column(db.String(10), nullable=True)
    suffix = db.Column(db.String(5), nullable=True)
    detection_time = db.Column(db.DateTime, default=datetime.now)
    confidence = db.Column(db.Float, nullable=True)
    
    # Relasi one-to-one dengan TaxInfo
    tax_info = db.relationship('TaxInfo', backref='license_plate', uselist=False)

# Model untuk tabel informasi pajak
class TaxInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_id = db.Column(db.Integer, db.ForeignKey('license_plate.id'), unique=True, nullable=False)
    brand = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    tax_amount = db.Column(db.String(50), nullable=True)
    tax_due_date = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(50), nullable=True)  # Status pajak (lunas/belum)
    created_at = db.Column(db.DateTime, default=datetime.now)

# Route untuk endpoint utama
@app.route('/')
def index():
    return "Plate Detection API is running!"

# Endpoint untuk menyimpan data plat nomor
@app.route('/api/plate', methods=['POST'])
def save_plate():
    try:
        data = request.json
        
        # Simpan data plat nomor
        new_plate = LicensePlate(
            plate_number=data['plate_number'],
            prefix=data.get('prefix'),
            numbers=data.get('numbers'),
            suffix=data.get('suffix'),
            confidence=data.get('confidence')
        )
        
        db.session.add(new_plate)
        db.session.commit()
        
        # Jika ada data pajak, simpan juga
        if 'tax_info' in data and data['tax_info']:
            tax_data = data['tax_info']
            new_tax_info = TaxInfo(
                license_id=new_plate.id,
                brand=tax_data.get('brand'),
                model=tax_data.get('model'),
                year=tax_data.get('year'),
                tax_amount=tax_data.get('tax_amount'),
                tax_due_date=tax_data.get('tax_due_date'),
                status=tax_data.get('status')
            )
            
            db.session.add(new_tax_info)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Data saved successfully',
            'plate_id': new_plate.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error saving data: {str(e)}'
        }), 500

# Endpoint untuk mendapatkan semua data plat nomor
@app.route('/api/plates', methods=['GET'])
def get_plates():
    try:
        plates = LicensePlate.query.order_by(LicensePlate.detection_time.desc()).all()
        
        result = []
        for plate in plates:
            plate_data = {
                'id': plate.id,
                'plate_number': plate.plate_number,
                'prefix': plate.prefix,
                'numbers': plate.numbers,
                'suffix': plate.suffix,
                'detection_time': plate.detection_time.strftime('%Y-%m-%d %H:%M:%S'),
                'confidence': plate.confidence
            }
            
            # Tambahkan data pajak jika ada
            if plate.tax_info:
                plate_data['tax_info'] = {
                    'brand': plate.tax_info.brand,
                    'model': plate.tax_info.model,
                    'year': plate.tax_info.year,
                    'tax_amount': plate.tax_info.tax_amount,
                    'tax_due_date': plate.tax_info.tax_due_date,
                    'status': plate.tax_info.status
                }
            
            result.append(plate_data)
        
        return jsonify({
            'success': True,
            'count': len(result),
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching data: {str(e)}'
        }), 500

# Endpoint untuk mendapatkan detail plat nomor berdasarkan ID
@app.route('/api/plate/<int:plate_id>', methods=['GET'])
def get_plate_detail(plate_id):
    try:
        plate = LicensePlate.query.get(plate_id)
        
        if not plate:
            return jsonify({
                'success': False,
                'message': 'Plate not found'
            }), 404
            
        plate_data = {
            'id': plate.id,
            'plate_number': plate.plate_number,
            'prefix': plate.prefix,
            'numbers': plate.numbers,
            'suffix': plate.suffix,
            'detection_time': plate.detection_time.strftime('%Y-%m-%d %H:%M:%S'),
            'confidence': plate.confidence
        }
        
        # Tambahkan data pajak jika ada
        if plate.tax_info:
            plate_data['tax_info'] = {
                'brand': plate.tax_info.brand,
                'model': plate.tax_info.model,
                'year': plate.tax_info.year,
                'tax_amount': plate.tax_info.tax_amount,
                'tax_due_date': plate.tax_info.tax_due_date,
                'status': plate.tax_info.status
            }
        
        return jsonify({
            'success': True,
            'data': plate_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching data: {str(e)}'
        }), 500

# Endpoint untuk mencari plat nomor
@app.route('/api/search', methods=['GET'])
def search_plate():
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
            
        plates = LicensePlate.query.filter(
            LicensePlate.plate_number.like(f'%{query}%')
        ).order_by(LicensePlate.detection_time.desc()).all()
        
        result = []
        for plate in plates:
            plate_data = {
                'id': plate.id,
                'plate_number': plate.plate_number,
                'detection_time': plate.detection_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if plate.tax_info:
                plate_data['brand'] = plate.tax_info.brand
                plate_data['tax_due_date'] = plate.tax_info.tax_due_date
            
            result.append(plate_data)
        
        return jsonify({
            'success': True,
            'count': len(result),
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error searching data: {str(e)}'
        }), 500

# Inisialisasi database
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")

if __name__ == '__main__':
    init_db()  # Membuat tabel jika belum ada
    app.run(debug=True, host='0.0.0.0', port=5000)