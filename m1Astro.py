import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, UnidentifiedImageError
import socket
import threading
import time
import os
import sys
from prot_ble import trigger_remote_control_closest
from prot_http.const_wifi import INET_ADDRESS_CAMERA, UDP_PORT_LIVEVIEW
from prot_http.command_http import *
from prot_http.const_http_cmd_rc_params import *
from urllib3 import PoolManager, HTTPResponse
from urllib3.exceptions import TimeoutError
from typing import Optional
import io
import shutil
import json
import rawpy
from astropy.io import fits
import numpy as np
import requests

class YiM1Controller(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yi M1 Astrophotography Controller")
        self.geometry("1080x800")
        self.configure(bg='lightgrey')

        self.ssid = None
        self.pwd = None
        self.http = PoolManager()
        self.live_view_thread = None
        self.capture_thread = None
        self.live_view_window = None
        self.liveview_label = None
        self.image_counter = 0
        self.connected = False

        self.image_dir = "captured_images"
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

        # Digital zoom factor
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0

        self.create_widgets()

    def create_widgets(self):
        # Create a style for the ttk widgets
        style = ttk.Style(self)
        style.theme_use('clam')

        # Create a Notebook
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)

        # Create Frames for each tab
        control_frame = ttk.Frame(notebook, padding=(10, 5))
        capture_frame = ttk.Frame(notebook, padding=(10, 5))
        gallery_frame = ttk.Frame(notebook, padding=(10, 5))

        notebook.add(control_frame, text="Controls")
        notebook.add(capture_frame, text="Capture")
        notebook.add(gallery_frame, text="Gallery")

        # Connection Section
        connect_frame = ttk.LabelFrame(self, text="Connection", padding=(10, 5))
        connect_frame.pack(fill="x", padx=10, pady=5)

        self.connect_button = ttk.Button(connect_frame, text="Connect", command=self.connect_camera)
        self.connect_button.grid(row=0, column=0, padx=5, pady=5)

        self.reconnect_button = ttk.Button(connect_frame, text="Reconnect - live View", command=self.reconnect_camera)
        self.reconnect_button.grid(row=0, column=1, padx=5, pady=5)
        self.reconnect_button.config(state="disabled")

        self.connection_status_label = tk.Label(connect_frame, text="Not Connected", fg="red", bg='lightgrey')
        self.connection_status_label.grid(row=0, column=2, padx=5, pady=5)

        connect_frame.pack(fill="x", padx=10, pady=5)

        # Parameters Control Section
        parameters_frame = ttk.LabelFrame(control_frame, text="Parameters Control", padding=(10, 5))
        parameters_frame.pack(fill="x", padx=10, pady=5)

        self.parameters = {
            "Exposure Mode:": RcExposureMode,
            "Shutter Speed:": RcShutterSpeed,
            "ISO:": RcIso,
            "White Balance:": RcWhiteBalance,
            "Focus Mode:": RcFocusMode,
            "F Stop:": RcFStop,
            "EV:": RcEvOffset,
            "Metering Mode:": RcMeteringMode,
            "Image Quality:": RcImageQuality,
            "Image Aspect:": RcImageAspect,
            "File Format:": RcFileFormat,
            "Drive Mode:": RcDriveMode,
            "Color Style:": RcColorStyle,
        }

        self.parameter_widgets = {}
        row = 0
        col = 0
        for label, enum in self.parameters.items():
            ttk.Label(parameters_frame, text=label).grid(row=row, column=col, padx=5, pady=5, sticky="w")
            combo = ttk.Combobox(parameters_frame, values=[e.value for e in enum])
            combo.grid(row=row, column=col + 1, padx=5, pady=5, sticky="ew")
            self.parameter_widgets[label] = combo
            col += 2
            if col >= 4:
                col = 0
                row += 1

        self.set_parameters_button = ttk.Button(parameters_frame, text="Set Parameters", command=self.set_parameters)
        self.set_parameters_button.grid(row=row + 1, columnspan=4, pady=10, sticky="ew")

        self.focus_preview_button = ttk.Button(parameters_frame, text="Focus Preview", command=self.focus_preview)
        self.focus_preview_button.grid(row=(len(self.parameters) // 2) + 2, columnspan=4, pady=10, sticky="ew")

        # Capture Section
        capture_config_frame = ttk.LabelFrame(capture_frame, text="Capture Configuration", padding=(10, 5))
        capture_config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(capture_config_frame, text="Number of Shots:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.num_shots = ttk.Entry(capture_config_frame)
        self.num_shots.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(capture_config_frame, text="Interval (s):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.interval = ttk.Entry(capture_config_frame)
        self.interval.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.start_capture_button = ttk.Button(capture_config_frame, text="Start Light Frames", command=self.start_capture)
        self.start_capture_button.grid(row=2, columnspan=2, pady=10, sticky="ew")

        # Gallery Section
        gallery_content_frame = ttk.Frame(gallery_frame)
        gallery_content_frame.pack(fill="both", expand=True)

        self.gallery_listbox = tk.Listbox(gallery_content_frame)
        self.gallery_listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.gallery_scrollbar = ttk.Scrollbar(gallery_content_frame, orient=tk.VERTICAL, command=self.gallery_listbox.yview)
        self.gallery_scrollbar.pack(side="left", fill="y")

        self.gallery_listbox.config(yscrollcommand=self.gallery_scrollbar.set)

        self.download_button = ttk.Button(gallery_frame, text="Download Selected Image", command=self.download_image)
        self.download_button.pack(pady=10)

        self.load_gallery_button = ttk.Button(gallery_frame, text="Load Gallery", command=self.load_gallery)
        self.load_gallery_button.pack(pady=10)

        # Close App Button
        self.close_button = ttk.Button(self, text="Close App", command=self.close_app)
        self.close_button.pack(side="bottom", fill="x", padx=10, pady=10)

        self.load_gallery()
        self.check_connection_status_async()

    def close_app(self):
        # Properly end streaming live view
        if self.live_view_thread and self.live_view_thread.is_alive():
            self.live_view_thread = None  # Signal the thread to stop

        # Properly end capture thread
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread = None  # Signal the thread to stop

        # Allow time for threads to stop
        time.sleep(1)

        # Destroy the main window to close the app
        self.destroy()

        # Exit the application
        sys.exit()


    def focus_preview(self):
        # Save the current parameters
        self.current_params = {label: combo.get() for label, combo in self.parameter_widgets.items()}
        # Set parameters for focusing
        self.set_focus_parameters()
        # Capture an image for focusing
        self.capture_focus_image()

    def set_focus_parameters(self):
        # Set parameters to values suitable for focusing
        focus_params = {
            "Exposure Mode:": "Manual",
            "Shutter Speed:": "2.5s",
            "ISO:": "6400",
            "White Balance:": "5000",
            "Focus Mode:": "ManualFocus",
            "File Format:":"RAW",
        }
        for label, value in focus_params.items():
            self.parameter_widgets[label].set(value)
        self.set_parameters()

    def capture_focus_image(self):
        try:
            self.send_command(RcCmdShootPhoto())
            time.sleep(3)  # Wait for the image to be saved on the camera
            self.retrieve_latest_image()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture focus image: {str(e)}")

    def retrieve_latest_image(self):
        try:
            # List images on the camera and get the latest one
            list_cmd = CmdFileList(permit_raw=True, permit_jpg=True)
            response = self.send_command(list_cmd)
            if response is None or response.status != 200:
                raise Exception("Failed to get image list from camera")

            image_paths = self.parse_image_list_response(response.data)
            latest_image_path = image_paths[-1] if image_paths else None
            if not latest_image_path:
                raise Exception("No images found on camera")

            # Retrieve the latest image
            get_cmd = CmdFileGetMidThumb(latest_image_path)
            response = self.send_command(get_cmd)
            if response is None or response.status != 200:
                raise Exception(f"Failed to retrieve image: {latest_image_path}")

            image_data = response.data
            focus_preview_path = os.path.join(self.image_dir, "focus_preview.jpg")
            with open(focus_preview_path, 'wb') as f:
                f.write(image_data)

            self.display_focus_image_window(focus_preview_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve latest image: {str(e)}")

    def display_focus_image_window(self, image_path):
        self.focus_window = tk.Toplevel(self)
        self.focus_window.title("Focus Preview")

        img = Image.open(image_path)
        img = img.resize((600, 500), Image.LANCZOS)
        self.focus_img = ImageTk.PhotoImage(img)

        self.img_label = tk.Label(self.focus_window, image=self.focus_img)
        self.img_label.pack()

        self.zoom_in_button = ttk.Button(self.focus_window, text="+", command=self.zoom_in_focus)
        self.zoom_in_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.zoom_out_button = ttk.Button(self.focus_window, text="-", command=self.zoom_out_focus)
        self.zoom_out_button.pack(side=tk.RIGHT, padx=10, pady=10)

        adjust_button = ttk.Button(self.focus_window, text="Adjust Focus", command=lambda: self.adjust_focus(self.focus_window))
        adjust_button.pack(side=tk.LEFT, padx=10, pady=10)

        confirm_button = ttk.Button(self.focus_window, text="Confirm Focus", command=lambda: self.confirm_focus(self.focus_window))
        confirm_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.img_label.bind("<B1-Motion>", self.pan_image)

    def adjust_focus(self, focus_window):
        focus_window.destroy()
        self.capture_focus_image()

    def confirm_focus(self, focus_window):
        focus_window.destroy()
        for label, value in self.current_params.items():
            self.parameter_widgets[label].set(value)
        self.set_parameters()
        messagebox.showinfo("Focus", "Focus confirmed and original parameters restored.")

    def zoom_in_focus(self):
        self.zoom_factor *= 1.2
        self.update_focus_image()

    def zoom_out_focus(self):
        self.zoom_factor /= 1.2
        self.update_focus_image()

    def update_focus_image(self):
        img = Image.open(os.path.join(self.image_dir, "focus_preview.jpg"))
        width, height = img.size
        crop_width = width / self.zoom_factor
        crop_height = height / self.zoom_factor
        left = self.pan_x - crop_width / 4
        top = self.pan_y - crop_height / 4
        right = left + crop_width
        bottom = top + crop_height
        img = img.crop((left, top, right, bottom))
        img = img.resize((600, 500), Image.LANCZOS)
        self.focus_img = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.focus_img)
        self.img_label.image = self.focus_img

    def pan_image(self, event):
        self.pan_x += event.x - self.img_label.winfo_width() / 4
        self.pan_y += event.y - self.img_label.winfo_height() / 4
        self.update_focus_image()

    def load_gallery(self):
        if not self.connected:
            messagebox.showerror("Error", "Camera is not connected.")
            return
        try:
            # List images on the camera
            print("Listing images on the camera...")
            list_cmd = CmdFileList(permit_raw=True, permit_jpg=True)
            response = self.send_command(list_cmd)
            if response is None or response.status != 200:
                raise Exception("Failed to get image list from camera")
            print(f"Image list response: {response.data}")

            # Parse response to get the list of image paths
            image_paths = self.parse_image_list_response(response.data)
            print(f"Image paths: {image_paths}")

            self.gallery_listbox.delete(0, tk.END)
            self.thumbnails = []
            self.image_paths = []

            for image_path in image_paths:
                image_filename = os.path.basename(image_path)
                thumbnail_path = os.path.join(self.image_dir, "thumbnails", image_filename + ".jpg")
                if os.path.exists(thumbnail_path):
                    img = Image.open(thumbnail_path)
                    img.thumbnail((100, 100))
                    img = ImageTk.PhotoImage(img)
                    self.thumbnails.append(img)
                    self.image_paths.append(image_path)
                    self.gallery_listbox.insert(tk.END, image_filename)
                else:
                    # Get thumbnail from the camera
                    print(f"Retrieving thumbnail: {image_path}")
                    get_cmd = CmdFileGetMidThumb(image_path)
                    response = self.send_command(get_cmd)
                    if response is None or response.status != 200:
                        raise Exception(f"Failed to retrieve thumbnail: {image_path}")

                    image_data = response.data
                    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                    with open(thumbnail_path, 'wb') as f:
                        f.write(image_data)

                    img = Image.open(thumbnail_path)
                    img.thumbnail((100, 100))
                    img = ImageTk.PhotoImage(img)
                    self.thumbnails.append(img)
                    self.image_paths.append(image_path)
                    self.gallery_listbox.insert(tk.END, image_filename)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load gallery: {str(e)}")

    def check_connection_status_async(self):
        threading.Thread(target=self.check_connection_status).start()

    def check_connection_status(self):
        try:
            # Attempt to fetch camera status to determine if connected
            status_cmd = CmdGetCameraStatus()
            response = self.send_command(status_cmd)
            if response and response.status == 200:
                self.reconnect_button.config(state="normal")
                self.connection_status_label.config(text="Connected", fg="green")
                self.connected = True
            else:
                self.connection_status_label.config(text="Not Connected", fg="red")
                self.connected = False
        except Exception as e:
            print(f"Connection check failed: {str(e)}")
            self.connection_status_label.config(text="Not Connected", fg="red")
            self.connected = False

    def display_image(self, event):
        if not self.gallery_listbox.curselection():
            return
        selected_index = self.gallery_listbox.curselection()[0]
        selected_file = self.gallery_listbox.get(selected_index)
        img_path = os.path.join(self.image_dir, selected_file)
        img = Image.open(img_path)
        img = img.resize((400, 300), Image.LANCZOS)
        img = ImageTk.PhotoImage(img)

        if self.liveview_label is not None:
            self.liveview_label.destroy()

        self.liveview_label = ttk.Label(self.live_view_window)
        self.liveview_label.pack(fill="both", expand=True)
        self.liveview_label.config(image=img)
        self.liveview_label.image = img

    def download_image(self):
        selected_index = self.gallery_listbox.curselection()
        if not selected_index:
            messagebox.showerror("Error", "No image selected.")
            return

        selected_index = selected_index[0]
        selected_file = self.gallery_listbox.get(selected_index)
        img_path = self.image_paths[selected_index]

        try:
            # Get the original image from the camera
            get_cmd = CmdFileGet(img_path)
            response = self.send_command(get_cmd)
            if response is None or response.status != 200:
                raise Exception(f"Failed to retrieve image: {img_path}")

            image_data = response.data
            save_path = filedialog.asksaveasfilename(defaultextension=".dng", filetypes=[("DNG files", "*.dng"), ("All files", "*.*")])
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(image_data)
                messagebox.showinfo("Success", f"Image saved as {save_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download image: {str(e)}")

    def connect_camera(self):
        self.connect_button.config(state="disabled")
        self.connect_thread = threading.Thread(target=self._connect_camera)
        self.connect_thread.start()

    def _connect_camera(self):
        try:
            self.ssid, self.pwd = trigger_remote_control_closest()
            if self.ssid and self.pwd:
                self.after(0, lambda: messagebox.showinfo("Success", f"Connected to BLE. SSID: {self.ssid}, Password: {self.pwd}"))
                self.after(0, self.prompt_wifi_connection)
                self.after(0, lambda: self.reconnect_button.config(state="normal"))
                self.after(0, lambda: self.connection_status_label.config(text="Connected", fg="green"))
                self.connected = True
            else:
                self.after(0, lambda: messagebox.showerror("Error", "Failed to connect to the camera."))
                self.connected = False
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Connection failed: {str(e)}"))
            self.connected = False
        finally:
            self.after(0, lambda: self.connect_button.config(state="normal"))

    def prompt_wifi_connection(self):
        # Prompt user to connect to the Wi-Fi network manually
        self.wifi_prompt = tk.Toplevel(self)
        self.wifi_prompt.title("Connect to Wi-Fi")
        self.wifi_prompt.geometry("300x150")

        ttk.Label(self.wifi_prompt, text="Please connect to the Wi-Fi network manually.").pack(pady=10)
        ttk.Label(self.wifi_prompt, text=f"SSID: {self.ssid}").pack(pady=5)
        ttk.Label(self.wifi_prompt, text=f"Password: {self.pwd}").pack(pady=5)
        ttk.Button(self.wifi_prompt, text="Start Live View", command=self.start_live_view).pack(pady=10)

    def validate_inputs(self):
        if not self.num_shots.get().isdigit():
            messagebox.showerror("Error", "Number of Shots must be an integer.")
            return False
        if not self.interval.get().isdigit():
            messagebox.showerror("Error", "Interval must be an integer.")
            return False
        return True

    def set_parameters(self):
        try:
            commands = []
            if self.parameter_widgets["Exposure Mode:"].get():
                commands.append(RcCmdSetCameraMode(RcExposureMode[self.parameter_widgets["Exposure Mode:"].get().replace(" ", "")]))
            if self.parameter_widgets["Shutter Speed:"].get():
                shutter_speed_value = self.parameter_widgets["Shutter Speed:"].get().replace("s", "")
                commands.append(RcCmdSetShutterSpeed(RcShutterSpeed(f"{shutter_speed_value}s")))
            if self.parameter_widgets["ISO:"].get():
                commands.append(RcCmdSetIso(RcIso(self.parameter_widgets["ISO:"].get())))
            if self.parameter_widgets["White Balance:"].get():
                commands.append(RcCmdSetWhiteBalanceMode(RcWhiteBalance(self.parameter_widgets["White Balance:"].get())))
            if self.parameter_widgets["Focus Mode:"].get():
                commands.append(RcCmdSetFocusingMode(RcFocusMode[self.parameter_widgets["Focus Mode:"].get()]))
            if self.parameter_widgets["F Stop:"].get():
                commands.append(RcCmdSetFStop(RcFStop(self.parameter_widgets["F Stop:"].get().replace("F", ""))))
            if self.parameter_widgets["EV:"].get():
                commands.append(RcCmdSetExposureValueOffset(RcEvOffset(self.parameter_widgets["EV:"].get())))

            for cmd in commands:
                self.send_command(cmd)
            messagebox.showinfo("Success", "Parameters set successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set parameters: {str(e)}")

    def capture_image(self):
        try:
            self.send_command(RcCmdShootPhoto())
            # Wait for the image to be saved on the camera
            time.sleep(2)  # Adjust this based on your camera's response time
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture image: {str(e)}")

    def parse_image_list_response(self, response_data):
        image_paths = []
        try:
            data = json.loads(response_data.decode())
            if 'data' in data:
                files = data['data']
                for file in files:
                    if file.get('filetype') == 'raw' and file.get('path').endswith('.DNG'):
                        image_paths.append(file['path'])
                    elif file.get('filetype') == 'jpg' and file.get('path').endswith('.JPG'):
                        image_paths.append(file['path'])
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        return image_paths

    def reconnect_camera(self):
        if self.live_view_thread and self.live_view_thread.is_alive():
            return
        self.live_view_thread = threading.Thread(target=self._start_live_view)
        self.live_view_thread.start()
        self.connection_status_label.config(text="Connected", fg="green")

    def retrieve_images(self):
        try:
            # List images on the camera
            print("Listing images on the camera...")
            list_cmd = CmdFileList(permit_raw=True, permit_jpg=True)
            response = self.send_command(list_cmd)
            if response is None or response.status != 200:
                raise Exception("Failed to get image list from camera")
            print(f"Image list response: {response.data}")

            # Parse response to get the list of image paths
            image_paths = self.parse_image_list_response(response.data)
            print(f"Image paths: {image_paths}")

            for image_path in image_paths:
                image_filename = os.path.basename(image_path)
                local_image_path = os.path.join(self.image_dir, image_filename)
                if os.path.exists(local_image_path):
                    print(f"Image already exists: {local_image_path}. Skipping download.")
                    continue

                # Get image from the camera
                print(f"Retrieving image: {image_path}")
                get_cmd = CmdFileGet(image_path)
                response = self.send_command(get_cmd)
                if response is None or response.status != 200:
                    raise Exception(f"Failed to retrieve image: {image_path}")

                image_data = response.data
                print(f"Saving image: {local_image_path}")

                # Save the image
                with open(local_image_path, 'wb') as f:
                    f.write(image_data)
            self.load_gallery()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve images: {str(e)}")

    def start_capture(self):
        if self.capture_thread and self.capture_thread.is_alive():
            return
        if not self.validate_inputs():
            return
        self.capture_thread = threading.Thread(target=self._start_capture)
        self.capture_thread.start()

    def _start_capture(self):
        try:
            num_shots = int(self.num_shots.get())
            interval = int(self.interval.get())
            for i in range(num_shots):
                self.capture_image()
                time.sleep(interval)
            self.after(0, lambda: messagebox.showinfo("Success", "Light frames capture completed successfully."))
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Astro imaging failed: {str(e)}"))

    def send_command(self, cmd: YiHttpCmd):
        try:
            json = str(cmd.to_json()).replace("'", '"').replace(' "', '"')
            url = f"http://{INET_ADDRESS_CAMERA}/?data={json}"
            print(f"Sending command to URL: {url}")  # Debug statement
            response: HTTPResponse = self.http.request("GET", url, timeout=10.0)
            if response.status != 200:
                raise Exception(f"Failed to send command. Status: {response.status}")
            print(f"Command response: {response.data}")  # Debug statement
            return response
        except TimeoutError:
            raise Exception("Timeout while sending command")
        except Exception as e:
            print(f"Exception: {str(e)}")
            return None

    def start_live_view(self):
        if self.live_view_thread and self.live_view_thread.is_alive():
            return
        self.live_view_thread = threading.Thread(target=self._start_live_view)
        self.live_view_thread.start()
        self.wifi_prompt.destroy()

    def _start_live_view(self):
        try:
            self.send_command(RcCmdStart())
            self.open_live_view_window()
            self.receive_live_view()
        except Exception as e:
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Failed to start live view: {str(e)}"))

    def open_live_view_window(self):
        if self.live_view_window is not None:
            return

        self.live_view_window = tk.Toplevel(self)
        self.live_view_window.title("Live View")
        self.live_view_window.geometry("800x600")

        self.liveview_label = ttk.Label(self.live_view_window)
        self.liveview_label.pack(fill="both", expand=True)

    def receive_live_view(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('', UDP_PORT_LIVEVIEW))
            sock.settimeout(2)

            data = bytearray()
            data_idx_frame = None
            data_idx_last_packet = -1
            data_valid = True

            while self.live_view_thread is not None:
                try:
                    pack, _ = sock.recvfrom(1024000)
                    if len(pack) < 12:
                        continue

                    idx_frame = int.from_bytes(pack[:4], byteorder='big')
                    len_packet_frame = int.from_bytes(pack[4:8], byteorder='big')
                    idx_packet_frame = int.from_bytes(pack[8:12], byteorder='big')

                    if data_idx_frame != idx_frame:
                        data = bytearray()
                        data_idx_frame = idx_frame
                        data_idx_last_packet = -1
                        data_valid = True

                    if data_valid:
                        if (idx_packet_frame - 1) == data_idx_last_packet:
                            data.extend(pack[12:])
                            data_idx_last_packet = idx_packet_frame
                        else:
                            data_valid = False
                            continue

                        if data_idx_last_packet == len_packet_frame - 1:
                            if len(data) > 2048:
                                try:
                                    img = Image.open(io.BytesIO(data[2048:]))
                                    img = ImageTk.PhotoImage(img)
                                    self.liveview_label.configure(image=img)
                                    self.liveview_label.image = img
                                except (UnidentifiedImageError, OSError) as e:
                                    print(f"Image decoding error: {e}")
                            else:
                                print(f"Incomplete frame received, length: {len(data)}")
                except TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error receiving live view data: {e}")


if __name__ == "__main__":
    app = YiM1Controller()
    app.mainloop()
