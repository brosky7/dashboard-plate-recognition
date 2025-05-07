# Impor library yang diperlukan
import os
import sys
import json
import re
import datetime
from client_api import PlateDetectionAPI

# Fungsi untuk mengintegrasikan kode deteksi plat dengan API
def integrate_api_with_detection_app():
    """
    Fungsi ini berisi kode yang perlu ditambahkan ke aplikasi utama Anda
    untuk mengintegrasikan dengan backend Flask API
    """
    # Inisialisasi API client
    api_client = PlateDetectionAPI(base_url="http://localhost:5000")
    
    # Fungsi ini akan dipanggil setelah deteksi plat dan mendapatkan data pajak
    def save_detection_result(plate_parts, tax_info):
        """
        Menyimpan hasil deteksi plat dan informasi pajak ke database
        
        Args:
            plate_parts (dict): Data plat nomor {'prefix': 'AB', 'numbers': '1234', 'suffix': 'CD'}
            tax_info (dict): Informasi pajak dari Samsat
        """
        if not plate_parts:
            print("No plate data to save")
            return
        
        # Siapkan data plat untuk disimpan
        plate_number = f"{plate_parts['prefix']}{plate_parts['numbers']}{plate_parts['suffix']}"
        plate_data = {
            "plate_number": plate_number,
            "prefix": plate_parts['prefix'],
            "numbers": plate_parts['numbers'],
            "suffix": plate_parts['suffix'],
            "confidence": 0.95  # Nilai confidence bisa diambil dari hasil deteksi YOLO
        }
        
        # Siapkan data pajak jika tersedia
        tax_data = None
        if tax_info and isinstance(tax_info, dict):
            tax_data = {
                "brand": tax_info.get('Merk', ''),
                "model": tax_info.get('Model', ''), 
                "year": tax_info.get('Tahun', ''),
                "tax_amount": tax_info.get('TOTAL PAJAK', ''),
                "tax_due_date": tax_info.get('TGL AKHIR PKB', ''),
                "status": "Lunas" if tax_info.get('STATUS', '').lower() == 'lunas' else "Belum Lunas"
            }
        
        # Kirim data ke server
        result = api_client.save_plate_data(plate_data, tax_data)
        
        if result.get('success'):
            print(f"Data saved successfully with ID: {result.get('plate_id')}")
            return result.get('plate_id')
        else:
            print(f"Failed to save data: {result.get('message')}")
            return None
    
    return save_detection_result

# # Contoh penggunaan
# if __name__ == "__main__":
#     # Contoh data plat dan pajak
#     plate_parts = {
#         "prefix": "AB",
#         "numbers": "1234",
#         "suffix": "CD"
#     }
    
#     tax_info = {
#         "Nopol": "AB 1234 CD",
#         "Merk": "Toyota",
#         "Model": "Avanza",
#         "Tahun": "2020",
#         "TOTAL PAJAK": "Rp 1.500.000",
#         "TGL AKHIR PKB": "2023-12-31",
#         "STATUS": "Lunas"
#     }
    
#     # Mendapatkan fungsi save_detection_result
#     save_detection_result = integrate_api_with_detection_app()
    
#     # Test fungsi
#     plate_id = save_detection_result(plate_parts, tax_info)
#     print(f"Saved plate ID: {plate_id}")