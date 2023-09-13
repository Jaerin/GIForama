import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageGrab, ImageEnhance, ImageChops, ImageDraw
import threading
import time
from io import BytesIO

class MonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Monitor App')
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.resizable(False, False)
        self.last_mouse_position = (None, None)




        self.selection = None
        self.selection_in_progress = False  # Add this variable
        self.update_image_flag = False
        self.stop_thread = threading.Event()
        self.recording = False
        self.mouse_held_down = False  # Add this line

        # Create a frame for the image
        self.image_frame = ttk.Frame(root)
        self.image_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        self.photo_image = self.create_blank_image()  # Create a placeholder image
        self.image_label = ttk.Label(self.image_frame, image=self.photo_image)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the recording info
        self.recording_info_frame = ttk.Frame(root)
        self.recording_info_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nw")

        self.timer_label = ttk.Label(self.recording_info_frame, text="Recording Time: 00:00", anchor=tk.W)
        self.timer_label.pack(side=tk.LEFT, padx=5)

        self.frame_count_label = ttk.Label(self.recording_info_frame, text="Frames Recorded: 0", anchor=tk.W)
        self.frame_count_label.pack(side=tk.LEFT, padx=5)

        self.estimated_size_label = ttk.Label(self.recording_info_frame, text="Estimated GIF Size: N/A", anchor=tk.W)
        self.estimated_size_label.pack(side=tk.LEFT, padx=5)

        # Create a frame for the file name input
        self.filename_frame = ttk.Frame(root)
        self.filename_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nw")

        self.filename_entry_label = ttk.Label(self.filename_frame, text="File Name:")
        self.filename_entry_label.pack(side=tk.LEFT)

        self.filename_entry = ttk.Entry(self.filename_frame)
        self.filename_entry.pack(side=tk.LEFT)
        self.filename_entry.insert(0, "output.gif")  # Default filename

        self.images_for_gif = []

        # Create a frame for the buttons
        self.button_frame = ttk.Frame(root)
        self.button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="sw")

        # Create a button to select the recording area
        self.select_area_button = ttk.Button(self.button_frame, text="Select Area", command=self.initiate_select_area)
        self.select_area_button.pack(side=tk.LEFT, padx=5)

        # Create a button for starting and stopping recording
        self.record_stop_button = ttk.Button(self.button_frame, text="Record", command=self.toggle_record_stop)
        self.record_stop_button.pack(side=tk.LEFT, padx=5)
        self.record_stop_button.config(state=tk.DISABLED)  # Start with the button disabled

        # Create a button for saving the GIF
        self.save_button = ttk.Button(self.button_frame, text="Save GIF", command=self.save_gif, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.quit_button = ttk.Button(self.button_frame, text="Quit", command=self.on_closing)
        self.quit_button.pack(side=tk.RIGHT, padx=5)

        self.recording_start_time = None
        self.frames_recorded = 0

        self.start_x = self.start_y = None  # Initialize selection variables
        self.rect = None
        self.canvas_img_pil = None
        self.canvas_img = None
        self.dimmed = None  # Store the dimmed version of the screen
        self.clear = None  # Store the clear version of the screen
        self.mask = None  # Initialize mask as None
        self.mask_draw = None  # Initialize ImageDraw object as None

    def toggle_record_stop(self):
        if not self.recording:
            # Start recording
            self.start_recording()
        else:
            # Stop recording
            self.stop_recording()

    def start_recording(self):
        self.recording_start_time = time.time()
        self.record_stop_button.config(text="Stop")
        self.save_button.config(state=tk.DISABLED)  # Disable save button during recording
        self.recording = True
        self.update_estimated_size_label()  # Update the estimated size label

    def stop_recording(self):
        self.record_stop_button.config(text="Record")
        self.save_button.config(state=tk.NORMAL)  # Enable save button after stopping recording
        self.recording = False
        self.recording_start_time = None
        self.update_estimated_size_label()  # Update the estimated size label

        # ... (rest of your stop recording code) ...

    def save_gif(self):
        filename = self.filename_entry.get()
        if not filename:
            filename = "output.gif"
        try:
            self.images_for_gif[0].save(filename,
                                        save_all=True,
                                        append_images=self.images_for_gif[1:],
                                        duration=100,  # 100 ms per frame
                                        loop=0)
            self.images_for_gif = []
            self.frames_recorded = 0
            self.frame_count_label.config(text="Frames Recorded: 0")
            self.recording_start_time = None  # Reset the recording time
            self.timer_label.config(text="Recording Time: 00:00")  # Reset the timer display
            self.update_estimated_size_label()  # Update the estimated size label
        except Exception as e:
            print(f"Error saving GIF: {e}")
    def update_estimated_size_label(self):
        estimated_size = self.estimate_gif_size()
        self.estimated_size_label.config(text=f"Estimated GIF Size: {estimated_size}")


    def update_dimmed_image(self, end_x, end_y):
        if self.canvas_img_pil is None:
            return

        # Ensure the coordinates are in the right order
        left = min(self.start_x, end_x)
        upper = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        lower = max(self.start_y, end_y)

        # Create the dimmed image
        dimmed = ImageEnhance.Brightness(self.canvas_img_pil).enhance(0.3)
        dimmed.paste(self.canvas_img_pil.crop((left, upper, right, lower)), (left, upper))

        # Draw the red selection box directly onto the dimmed image
        draw = ImageDraw.Draw(dimmed)
        draw.rectangle([left, upper, right, lower], outline='red', width=2)

        dimmed_photo_image = ImageTk.PhotoImage(dimmed)

        if not self.stop_thread.is_set():
            self.canvas.itemconfig(self.canvas_image, image=dimmed_photo_image)
            self.photo_image = dimmed_photo_image



    def initiate_select_area(self):
        # Clean up and stop the existing update thread if it exists
        if hasattr(self, 'update_thread') and self.update_thread.is_alive():
            self.update_image_flag = False
            self.stop_thread.set()  # Signal the previous thread to stop
            self.update_thread.join()  # Wait for the previous thread to finish
            self.cleanup_and_stop_thread()  # Cleanup resources
        
        self.root.iconify()
        self.root.update()
        self.root.after(200)

        try:
            # Always take a fresh screenshot
            screen = ImageGrab.grab()
            if hasattr(self, 'select_win'):
                try:
                    self.select_win.destroy()
                except tk.TclError:
                    pass

            self.select_win = tk.Toplevel()
            self.canvas_img_pil = screen
            self.canvas_img = ImageTk.PhotoImage(screen)
            self.select_win.attributes('-fullscreen', True, '-topmost', True)
            canvas = tk.Canvas(self.select_win, cursor='cross')
            canvas.pack(fill=tk.BOTH, expand=tk.YES)
            self.canvas_img_pil = screen
            self.canvas_img = ImageTk.PhotoImage(screen)
            self.canvas_image = canvas.create_image(0, 0, anchor=tk.NW, image=self.canvas_img)
            canvas.bind('<ButtonPress-1>', self.on_press)
            canvas.bind('<B1-Motion>', self.on_drag)
            canvas.bind('<ButtonRelease-1>', self.on_release)
            self.canvas = canvas
            
        except Exception as e:
            print(f"Error capturing screen: {e}")
            self.root.deiconify()

    def create_blank_image(self):
        # Create a placeholder blank image
        return ImageTk.PhotoImage(Image.new("RGB", (1, 1), "white"))

    def update_timer(self):
        if self.recording_start_time is not None:
            current_time = time.time()
            elapsed_time = current_time - self.recording_start_time
            formatted_time = time.strftime("%M:%S", time.gmtime(elapsed_time))
            self.timer_label.config(text=f"Recording Time: {formatted_time}")
        # Schedule the timer to update every 1000 ms (1 second)
        self.root.after(1000, self.update_timer)
        
    def update_selected_area(self):
        while self.update_image_flag:
            if not self.selection:
                self.photo_image = self.create_blank_image()
                self.image_label.config(image=self.photo_image)
                self.root.update_idletasks()
                time.sleep(0.1)
                continue

            x1, y1, x2, y2 = self.selection
            try:
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                if self.recording:
                    self.images_for_gif.append(img)  # Storing the image for GIF generation
                    self.frames_recorded += 1
                    self.frame_count_label.config(text=f"Frames Recorded: {self.frames_recorded}")
                self.previous_image = self.photo_image
                self.photo_image = ImageTk.PhotoImage(img)
                self.image_label.config(image=self.photo_image)
                self.root.update_idletasks()
                time.sleep(0.1)  # Introduce a delay to throttle the updates
            except Exception as e:
                print(f"Error capturing screen: {e}")
                self.update_image_flag = False


    def initiate_select_area(self):
        if not self.selection_in_progress:  # Check if a selection is not already in progress
            self.selection_in_progress = True  # Set selection in progress

            self.root.iconify()
            self.root.update()
            self.root.after(200)

            try:
                # Always take a fresh screenshot
                screen = ImageGrab.grab()
                if hasattr(self, 'select_win'):
                    try:
                        self.select_win.destroy()
                    except tk.TclError:
                        pass

                self.select_win = tk.Toplevel()
                self.canvas_img_pil = screen
                self.canvas_img = ImageTk.PhotoImage(screen)
                self.select_win.attributes('-fullscreen', True, '-topmost', True)
                canvas = tk.Canvas(self.select_win, cursor='cross')
                canvas.pack(fill=tk.BOTH, expand=tk.YES)
                self.canvas_img_pil = screen
                self.canvas_img = ImageTk.PhotoImage(screen)
                self.canvas_image = canvas.create_image(0, 0, anchor=tk.NW, image=self.canvas_img)
                canvas.bind('<ButtonPress-1>', self.on_press)
                canvas.bind('<B1-Motion>', self.on_drag)
                canvas.bind('<ButtonRelease-1>', self.on_release)
                self.canvas = canvas
            except Exception as e:
                print(f"Error capturing screen: {e}")
                self.root.deiconify()

    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.mouse_held_down = True  # Set the flag to True
        self.continuous_update()  # Start the continuous update

    def on_drag(self, event):
        self.update_dimmed_image(event.x, event.y)

    def continuous_update(self):
        current_mouse_position = (self.canvas.winfo_pointerx() - self.canvas.winfo_rootx(),
                                  self.canvas.winfo_pointery() - self.canvas.winfo_rooty())
        
        # Check if the mouse position has changed
        if self.mouse_held_down and current_mouse_position != self.last_mouse_position:
            self.update_dimmed_image(*current_mouse_position)
            self.last_mouse_position = current_mouse_position  # Update the last known position

        self.canvas.after(1, self.continuous_update)  # Reduced delay to 20ms

    def on_release(self, event):
        self.selection = (self.start_x, self.start_y, event.x, event.y)
        self.mouse_held_down = False  # Set the flag to False
        
        if hasattr(self, 'canvas_img_pil'):
            self.canvas_img_pil = None
        if hasattr(self, 'canvas_img'):
            self.canvas_img = None
        if hasattr(self, 'select_win'):
            self.select_win.destroy()

        self.root.deiconify()

        min_border = 10  # Minimum border size
        x1, y1, x2, y2 = self.selection

        # Calculate the minimum height based on the button frame's location
        button_frame_height = self.button_frame.winfo_height()
        min_height = 2 * min_border + button_frame_height
        
        # Calculate the height while ensuring it's not below the minimum
        height = max(abs(y2 - y1), min_height)
        
        # Adjust the window size to accommodate the buttons and maintain the minimum size
        self.root.geometry(f"{x2 - x1 + 20}x{height + 135}")  # Increased window height

        self.update_image_flag = True

        if not hasattr(self, 'update_thread') or not self.update_thread.is_alive():
            self.stop_thread.clear()
            self.update_thread = threading.Thread(target=self.update_selected_area)
            self.update_thread.start()
            self.record_stop_button.config(text="Record", state=tk.NORMAL)
        else:
            # Reuse the existing update thread
            self.record_stop_button.config(text="Record", state=tk.NORMAL)

        self.selection_in_progress = False  # Reset selection in progress
        self.dimmed = None
        self.mask = None
        self.mask_draw = None


    def estimate_gif_size(self):
        if not self.images_for_gif:
            return "N/A"

        try:
            # Create a BytesIO object to save the GIF in memory
            buffer = BytesIO()
            
            # Save the GIF to the buffer (you can specify other options like duration, loop, etc.)
            self.images_for_gif[0].save(buffer, format="GIF", save_all=True, append_images=self.images_for_gif[1:])
            
            # Get the size of the buffer in bytes
            size_bytes = buffer.tell()
            
            # Convert bytes to human-readable format
            if size_bytes < 1024:
                return f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.2f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.2f} MB"
        except Exception as e:
            print(f"Error estimating GIF size: {e}")
            return "N/A"


    def clear_image(self):
        self.selection = None
        self.cleanup_and_stop_thread()
        self.record_stop_button.config(text="Record")  # Update the button text to "Record"
        self.quit_button.config(state=tk.NORMAL)  # Enable the "Quit" button

    def post_clear_actions(self):
        # Save the animated GIF
        if self.images_for_gif:
            filename = self.filename_entry.get()
            if not filename:
                filename = "output.gif"
            try:
                self.images_for_gif[0].save(filename,
                                            save_all=True,
                                            append_images=self.images_for_gif[1:],
                                            duration=100,  # 100 ms per frame
                                            loop=0)
                self.images_for_gif = []
            except Exception as e:
                print(f"Error saving GIF: {e}")

        self.image_label.config(image=self.create_blank_image())
        self.root.geometry("")  # Reset the window size
        self.record_stop_button.config(state=tk.NORMAL)  # Enable the "Record" button
        self.quit_button.config(state=tk.NORMAL)  # Enable the "Quit" button

    def on_closing(self):
        self.update_image_flag = False

        if hasattr(self, 'update_thread') and self.update_thread.is_alive():
            # Wait a bit and check again
            self.root.after(100, self.on_closing)
        else:
            self.clean_up_and_exit()

    def clean_up_and_exit(self):
        # Additional clean-up can be placed here if needed in the future

        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = MonitorApp(root)
    app.update_timer()  # Start the timer update
    root.mainloop()