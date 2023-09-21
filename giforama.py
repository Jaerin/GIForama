import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab, ImageEnhance, ImageDraw
from io import BytesIO
import threading
import time
import queue

class MonitorApp:
    def __init__(self, root):
        self.setup_variables(root)
        self.setup_ui_elements()

    def setup_variables(self, root):
        self.root = root
        self.root.title('Monitor App')
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.minsize(420, 135)
        self.root.resizable(False, False)
        self.last_mouse_position = (None, None)
        self.selection = None
        self.selection_in_progress = False
        self.update_image_flag = False
        self.stop_thread = threading.Event()
        self.recording = False
        self.mouse_held_down = False
        self.recording_start_time = None
        self.images_for_gif = []
        self.frames_recorded = 0
        self.start_x = self.start_y = None
        self.canvas_img_pil = None
        self.canvas_img = None
        self.update_queue = queue.Queue()

    def setup_ui_elements(self):
        self.setup_image_frame()
        self.setup_recording_info_frame()
        self.setup_filename_frame()
        self.setup_button_frame()
        self.root.update_idletasks()

    def setup_image_frame(self):
        self.image_frame = ttk.Frame(self.root)
        self.image_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        self.photo_image = self.create_blank_image()
        self.image_label = ttk.Label(self.image_frame, image=self.photo_image)
        self.image_label.pack(fill=tk.BOTH, expand=True)

    def setup_recording_info_frame(self):
        self.recording_info_frame = ttk.Frame(self.root)
        self.recording_info_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nw")
        self.timer_label = ttk.Label(self.recording_info_frame, text="Recording Time: 00:00", anchor=tk.W)
        self.timer_label.pack(side=tk.LEFT, padx=5)
        self.frame_count_label = ttk.Label(self.recording_info_frame, text="Frames Recorded: 0", anchor=tk.W)
        self.frame_count_label.pack(side=tk.LEFT, padx=5)
        self.estimated_size_label = ttk.Label(self.recording_info_frame, text="Estimated GIF Size: N/A", anchor=tk.W)
        self.estimated_size_label.pack(side=tk.LEFT, padx=5)

    def setup_filename_frame(self):
        self.filename_frame = ttk.Frame(self.root)
        self.filename_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nw")
        self.filename_entry_label = ttk.Label(self.filename_frame, text="File Name:")
        self.filename_entry_label.pack(side=tk.LEFT)
        self.filename_entry = ttk.Entry(self.filename_frame)
        self.filename_entry.pack(side=tk.LEFT)
        self.filename_entry.insert(0, "output.gif")

    def setup_button_frame(self):
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="sw")
        self.select_area_button = ttk.Button(self.button_frame, text="Select Area", command=self.initiate_select_area)
        self.select_area_button.pack(side=tk.LEFT, padx=5)
        self.record_stop_button = ttk.Button(self.button_frame, text="Record", command=self.toggle_record_stop, state=tk.DISABLED)
        self.record_stop_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(self.button_frame, text="Save GIF", command=self.save_gif, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.quit_button = ttk.Button(self.button_frame, text="Quit", command=self.on_closing)
        self.quit_button.pack(side=tk.RIGHT, padx=5)

    def toggle_record_stop(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        self.recording_start_time = time.time()
        self.record_stop_button.config(text="Stop")
        self.save_button.config(state=tk.DISABLED)
        self.recording = True
        self.update_estimated_size_label()

    def stop_recording(self):
        self.record_stop_button.config(text="Record")
        self.save_button.config(state=tk.NORMAL)
        self.recording = False
        self.recording_start_time = None
        self.update_estimated_size_label()

    def save_gif(self):
        filename = self.filename_entry.get().strip()
        if not filename:
            filename = "output.gif"
        elif not filename.lower().endswith('.gif'):
            filename += ".gif"
        try:
            self.images_for_gif[0].save(filename,
                                        save_all=True,
                                        append_images=self.images_for_gif[1:],
                                        duration=100,
                                        loop=0)
            self.images_for_gif = []
            self.frames_recorded = 0
            self.frame_count_label.config(text="Frames Recorded: 0")
            self.recording_start_time = None
            self.timer_label.config(text="Recording Time: 00:00")
            self.update_estimated_size_label()
        except Exception as e:
            print(f"Error saving GIF: {e}")
 
    def update_estimated_size_label(self):
        estimated_size = self.estimate_gif_size()
        self.estimated_size_label.config(text=f"Estimated GIF Size: {estimated_size}")


    def update_dimmed_image(self, end_x, end_y):
        if self.canvas_img_pil is None:
            return

        left = min(self.start_x, end_x)
        upper = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        lower = max(self.start_y, end_y)

        # Create a copy of the original image
        dimmed = self.canvas_img_pil.copy()

        # Dim the regions outside the selected area
        if left > 0:
            dimmed.paste(ImageEnhance.Brightness(dimmed.crop((0, 0, left, dimmed.height))).enhance(0.3), (0, 0))
        if right < dimmed.width:
            dimmed.paste(ImageEnhance.Brightness(dimmed.crop((right, 0, dimmed.width, dimmed.height))).enhance(0.3), (right, 0))
        if upper > 0:
            dimmed.paste(ImageEnhance.Brightness(dimmed.crop((left, 0, right, upper))).enhance(0.3), (left, 0))
        if lower < dimmed.height:
            dimmed.paste(ImageEnhance.Brightness(dimmed.crop((left, lower, right, dimmed.height))).enhance(0.3), (left, lower))

        # Draw the red rectangle around the selected area
        draw = ImageDraw.Draw(dimmed)
        draw.rectangle([left, upper, right, lower], outline='red', width=2)

        dimmed_photo_image = ImageTk.PhotoImage(dimmed)

        if not self.stop_thread.is_set():
            self.canvas.itemconfig(self.canvas_image, image=dimmed_photo_image)
            self.photo_image = dimmed_photo_image

    def initiate_select_area(self):
        if hasattr(self, 'update_thread') and self.update_thread.is_alive():
            self.update_image_flag = False
        
        self.root.iconify()
        self.root.update()
        self.root.after(200)

        try:
            screen = ImageGrab.grab()
            self.reset_selection_window()
            self.select_win = tk.Toplevel()
            self.canvas_img_pil = screen
            self.canvas_img = ImageTk.PhotoImage(screen)
            self.select_win.attributes('-fullscreen', True, '-topmost', True)
            canvas = tk.Canvas(self.select_win, cursor='cross', highlightthickness=0, bg='black', width=screen.width, height=screen.height)
            canvas.pack(fill=tk.BOTH, expand=tk.YES)
            self.canvas_image = canvas.create_image(0, 0, anchor=tk.NW, image=self.canvas_img)
            canvas.bind('<ButtonPress-1>', self.on_press)
            canvas.bind('<B1-Motion>', self.on_drag)
            canvas.bind('<ButtonRelease-1>', self.on_release)
            self.canvas = canvas
            
        except Exception as e:
            print(f"Error capturing screen: {e}")
            self.root.deiconify()

    def create_blank_image(self):
        return ImageTk.PhotoImage(Image.new("RGB", (1, 1), "white"))

    def update_timer(self):
        if self.recording_start_time is not None:
            current_time = time.time()
            elapsed_time = current_time - self.recording_start_time
            formatted_time = time.strftime("%M:%S", time.gmtime(elapsed_time))
            self.timer_label.config(text=f"Recording Time: {formatted_time}")
        self.root.after(1000, self.update_timer)
        
    def update_selected_area(self):
        while self.update_image_flag and not self.stop_thread.is_set():
            if not self.selection:
                self.update_queue.put(("update_image", self.create_blank_image()))  # <-- Use the queue to send updates
                continue

            x1, y1, x2, y2 = self.selection
            try:
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                if self.recording:
                    self.images_for_gif.append(img)
                    self.frames_recorded += 1
                    self.update_queue.put(("update_frame_count", self.frames_recorded))  # <-- Use the queue to send updates
                self.update_queue.put(("update_image", ImageTk.PhotoImage(img)))  # <-- Use the queue to send updates
            except Exception as e:
                print(f"Error capturing screen: {e}")
                self.update_image_flag = False

    def poll_queue(self):
        while not self.update_queue.empty():
            action, data = self.update_queue.get()
            if action == "update_image":
                self.photo_image = data
                self.image_label.config(image=self.photo_image)
            elif action == "update_frame_count":
                self.frame_count_label.config(text=f"Frames Recorded: {data}")
        self.root.after(10, self.poll_queue)

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.mouse_held_down = True
        self.continuous_update()

    def on_drag(self, event):
        self.update_dimmed_image(event.x, event.y)

    def continuous_update(self):
        current_mouse_position = (self.canvas.winfo_pointerx() - self.canvas.winfo_rootx(),
                                  self.canvas.winfo_pointery() - self.canvas.winfo_rooty())
        
        if self.mouse_held_down and current_mouse_position != self.last_mouse_position:
            self.update_dimmed_image(*current_mouse_position)
            self.last_mouse_position = current_mouse_position

        self.canvas.after(1, self.continuous_update)

    def reset_selection_window(self):
        if hasattr(self, 'canvas_img_pil'):
            self.canvas_img_pil = None
        if hasattr(self, 'canvas_img'):
            self.canvas_img = None
        if hasattr(self, 'select_win'):
            try:
                self.select_win.destroy()
            except tk.TclError:
                pass

    def on_release(self, event):
        left = min(self.start_x, event.x)
        upper = min(self.start_y, event.y)
        right = max(self.start_x, event.x)
        lower = max(self.start_y, event.y)


        MIN_SELECTION_SIZE = 10  
        if abs(right - left) < MIN_SELECTION_SIZE or abs(lower - upper) < MIN_SELECTION_SIZE:
            print("Selection too small. Ignored.")
            self.reset_selection_window()
            self.root.deiconify()
            return

        self.selection = (left, upper, right, lower)
        self.mouse_held_down = False
        
        if hasattr(self, 'canvas_img_pil'):
            self.canvas_img_pil = None
        if hasattr(self, 'canvas_img'):
            self.canvas_img = None
        if hasattr(self, 'select_win'):
            self.select_win.destroy()

        self.root.deiconify()
        self.root.focus_force()

        
        button_frame_height = self.button_frame.winfo_height()
        min_height = 20 + button_frame_height
        
        height = max(abs(lower - upper), min_height)
        
        self.root.geometry(f"{right - left + 20}x{height + 135}")

        self.update_image_flag = True

        if not hasattr(self, 'update_thread') or not self.update_thread.is_alive():
            self.stop_thread.clear()
            self.update_thread = threading.Thread(target=self.update_selected_area)
            self.update_thread.start()
            self.record_stop_button.config(text="Record", state=tk.NORMAL)
        else:
            self.record_stop_button.config(text="Record", state=tk.NORMAL)

        self.selection_in_progress = False

    def estimate_gif_size(self):
        if not hasattr(self, 'images_for_gif') or not self.images_for_gif:
            return "N/A"

        try:
            buffer = BytesIO()

            self.images_for_gif[0].save(buffer, format="GIF", save_all=True, append_images=self.images_for_gif[1:])
            size_bytes = buffer.tell()
            
            if size_bytes < 1024:
                return f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.2f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.2f} MB"
        except Exception as e:
            print(f"Error estimating GIF size: {e}")
            return "N/A"

    def on_closing(self):
        self.update_image_flag = False
        self.stop_thread.set()

        if hasattr(self, 'update_thread') and self.update_thread.is_alive():
            self.root.after(100, self.on_closing)
        else:
            self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = MonitorApp(root)
    app.update_timer()
    app.poll_queue()
    root.mainloop()