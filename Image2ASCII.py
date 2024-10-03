import pyglet
from pyglet.window import key, mouse
from tkinter import Tk, filedialog
import os
import numpy as np
from PIL import Image
import subprocess

# 002 3-10-2024

# Set accepted image formats
ACCEPTED_FORMATS = ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp']

# Define the ASCII characters based on intensity
ASCII_CHARS = "@%#*+=-:. "  # Make sure this is defined globally

# Constants for GitHub label
GITHUB_FONT_SIZE = 10  # Font size for the GitHub link text
GITHUB_TRANSPARENCY = 145  # Transparency (out of 255, semi-transparent)
RATIO_ADJUSTMENT_NUM = 2.8

class ImageApp(pyglet.window.Window):
    def __init__(self):
        super().__init__(width=800, height=375, caption="Image to ASCII", resizable=False)

        # Label asking to submit an image
        self.prompt_label = pyglet.text.Label('Submit an image to convert to ASCII art!',
                                              font_name='Arial', font_size=14,
                                              x=self.width // 2, y=self.height // 2 + 100, anchor_x='center')

        # Browse button
        self.browse_button = pyglet.shapes.Rectangle(self.width // 2 - 60, self.height // 2, 120, 40,
                                                     color=(50, 100, 150))
        self.browse_text = pyglet.text.Label('Browse', font_name='Arial', font_size=16,
                                             x=self.width // 2, y=self.height // 2 + 20, anchor_x='center',
                                             anchor_y='center')

        # Console for message output
        self.console_messages = []
        self.console_labels = []
        self.max_console_lines = 5  # Maximum number of lines to show

        # GitHub link at the bottom-right corner
        self.github_label = pyglet.text.Label('https://github.com/Fklyf/Image2ASCII',
                                              font_name='Arial', font_size=GITHUB_FONT_SIZE,
                                              x=10, y=10, anchor_x='right',
                                              color=(255, 255, 255, GITHUB_TRANSPARENCY))

        # Invisible drag-and-drop area covering the entire window
        self.invisible_button = pyglet.shapes.Rectangle(0, 0, self.width, self.height, color=(0, 0, 0, 0))

        # Variables for user input
        self.input_buffer = ""
        self.entering_width = True
        self.width_input = None
        self.height_input = None
        self.image_path = None
        self.image_processed = False
        self.awaiting_input = False  # Tracks if the program is waiting for width/height input
        self.processing_started = False  # Prevents duplicate input during processing
        self.input_disabled = False  # Flag to disable input spam

        # Enable file drop
        self.set_handler('on_file_drop', self.on_file_drop)

    def on_draw(self):
        self.clear()

        # Draw the labels and buttons
        self.prompt_label.draw()
        self.browse_button.draw()
        self.browse_text.draw()
        self.github_label.draw()

        # Draw console messages
        for label in self.console_labels:
            label.draw()

    def on_resize(self, width, height):
        # Center the prompt label, browse button, and console relative to the window size
        self.prompt_label.x = width // 2
        self.prompt_label.y = height // 2 + 100

        self.browse_button.x = width // 2 - 60
        self.browse_button.y = height // 2
        self.browse_text.x = width // 2
        self.browse_text.y = height // 2 + 20

        # Update GitHub label position 10 pixels from the right and 10 pixels from the bottom
        self.github_label.x = width - 10
        self.github_label.y = 10

        # Resize the invisible drag-and-drop area
        self.invisible_button.width = width
        self.invisible_button.height = height

        # Reposition the console messages
        self.update_console_positions()

    def update_console_positions(self):
        """Repositions the console lines dynamically from the bottom upwards, showing the latest messages."""
        y_pos = 40  # Start just above the GitHub label
        for i, label in enumerate(reversed(self.console_labels)):
            label.x = self.width // 2
            label.y = y_pos
            y_pos += 20
            if y_pos > self.browse_button.y - 20:  # Ensure messages don't cover the Browse button
                break

    def add_to_console(self, message, clear_last=False):
        """Adds a new line of text to the console, keeping only the latest messages visible."""
        if clear_last and self.console_labels:
            self.console_labels.pop()  # Remove the last label if clearing last message

        # Create a new label for the message
        new_label = pyglet.text.Label(message, font_name='Arial', font_size=12, anchor_x='center')
        self.console_labels.append(new_label)
        self.console_messages.append(message)

        # If more than max_console_lines, remove the oldest message
        if len(self.console_labels) > self.max_console_lines:
            self.console_labels.pop(0)
            self.console_messages.pop(0)

        # Update the positions of the labels
        self.update_console_positions()

    def on_mouse_press(self, x, y, button, modifiers):
        # Check if the user clicked the "Browse" button
        if self.browse_button.x < x < self.browse_button.x + self.browse_button.width and \
                self.browse_button.y < y < self.browse_button.y + self.browse_button.height:
            # Open file dialog when the "Browse" button is clicked
            self.select_image()

        # Check if the GitHub label is clicked
        if self.github_label.x - 100 < x < self.github_label.x + self.github_label.content_width and \
                self.github_label.y - 20 < y < self.github_label.y + self.github_label.content_height:
            self.add_to_console("Opening GitHub page...")
            # Open GitHub link
            self.open_github()

    def open_github(self):
        url = "https://github.com/Fklyf/Image2ASCII"
        try:
            if os.name == 'posix':
                subprocess.call(['xdg-open', url])
            elif os.name == 'nt':
                os.startfile(url)
        except Exception as e:
            self.add_to_console(f"Error opening GitHub: {e}")

    def on_file_drop(self, path):
        """Handles the drag-and-drop functionality."""
        if self.processing_started:
            return  # Ignore further input if processing has already started

        self.image_processed = False  # Reset image processing flag
        self.clear_console()  # Clear console when a new file is dropped
        if self.is_image(path):
            self.image_path = path
            self.add_to_console(f"Accepted image file: {self.image_path}")
            self.ask_for_dimensions(self.image_path)
        else:
            self.add_to_console(f"Rejected file: {path}. It is not a valid image format.")

    def clear_console(self):
        """Clears the console output."""
        self.console_labels.clear()
        self.console_messages.clear()

    def select_image(self):
        if self.processing_started:
            return  # Ignore further input if processing has already started

        # Hide the main tkinter window
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(title="Select Image", filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")])
        root.destroy()

        self.image_processed = False  # Reset image processing flag
        self.clear_console()  # Clear console when a new file is selected
        if file_path and self.is_image(file_path):
            self.image_path = file_path
            self.add_to_console(f"Selected image: {self.image_path}")
            self.ask_for_dimensions(self.image_path)
        else:
            self.add_to_console("Invalid image file selected.")

    def is_image(self, file_path):
        # Validate file by checking the file type using Pillow (more robust than just extension)
        try:
            with Image.open(file_path) as img:
                img.verify()  # Verify if it's an image file
            return True
        except (IOError, SyntaxError):
            return False

    def ask_for_dimensions(self, image_path):
        """Ask for width and height in a non-blocking way, showing in the console."""
        self.entering_width = True
        self.awaiting_input = True
        self.input_buffer = ""
        self.input_disabled = False  # Allow new input after resetting
        self.add_to_console("Enter desired width (leave blank for default):")

    def on_text(self, text):
        if self.awaiting_input and not self.processing_started and not self.input_disabled:  # Prevent spamming input
            if text == '\r':  # Enter key
                self.input_disabled = True  # Disable further input after pressing Enter
                if not self.input_buffer.strip():
                    self.add_to_console("No input provided, using default size.", clear_last=True)
                    if self.entering_width:
                        self.width_input = None  # Leave as None to use default
                        self.entering_width = False
                        self.input_disabled = False  # Re-enable input for height
                        self.add_to_console("Enter desired height (leave blank for default):")
                    else:
                        self.height_input = None  # Leave as None to use default
                        self.process_image()  # Process the image
                    self.input_buffer = ""
                    return

                if not self.input_buffer.isdigit():
                    self.add_to_console("Error: Please enter a valid number.")
                    self.input_buffer = ""  # Reset the input buffer
                    self.input_disabled = False  # Re-enable input if error occurs
                    return

                if self.entering_width:
                    self.add_to_console(f"Width entered: {self.input_buffer}", clear_last=True)
                    self.width_input = int(self.input_buffer)
                    self.input_buffer = ""
                    self.entering_width = False
                    self.input_disabled = False  # Re-enable input for height
                    self.add_to_console("Enter desired height (leave blank for default):")
                else:
                    self.add_to_console(f"Height entered: {self.input_buffer}", clear_last=True)
                    self.height_input = int(self.input_buffer)
                    self.input_buffer = ""
                    self.process_image()

            else:
                self.input_buffer += text
                self.add_to_console(self.input_buffer, clear_last=True)  # Update the console with the current input buffer

    def process_image(self):
        """Initiates image processing and prevents further input."""
        if not self.image_processed:
            self.processing_started = True  # Mark processing as started to prevent double input
            self.add_to_console("Processing image...")  # Show loading message
            self.convert_image_to_ascii(self.image_path, self.width_input, self.height_input)

    def convert_image_to_ascii(self, image_path, new_width=None, new_height=None):
        """Convert the image to ASCII art and save it."""
        try:
            image = Image.open(image_path)
        except Exception as e:
            self.add_to_console(f"Unable to open image file. Error: {e}")
            self.processing_started = False  # Reset processing flag if an error occurs
            self.input_disabled = False  # Allow re-entry after error
            return

        # Get the file name without extension for renaming
        file_name, _ = os.path.splitext(os.path.basename(image_path))

        if new_width is None:
            new_width = image.size[0]  # Default to image's original width
        if new_height is None:
            new_height = image.size[1]  # Default to image's original height

        # Resize and convert to grayscale
        image = resize_image(image, new_width=new_width, new_height=new_height)
        image = grayscale_image(image)

        # Convert to ASCII
        ascii_art = pixel_to_ascii(image)

        # Save the result to a file
        ascii_file_path = f"{file_name}_ASCII.txt"
        with open(ascii_file_path, "w") as f:
            f.write(ascii_art)
        self.add_to_console(f"ASCII art successfully written to {ascii_file_path}!")

        # Automatically open the ASCII file
        self.open_file(ascii_file_path)

        self.image_processed = True
        self.processing_started = False  # Allow new input after processing is complete

    def open_file(self, file_path):
        # Open the file with the default system program
        try:
            if os.name == 'posix':
                subprocess.call(['xdg-open', file_path])
            elif os.name == 'nt':
                os.startfile(file_path)
            else:
                self.add_to_console(f"Cannot open file: {file_path}. Unsupported OS.")
        except Exception as e:
            self.add_to_console(f"Error opening file: {e}")


# Resize the image, ensuring it fits within the given width and height while maintaining aspect ratio
def resize_image(image, new_width=None, new_height=None):
    original_width, original_height = image.size
    aspect_ratio = original_height / original_width

    # ASCII characters are roughly twice as tall as they are wide, so we adjust the aspect ratio
    aspect_ratio_adjustment = RATIO_ADJUSTMENT_NUM

    # If both width and height are given, adjust the height based on width to maintain aspect ratio
    if new_width and new_height:
        target_height = int(new_width * aspect_ratio / aspect_ratio_adjustment)
        if target_height > new_height:
            new_width = int(new_height * aspect_ratio_adjustment / aspect_ratio)
        else:
            new_height = target_height
    # If only the width is given, calculate the height
    elif new_width:
        new_height = int(new_width * aspect_ratio / aspect_ratio_adjustment)
    # If only the height is given, calculate the width
    elif new_height:
        new_width = int(new_height * aspect_ratio_adjustment / aspect_ratio)

    # Resize the image to the new dimensions
    return image.resize((new_width, new_height))


# Convert image to grayscale, and handle transparency
def grayscale_image(image):
    if image.mode in ('RGBA', 'LA'):  # Handle images with transparency
        grayscale_image = image.convert("L")  # Convert to grayscale
        alpha = image.getchannel('A')  # Get the alpha channel

        np_grayscale = np.array(grayscale_image)
        np_alpha = np.array(alpha)

        # Make transparent pixels white
        np_grayscale[np_alpha == 0] = 255
        return Image.fromarray(np_grayscale)

    return image.convert("L")  # Convert to grayscale


# Map the grayscale pixel values to ASCII characters
def pixel_to_ascii(image):
    pixels = np.array(image)
    ascii_str = ''
    for pixel_row in pixels:
        for pixel in pixel_row:
            ascii_str += ASCII_CHARS[pixel // 32] if pixel != 255 else ' '
        ascii_str += '\n'
    return ascii_str


if __name__ == "__main__":
    try:
        window = ImageApp()
        pyglet.app.run()
    except KeyboardInterrupt:
        print("Application stopped.")
