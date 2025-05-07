import cv2
from ultralytics import YOLO
import requests
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from tkinter import Label, Button, Entry, StringVar, Frame, messagebox, Toplevel, ttk
from paddleocr import PaddleOCR
import re
from bs4 import BeautifulSoup
import time
import threading
import os
import datetime

# Import API client untuk terhubung dengan backend Flask
from client_api import PlateDetectionAPI

# Configuration for video source and detection model
# RTSP_URL = "rtsp://admin:Gsicctv321@192.168.0.2:554/Streaming/Channels/102" # Use Router
RTSP_URL = "rtsp://admin:Gsicctv321@192.168.1.2:554/Streaming/Channels/102" # Use LAN cable
# CAPTURE_URL = "http://admin:Gsicctv321@192.168.0.2/ISAPI/Streaming/channels/1/picture" # Use Router
CAPTURE_URL = "http://admin:Gsicctv321@192.168.1.2/ISAPI/Streaming/channels/1/picture" # Use LAN cable

MODEL_PATH = "C:\\Imam\\tes_cctv\\capture\\best.pt"

# Inisialisasi API client
api_client = PlateDetectionAPI(base_url="http://localhost:5000")

# Enhanced RTSPStream class for H.265 streams
class RTSPStream:
    def __init__(self, rtsp_url, retry_interval=3):
        self.rtsp_url = rtsp_url
        self.frame = None
        self.last_frame = None
        self.stopped = False
        self.retry_interval = retry_interval
        self.last_frame_time = time.time()
        self.connection_status = "Connecting..."
        
        # Set environment variables to control FFmpeg behavior
        # os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,rtp,udp,tcp,rtsp|fflags;nobuffer|rtsp_transport;tcp"
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,rtp,udp,tcp,rtsp|fflags;nobuffer|rtsp_transport;tcp|max_delay;500000"
        
        # Start the stream thread
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def create_capture(self):
        """Create and configure the capture object with optimized settings for H.265"""
        try:
            # Use TCP for RTSP transport - more reliable but slightly higher latency
            capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # Critical settings for H.265 streams
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Smallest buffer possible
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H265'))  # Explicitly set H.265 codec
            
            # Additional settings for better performance
            capture.set(cv2.CAP_PROP_FPS, 15)  # Limit FPS to reduce processing load
            
            if not capture.isOpened():
                self.connection_status = "Failed to open stream"
                print("Failed to open stream!")
                return None
                
            self.connection_status = "Connected"
            return capture
        except Exception as e:
            self.connection_status = f"Error: {str(e)}"
            print(f"Error creating capture: {str(e)}")
            return None

    def update(self):
        """Thread method to continuously read frames"""
        while not self.stopped:
            try:
                # Create or recreate capture if needed
                if not hasattr(self, 'capture') or self.capture is None:
                    self.capture = self.create_capture()
                    if self.capture is None:
                        time.sleep(self.retry_interval)
                        continue
                
                # Try to read a frame
                ret, frame = self.capture.read()
                
                # Update the last frame time if successful
                current_time = time.time()
                
                if ret:
                    self.frame = frame
                    self.last_frame = frame
                    self.last_frame_time = current_time
                    self.connection_status = "Connected"
                else:
                    # If we haven't received a frame for more than 5 seconds, try to reconnect
                    if current_time - self.last_frame_time > 5:
                        self.connection_status = "Reconnecting..."
                        print("No frames received for 5 seconds, reconnecting...")
                        if hasattr(self, 'capture') and self.capture is not None:
                            self.capture.release()
                        self.capture = None
                        time.sleep(self.retry_interval)
            
            except Exception as e:
                self.connection_status = f"Error: {str(e)}"
                print(f"Error reading frame: {str(e)}")
                # Release the capture and retry
                if hasattr(self, 'capture') and self.capture is not None:
                    self.capture.release()
                self.capture = None
                time.sleep(self.retry_interval)

    def get_frame(self):
        """Return the most recent frame"""
        return self.frame
    
    def get_status(self):
        """Return the current connection status"""
        return self.connection_status

    def stop(self):
        """Stop the thread and release resources"""
        self.stopped = True
        if hasattr(self, 'capture') and self.capture is not None:
            self.capture.release()

# Load YOLO model
try:
    model = YOLO(MODEL_PATH)
    print("SUKSES YOLO")
except Exception as e:
    print(f"Error loading YOLO model: {str(e)}")
    model = None

# Initialize OCR
try:
    ocr = PaddleOCR()
except Exception as e:
    print(f"Error initializing PaddleOCR: {str(e)}")
    ocr = None

# Initialize RTSP stream
stream = RTSPStream(RTSP_URL)

# Colors
DARK_BLUE = "#002D72"
TEAL = "#009688"
WHITE = "#FFFFFF"
LIGHT_GRAY = "#F0F0F0"
GRAY = "#808080"
GREEN = "#4CAF50"
RED = "#F44336"
BLUE = "#2196F3"
PURPLE = "#9C27B0"

# Ukuran fixed untuk video streams
STREAM_WIDTH = 640
STREAM_HEIGHT = 480
DETECTION_WIDTH = 400
DETECTION_HEIGHT = 300

# GUI Setup
root = tk.Tk()
root.title("Sistem Deteksi Plat Nomor")

# Current active page
current_page = "beranda"

# Membuat fullscreen saat dibuka
root.state('zoomed')
width = root.winfo_screenwidth()
height = root.winfo_screenheight()
root.geometry(f"{width}x{height}+0+0")

# Main frame sebagai container untuk semua komponen
main_frame = Frame(root)
main_frame.pack(fill="both", expand=True)

# Sidebar frame di sebelah kiri
sidebar_frame = Frame(main_frame, bg=DARK_BLUE, width=170)
sidebar_frame.pack(side="left", fill="y")
sidebar_frame.pack_propagate(False)  # Mencegah frame menyusut ke size kontennya

# Logo atau judul aplikasi
app_title = Label(sidebar_frame, text="Sistem\nCek Pajak\nKendaraan", font=("Arial", 16, "bold"), bg=DARK_BLUE, fg=WHITE)
app_title.pack(pady=20)

# Content frame di sebelah kanan - akan berisi beranda_frame dan riwayat_frame
content_frame = Frame(main_frame, bg=WHITE)
content_frame.pack(side="right", fill="both", expand=True)

# Frame untuk halaman beranda
beranda_frame = Frame(content_frame, bg=WHITE)

# Frame untuk halaman riwayat
riwayat_frame = Frame(content_frame, bg=WHITE)

# Variabel untuk menyimpan data plat dan pajak terkini
current_plate_parts = None
current_tax_info = None

# Last error frame counter
last_frame_error_count = 0
last_frame_time = time.time()

# Status message yang akan digunakan oleh kedua halaman
status_message = Label(content_frame, text="Ready", font=("Arial", 10), fg="blue", bg=WHITE)
status_message.pack(side="bottom", anchor="w", padx=20, pady=5)

def update_status(message, color="blue"):
    """Update status message with optional color"""
    status_message.config(text=message, fg=color)
    root.update_idletasks()

def extract_license_plate(text):
    """
    Extract only the license plate number from OCR results using regex.
    Indonesian license plate format: AB1234CD
    """
    pattern = r'([A-Z]{1,2})\.?(\d{1,4})\.?([A-Z0-9]{1,3})'  # Indonesian license plate pattern
    match = re.search(pattern, text)
    if match:
        return {
            'prefix': match.group(1),      # AB
            'numbers': match.group(2),     # 1234
            'suffix': match.group(3)       # CD
        }
    return None

def convert_numbers_to_letters(text):
    """
    Convert common number-to-letter confusions in OCR:
    0->O, 1->I, 2->Z, 4->A, 5->S, 6->G, 8->B
    """
    replacements = {
        '0': 'O',
        '1': 'I',
        '2': 'Z',
        '4': 'A',
        '5': 'S',
        '6': 'G',
        '8': 'B'
    }
    
    return ''.join(replacements.get(char, char) for char in text)

def show_beranda():
    """Show beranda (home) page"""
    global current_page
    
    # Update button colors
    beranda_button.config(bg=TEAL)
    riwayat_button.config(bg=DARK_BLUE)
    
    # Hide riwayat frame
    riwayat_frame.pack_forget()
    
    # Show beranda frame
    beranda_frame.pack(fill="both", expand=True)
    
    # Update current page
    current_page = "beranda"
    
    # Resume stream updates if we're coming back from riwayat page
    update_stream()

def show_riwayat():
    """Show riwayat (history) page"""
    global current_page
    
    # Update button colors
    beranda_button.config(bg=DARK_BLUE)
    riwayat_button.config(bg=TEAL)
    
    # Hide beranda frame
    beranda_frame.pack_forget()
    
    # Show riwayat frame and refresh data
    riwayat_frame.pack(fill="both", expand=True)
    refresh_history_data()
    
    # Update current page
    current_page = "riwayat"

# Setup menu buttons in sidebar
beranda_button = Button(sidebar_frame, text="Beranda", bg=TEAL, fg=WHITE, 
                       font=("Arial", 14), bd=0, activebackground=TEAL, activeforeground=WHITE, 
                       width=15, anchor="w", padx=10, command=show_beranda)
beranda_button.pack(fill="x", pady=2)

riwayat_button = Button(sidebar_frame, text="Riwayat", bg=DARK_BLUE, fg=WHITE, 
                       font=("Arial", 14), bd=0, activebackground=TEAL, activeforeground=WHITE, 
                       width=15, anchor="w", padx=10, command=show_riwayat)
riwayat_button.pack(fill="x", pady=2)

# -------- SETUP BERANDA PAGE --------

# Header dengan judul halaman
header_frame = Frame(beranda_frame, bg=WHITE)
header_frame.pack(fill="x", padx=20, pady=10)

# Frame untuk konten utama (terbagi menjadi 2 kolom)
main_content = Frame(beranda_frame, bg=WHITE)
main_content.pack(fill="both", expand=True, padx=20, pady=10)

# Kolom kiri - Stream dan deteksi
left_column = Frame(main_content, bg=WHITE)
left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

# Kolom kanan - Hasil dan info
right_column = Frame(main_content, bg=WHITE)
right_column.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=10)

# Frame untuk video stream dengan ukuran fixed
stream_frame = Frame(left_column, bg=LIGHT_GRAY, bd=1, relief="solid", width=STREAM_WIDTH, height=STREAM_HEIGHT)
stream_frame.pack(fill="both", expand=True)
stream_frame.pack_propagate(False)  # Mencegah frame mengubah ukuran mengikuti kontennya

frame_stream = Label(stream_frame)
frame_stream.pack(fill="both", expand=True, padx=1, pady=1)

# Stream status
stream_status_frame = Frame(left_column, bg=WHITE)
stream_status_frame.pack(fill="x", pady=5)

stream_status_label = Label(stream_status_frame, text="Status Stream:", font=("Arial", 10), bg=WHITE)
stream_status_label.pack(side="left")

stream_status = Label(stream_status_frame, text="Connecting...", font=("Arial", 10), fg="blue", bg=WHITE)
stream_status.pack(side="left", padx=5)

# Buttons frame
buttons_frame = Frame(left_column, bg=WHITE)
buttons_frame.pack(fill="x", pady=5)

# Right column - Hasil Foto dan Informasi
hasil_title = Label(right_column, text="Hasil Foto", font=("Arial", 16, "bold"), bg=WHITE)
hasil_title.pack(anchor="w", pady=5)

# Frame for detection results dengan ukuran fixed
frame_detection_container = Frame(right_column, bg=LIGHT_GRAY, bd=1, relief="solid", width=DETECTION_WIDTH, height=DETECTION_HEIGHT)
frame_detection_container.pack(fill="x", pady=5)
frame_detection_container.pack_propagate(False)  # Mencegah frame mengubah ukuran mengikuti kontennya

frame_detection = Label(frame_detection_container)
frame_detection.pack(fill="both", expand=True, padx=1, pady=1)

# Label untuk OCR results
ocr_frame = Frame(right_column, bg=WHITE)
ocr_frame.pack(fill="x", pady=5)

label_ocr = Label(ocr_frame, text="Plat Nomor: ", font=("Arial", 14, "bold"), bg=WHITE)
label_ocr.pack(anchor="w")

# Frame for OCR correction
correction_frame = Frame(right_column, bg=WHITE)
correction_frame.pack(fill="x", pady=5)

correction_label = Label(correction_frame, text="Koreksi Plat Nomor", font=("Arial", 12), bg=WHITE)
correction_label.pack(anchor="w")

correction_entry = Entry(correction_frame, font=("Arial", 12), width=20)
correction_entry.pack(side="left", pady=5)

# Frame untuk informasi kendaraan
tax_frame = Frame(right_column, bg=WHITE, bd=1, relief="solid")
tax_frame.pack(fill="x", pady=10)

tax_title = Label(tax_frame, text="Informasi Kendaraan", font=("Arial", 14, "bold"), bg=WHITE)
tax_title.pack(anchor="w", padx=10, pady=5)

tax_info_frame = Frame(tax_frame, bg=WHITE)
tax_info_frame.pack(fill="both", expand=True, padx=10, pady=5)

# Create labels for tax information with new styling
label_nopol = Label(tax_info_frame, text="Nopol:", font=("Arial", 12), bg=WHITE)
label_nopol.grid(row=0, column=0, sticky="w", pady=2)

label_brand = Label(tax_info_frame, text="Merk:", font=("Arial", 12), bg=WHITE)
label_brand.grid(row=1, column=0, sticky="w", pady=2)

label_model = Label(tax_info_frame, text="Model:", font=("Arial", 12), bg=WHITE)
label_model.grid(row=2, column=0, sticky="w", pady=2)

label_year = Label(tax_info_frame, text="Tahun:", font=("Arial", 12), bg=WHITE)
label_year.grid(row=3, column=0, sticky="w", pady=2)

label_tax_amount = Label(tax_info_frame, text="Total Pajak:", font=("Arial", 12, "bold"), bg=WHITE)
label_tax_amount.grid(row=4, column=0, sticky="w", pady=2)

label_tax_due = Label(tax_info_frame, text="Tanggal Akhir PKB:", font=("Arial", 12, "bold"), bg=WHITE)
label_tax_due.grid(row=5, column=0, sticky="w", pady=2)

# Value labels
label_nopol_value = Label(tax_info_frame, text="-", font=("Arial", 12), bg=WHITE)
label_nopol_value.grid(row=0, column=1, sticky="w", pady=2, padx=10)

label_brand_value = Label(tax_info_frame, text="-", font=("Arial", 12), bg=WHITE)
label_brand_value.grid(row=1, column=1, sticky="w", pady=2, padx=10)

label_model_value = Label(tax_info_frame, text="-", font=("Arial", 12), bg=WHITE)
label_model_value.grid(row=2, column=1, sticky="w", pady=2, padx=10)

label_year_value = Label(tax_info_frame, text="-", font=("Arial", 12), bg=WHITE)
label_year_value.grid(row=3, column=1, sticky="w", pady=2, padx=10)

label_tax_amount_value = Label(tax_info_frame, text="-", font=("Arial", 12, "bold"), bg=WHITE)
label_tax_amount_value.grid(row=4, column=1, sticky="w", pady=2, padx=10)

label_tax_due_value = Label(tax_info_frame, text="-", font=("Arial", 12, "bold"), bg=WHITE)
label_tax_due_value.grid(row=5, column=1, sticky="w", pady=2, padx=10)

# -------- SETUP RIWAYAT PAGE --------

# Header untuk halaman riwayat
riwayat_header = Label(riwayat_frame, text="Riwayat Deteksi Plat Nomor", font=("Arial", 18, "bold"), bg=WHITE)
riwayat_header.pack(anchor="w", padx=20, pady=15)

# Frame untuk tabel riwayat
riwayat_table_frame = Frame(riwayat_frame, bg=WHITE)
riwayat_table_frame.pack(fill="both", expand=True, padx=20, pady=10)

# Saat mendefinisikan Treeview di halaman Riwayat
columns = ("id", "plate_number", "detection_time", "brand", "model", "tax_amount", "tax_due_date")
riwayat_tree = ttk.Treeview(riwayat_table_frame, columns=columns, show="headings", height=20)

# Define headings dengan anchor="w" untuk rata kiri
riwayat_tree.heading("id", text="ID", anchor="w")
riwayat_tree.heading("plate_number", text="Plat Nomor", anchor="w")
riwayat_tree.heading("detection_time", text="Jam Kunjungan", anchor="w")
riwayat_tree.heading("brand", text="Merk", anchor="w")
riwayat_tree.heading("model", text="Model", anchor="w")
riwayat_tree.heading("tax_amount", text="Jumlah Pajak", anchor="w")
riwayat_tree.heading("tax_due_date", text="Tanggal Akhir PKB", anchor="w")

# Define column widths dan juga set anchor="w" untuk isi kolom
riwayat_tree.column("id", width=50, anchor="w")
riwayat_tree.column("plate_number", width=120, anchor="w")
riwayat_tree.column("detection_time", width=150, anchor="w")
riwayat_tree.column("brand", width=100, anchor="w")
riwayat_tree.column("model", width=100, anchor="w")
riwayat_tree.column("tax_amount", width=120, anchor="w")
riwayat_tree.column("tax_due_date", width=120, anchor="w")

# Add a scrollbar
riwayat_scrollbar = ttk.Scrollbar(riwayat_table_frame, orient="vertical", command=riwayat_tree.yview)
riwayat_tree.configure(yscrollcommand=riwayat_scrollbar.set)
riwayat_scrollbar.pack(side="right", fill="y")
riwayat_tree.pack(side="left", fill="both", expand=True)

# Refresh button for history
refresh_frame = Frame(riwayat_frame, bg=WHITE)
refresh_frame.pack(fill="x", padx=20, pady=10)

refresh_button = Button(refresh_frame, text="Refresh", command=None, 
                      bg=BLUE, fg=WHITE, font=("Arial", 10, "bold"), width=10)
refresh_button.pack(side="left")

# -------- BERANDA FUNCTIONS --------

def update_stream():
    """Update video stream with threaded frame capture"""
    global last_frame_error_count, last_frame_time
    
    # Only update if beranda page is active
    if current_page != "beranda":
        return
    
    # Update stream status
    stream_status_text = f"Connected" if stream.get_status() == "Connected" else stream.get_status()
    stream_status.config(text=stream_status_text)
    
    # Get frame from stream
    frame = stream.get_frame()
    
    if frame is not None:
        # Reset error counter when we get a valid frame
        last_frame_error_count = 0
        last_frame_time = time.time()
        
        try:
            # Convert frame to display in tkinter with FIXED size
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((STREAM_WIDTH, STREAM_HEIGHT), Image.LANCZOS)  # Use FIXED size
            img = ImageTk.PhotoImage(img)
            frame_stream.config(image=img)
            frame_stream.image = img
        except Exception as e:
            print(f"Error converting frame: {str(e)}")
    else:
        # Count consecutive frame errors
        current_time = time.time()
        if current_time - last_frame_time > 1:  # Only count as error if it's been more than a second
            last_frame_error_count += 1
            last_frame_time = current_time
            
        if last_frame_error_count > 10:
            # If we've had many errors, try to show a "No Signal" message
            try:
                no_signal_img = Image.new('RGB', (STREAM_WIDTH, STREAM_HEIGHT), color=(0, 0, 0))
                draw = ImageDraw.Draw(no_signal_img)
                draw.text((STREAM_WIDTH//2-50, STREAM_HEIGHT//2), "No Signal", fill=(255, 255, 255))
                no_signal_tk = ImageTk.PhotoImage(no_signal_img)
                frame_stream.config(image=no_signal_tk)
                frame_stream.image = no_signal_tk
            except Exception:
                # If PIL DrawText fails, just pass
                pass
    
    # Schedule the next update if still on beranda page
    if current_page == "beranda":
        root.after(33, update_stream)  # Approximately 30 FPS

def save_to_database():
    """Save current detection data to database"""
    global current_plate_parts, current_tax_info
    
    if not current_plate_parts:
        messagebox.showwarning("Warning", "No plate detected yet!")
        return
    
    try:
        # Prepare plate data
        plate_number = f"{current_plate_parts['prefix']}{current_plate_parts['numbers']}{current_plate_parts['suffix']}"
        plate_data = {
            "plate_number": plate_number,
            "prefix": current_plate_parts['prefix'],
            "numbers": current_plate_parts['numbers'],
            "suffix": current_plate_parts['suffix'],
            "confidence": current_plate_parts.get('confidence', 0.95)  # Use stored confidence if available
        }
        
        # Prepare tax data if available
        tax_data = None
        if current_tax_info:
            tax_data = {
                "brand": current_tax_info.get('Merk', ''),
                "model": current_tax_info.get('Model', ''),
                "year": current_tax_info.get('Tahun', ''),
                "tax_amount": current_tax_info.get('TOTAL PAJAK', ''),
                "tax_due_date": current_tax_info.get('TGL AKHIR PKB', ''),
                "status": "Lunas" if current_tax_info.get('STATUS', '').lower() == 'lunas' else "Belum Lunas"
            }
        
        # Save data to database via API
        result = api_client.save_plate_data(plate_data, tax_data)
        
        if result.get('success'):
            update_status(f"Data saved to database with ID: {result.get('plate_id')}", "green")
            messagebox.showinfo("Success", f"Data successfully saved to database with ID: {result.get('plate_id')}")
        else:
            update_status(f"Failed to save data: {result.get('message')}", "red")
            messagebox.showerror("Error", f"Failed to save data: {result.get('message')}")
    except Exception as e:
        update_status(f"Error saving data: {str(e)}", "red")
        messagebox.showerror("Error", f"Error saving data: {str(e)}")

def apply_correction():
    """
    Function to apply manual correction from user and check tax info.
    """
    global current_plate_parts, current_tax_info
    
    corrected_text = correction_entry.get().strip().upper()
    if corrected_text:
        label_ocr.config(text=f"Plat Nomor: {corrected_text}")
        update_status("Processing corrected plate...")
        
        # Process the corrected plate and check tax
        plate_parts = extract_license_plate(corrected_text)
        if plate_parts:
            # Apply the number-to-letter correction in the UI for clarity
            original_suffix = plate_parts['suffix']
            corrected_suffix = convert_numbers_to_letters(original_suffix)
            
            # If correction changed something, show it to the user
            if original_suffix != corrected_suffix:
                plate_parts['suffix'] = corrected_suffix
                corrected_full = f"{plate_parts['prefix']}{plate_parts['numbers']}{corrected_suffix}"
                label_ocr.config(text=f"Plat Nomor: {corrected_full}")
            
            # Update current plate parts for saving to database
            current_plate_parts = plate_parts
            
            # Check tax info
            check_tax_info(plate_parts)
        else:
            messagebox.showwarning("Warning", "Invalid license plate format.")
    else:
        messagebox.showwarning("Warning", "Please enter valid license plate text.")

def reset_all():
    """
    Function to reset capture results and OCR
    """
    global current_plate_parts, current_tax_info
    
    # Reset detection image
    frame_detection.config(image='')
    frame_detection.image = None
    
    # Reset OCR text
    label_ocr.config(text="Plat Nomor: ")
    
    # Reset correction entry
    correction_entry.delete(0, tk.END)
    
    # Reset tax information
    reset_tax_info()
    
    # Reset current data
    current_plate_parts = None
    current_tax_info = None
    
    update_status("All results have been reset")

def reset_tax_info():
    """Reset all tax information fields"""
    label_nopol_value.config(text="-")
    label_brand_value.config(text="-")
    label_model_value.config(text="-")
    label_year_value.config(text="-")
    label_tax_amount_value.config(text="-")
    label_tax_due_value.config(text="-")

def set_not_found_data(message):
    """Helper function to set all tax information fields to the given message"""
    label_nopol_value.config(text=message)
    label_brand_value.config(text=message)
    label_model_value.config(text=message)
    label_year_value.config(text=message)
    label_tax_amount_value.config(text=message)
    label_tax_due_value.config(text=message)

def check_tax_info(plate_parts):
    """Check tax info from Samsat Sleman API with number-to-letter correction."""
    global current_tax_info
    
    plate_number = plate_parts['numbers']
    plate_suffix = plate_parts['suffix']
    
    # Apply number-to-letter correction to the suffix part
    corrected_suffix = convert_numbers_to_letters(plate_suffix)
    
    update_status(f"Checking tax info for {plate_number}-{corrected_suffix}...")

    try:
        url = "https://samsatsleman.jogjaprov.go.id/cek/pages/getpajak"
        post_data = {
            "nomer": plate_number,
            "kode_belakang": corrected_suffix
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://samsatsleman.jogjaprov.go.id/cek/pajak"
        }

        # Send POST request
        response = requests.post(url, data=post_data, headers=headers)

        print("post_data:", post_data)
        print("response:", response.text)

        if response.status_code != 200:
            update_status(f"Failed to submit tax query: {response.status_code}", "red")
            return
        
        # Check if response is empty or no tax table
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='table table-bordered')

        if not table:
            # Handle case when no table is found
            update_status("No tax information found", "orange")
            # Set all tax information fields to "Data Kendaraan Tidak Ditemukan!"
            not_found_message = "Data Kendaraan Tidak Ditemukan!"
            set_not_found_data(not_found_message)
            current_tax_info = None
            return
        
        # Check for the specific "Data Tidak ditemukan!" message format
        data_not_found_cell = table.find('td', string="Data Tidak ditemukan!")
        if data_not_found_cell or "Data Tidak ditemukan!" in table.text:
            update_status("Vehicle data not found", "orange")
            not_found_message = "Data Kendaraan Tidak Ditemukan!"
            set_not_found_data(not_found_message)
            current_tax_info = None
            return

        # Get tax data from table
        tax_info = {}
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                tax_info[key] = value

        # Save current tax info for database
        current_tax_info = tax_info
                
        # Update GUI
        label_nopol_value.config(text=tax_info.get('Nopol', '-'))
        label_brand_value.config(text=tax_info.get('Merk', '-'))
        label_model_value.config(text=tax_info.get('Model', '-'))
        label_year_value.config(text=tax_info.get('Tahun', '-'))
        label_tax_amount_value.config(text=tax_info.get('TOTAL PAJAK', '-'))
        label_tax_due_value.config(text=tax_info.get('TGL AKHIR PKB', '-'))

        update_status("Tax information retrieved successfully", "green")

    except Exception as e:
        update_status(f"Error checking tax info: {str(e)}", "red")
        print(f"Error: {str(e)}")
        # Also set to "Data Kendaraan Tidak Ditemukan!" on exception
        not_found_message = "Data Kendaraan Tidak Ditemukan!"
        set_not_found_data(not_found_message)
        current_tax_info = None
def capture_and_detect():
    """Capture and detect license plates"""
    global current_plate_parts, current_tax_info
    
    if model is None:
        update_status("Error: YOLO model not loaded!", "red")
        messagebox.showerror("Error", "YOLO model not loaded. Please check your model path and dependencies.")
        return
        
    if ocr is None:
        update_status("Error: OCR engine not initialized!", "red")
        messagebox.showerror("Error", "OCR engine not initialized. Please check PaddleOCR installation.")
        return
    
    update_status("Capturing image...")
    try:
        # Try to get a frame from the stream first (faster than making a new HTTP request)
        frame = stream.get_frame()
        
        # If we don't have a frame from the stream, use HTTP snapshot as fallback
        if frame is None:
            response = requests.get(CAPTURE_URL, auth=('admin', 'Gsicctv321'), stream=True)
            if response.status_code == 200:
                img_array = np.array(bytearray(response.content), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            else:
                update_status(f"Failed to capture image: {response.status_code}", "red")
                return
        else:
            # Use the frame from the stream
            img = frame.copy()
        
        # Tampilkan hasil capture terlebih dahulu (tanpa bounding box)
        capture_img = img.copy()
        capture_rgb = cv2.cvtColor(capture_img, cv2.COLOR_BGR2RGB)
        capture_pil = Image.fromarray(capture_rgb)
        capture_pil = capture_pil.resize((DETECTION_WIDTH, DETECTION_HEIGHT), Image.LANCZOS)
        capture_tk = ImageTk.PhotoImage(capture_pil)
        frame_detection.config(image=capture_tk)
        frame_detection.image = capture_tk
        
        update_status("Running YOLO detection...")
        plate_texts = []
        plate_parts_list = []
        detection_confidence = 0.0
        
        try:
            # Deteksi dengan YOLO dengan penanganan error
            results = model(img)
            
            if results is not None and hasattr(results, '__iter__'):
                for result in results:
                    if hasattr(result, 'boxes') and len(result.boxes) > 0:
                        for box in result.boxes:
                            try:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])  # Access bbox coordinates
                                conf = box.conf[0].item()  # Access confidence score
                                cls = int(box.cls[0].item())  # Access class ID
                                
                                # Save confidence for database
                                detection_confidence = conf
                                
                                # Draw detection box - penting untuk ditampilkan
                                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(img, f"{model.names[cls]}: {conf:.2f}", (x1, y1 - 10),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                                
                                # Extract license plate region
                                if y1 < y2 and x1 < x2 and y1 >= 0 and x1 >= 0 and y2 < img.shape[0] and x2 < img.shape[1]:
                                    plate_region = img[y1:y2, x1:x2]
                                    
                                    # Skip if region is too small
                                    if plate_region.size == 0:
                                        continue
                                        
                                    plate_region_gray = cv2.cvtColor(plate_region, cv2.COLOR_BGR2GRAY)
                                    
                                    update_status("Running OCR...")
                                    # Run OCR with penanganan error
                                    try:
                                        ocr_result = ocr.ocr(plate_region_gray, cls=True)
                                        if ocr_result is not None:
                                            for res in ocr_result:
                                                if res is not None:
                                                    for line in res:
                                                        if line and len(line) > 1 and line[1] and len(line[1]) > 0:
                                                            raw_text = line[1][0]  # Get OCR text result
                                                            plate_parts = extract_license_plate(raw_text)  # Clean with regex
                                                            if plate_parts:
                                                                full_plate = f"{plate_parts['prefix']}{plate_parts['numbers']}{plate_parts['suffix']}"
                                                                plate_texts.append(full_plate)
                                                                plate_parts_list.append(plate_parts)
                                    except Exception as ocr_error:
                                        print(f"OCR error: {str(ocr_error)}")
                                        # Continue despite OCR error
                            except Exception as box_error:
                                print(f"Box processing error: {str(box_error)}")
                                # Continue processing other boxes
        
        except Exception as detection_error:
            print(f"Detection error: {str(detection_error)}")
            update_status("Detection error, but image captured", "orange")
            # Continue with the function, don't return

        # Display filtered OCR text results
        if plate_texts:
            detected_text_list = []
            corrected_plate_parts_list = []
            for plate_parts in plate_parts_list:
                original_suffix = plate_parts['suffix']
                corrected_suffix = convert_numbers_to_letters(original_suffix)
                
                # If correction changed something, modify the plate parts
                if original_suffix != corrected_suffix:
                    plate_parts['suffix'] = corrected_suffix
                
                full_plate = f"{plate_parts['prefix']}{plate_parts['numbers']}{plate_parts['suffix']}"
                detected_text_list.append(full_plate)
                corrected_plate_parts_list.append(plate_parts)
            
            detected_text = detected_text_list[0]
            label_ocr.config(text=f"Plat Nomor: {detected_text}")
            # Fill correction entry with corrected OCR result for easy correction
            correction_entry.delete(0, tk.END)
            correction_entry.insert(0, detected_text)  # Insert first corrected OCR result to entry
            
            # Update current plate parts for database saving
            current_plate_parts = corrected_plate_parts_list[0]
            current_plate_parts['confidence'] = detection_confidence
            
            # Check tax information for the first detected plate
            update_status("Checking tax information...")
            check_tax_info(corrected_plate_parts_list[0])

            # Convert and display detection result image with bounding boxes
            img_with_boxes = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_with_boxes = Image.fromarray(img_with_boxes)
            img_with_boxes = img_with_boxes.resize((DETECTION_WIDTH, DETECTION_HEIGHT), Image.LANCZOS)
            img_with_boxes = ImageTk.PhotoImage(img_with_boxes)
            frame_detection.config(image=img_with_boxes)
            frame_detection.image = img_with_boxes
        else:
            label_ocr.config(text="Plat Nomor: Not Found")
            correction_entry.delete(0, tk.END)
            update_status("No license plate detected but image captured", "orange")
            current_plate_parts = None
            current_tax_info = None
        
        update_status("Capture complete")
    except Exception as e:
        # Catch any global errors
        update_status(f"Error in capture: {str(e)}", "red")
        print(f"Capture error: {str(e)}")
# -------- RIWAYAT FUNCTIONS --------

def refresh_history_data():
    """Refresh history data in the treeview"""
    try:
        # Clear existing data
        for item in riwayat_tree.get_children():
            riwayat_tree.delete(item)
            
        # Get all plates from database
        update_status("Fetching history data...")
        result = api_client.get_all_plates()
        
        if result.get('success'):
            plates_data = result.get('data', [])
            for plate in plates_data:
                tax_info = plate.get('tax_info', {})
                riwayat_tree.insert("", "end", values=(
                    plate.get('id', ''),
                    plate.get('plate_number', ''),
                    plate.get('detection_time', ''),
                    tax_info.get('brand', '-') if tax_info else '-',
                    tax_info.get('model', '-') if tax_info else '-',
                    tax_info.get('tax_amount', '-') if tax_info else '-',
                    tax_info.get('tax_due_date', '-') if tax_info else '-'
                ))
            update_status(f"Loaded {len(plates_data)} records", "green")
        else:
            update_status(f"Failed to fetch data: {result.get('message')}", "red")
    except Exception as e:
        update_status(f"Error refreshing data: {str(e)}", "red")

# Connect functions to buttons
# Capture button
btn_capture = Button(buttons_frame, text="Capture", width=10, font=("Arial", 10, "bold"), 
                   bg=GREEN, fg=WHITE, command=capture_and_detect)
btn_capture.pack(side="left", padx=5)

# Reset button
btn_reset = Button(buttons_frame, text="Reset", width=10, font=("Arial", 10, "bold"), 
                  bg=RED, fg=WHITE, command=reset_all)
btn_reset.pack(side="left", padx=5)

# Save button
btn_save = Button(buttons_frame, text="Save", width=10, font=("Arial", 10, "bold"), 
                bg=BLUE, fg=WHITE, command=save_to_database)
btn_save.pack(side="left", padx=5)

# Correction button
correction_button = Button(correction_frame, text="Koreksi", command=apply_correction, 
                         bg=DARK_BLUE, fg=WHITE, font=("Arial", 10, "bold"))
correction_button.pack(side="left", padx=5)

# Connect refresh button for history
refresh_button.config(command=refresh_history_data)

# Bind space bar for capture
root.bind('<space>', lambda event: capture_and_detect() if current_page == "beranda" else None)

# Set up proper cleanup handler
def on_closing():
    stream.stop()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

# Show beranda page by default
show_beranda()

# Start main loop
root.mainloop()