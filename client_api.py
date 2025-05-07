import requests
import json

class PlateDetectionAPI:
    """
    Kelas untuk menghubungkan aplikasi deteksi plat dengan backend Flask
    """
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        
    def save_plate_data(self, plate_data, tax_info=None):
        """
        Menyimpan data plat dan informasi pajak ke server
        
        Args:
            plate_data (dict): Data plat nomor
            tax_info (dict, optional): Informasi pajak
            
        Returns:
            dict: Response dari server
        """
        url = f"{self.base_url}/api/plate"
        
        # Menyiapkan data untuk dikirim
        payload = {
            "plate_number": plate_data.get("plate_number", ""),
            "prefix": plate_data.get("prefix", ""),
            "numbers": plate_data.get("numbers", ""),
            "suffix": plate_data.get("suffix", ""),
            "confidence": plate_data.get("confidence", 0.0)
        }
        
        # Tambahkan informasi pajak jika ada
        if tax_info:
            payload["tax_info"] = {
                "brand": tax_info.get("brand", ""),
                "model": tax_info.get("model", ""),
                "year": tax_info.get("year", ""),
                "tax_amount": tax_info.get("tax_amount", ""),
                "tax_due_date": tax_info.get("tax_due_date", ""),
                "status": tax_info.get("status", "")
            }
        
        try:
            response = requests.post(url, json=payload)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_all_plates(self):
        """
        Mendapatkan semua data plat nomor dari server
        
        Returns:
            dict: Response dari server
        """
        url = f"{self.base_url}/api/plates"
        
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_plate_detail(self, plate_id):
        """
        Mendapatkan detail data plat nomor berdasarkan ID
        
        Args:
            plate_id (int): ID plat nomor
            
        Returns:
            dict: Response dari server
        """
        url = f"{self.base_url}/api/plate/{plate_id}"
        
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def search_plate(self, query):
        """
        Mencari plat nomor berdasarkan query
        
        Args:
            query (str): Query pencarian
            
        Returns:
            dict: Response dari server
        """
        url = f"{self.base_url}/api/search?q={query}"
        
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

# # Contoh penggunaan API client
# if __name__ == "__main__":
#     api = PlateDetectionAPI()
    
#     # Contoh menyimpan data plat
#     plate_data = {
#         "plate_number": "AB1234CD",
#         "prefix": "AB",
#         "numbers": "1234",
#         "suffix": "CD",
#         "confidence": 0.95
#     }
    
#     tax_info = {
#         "brand": "Toyota",
#         "model": "Avanza",
#         "year": "2020",
#         "tax_amount": "Rp 1.500.000",
#         "tax_due_date": "2023-12-31",
#         "status": "Lunas"
#     }
    
#     result = api.save_plate_data(plate_data, tax_info)
#     print(result)