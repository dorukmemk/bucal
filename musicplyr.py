import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import pygame
import json
import os
from PIL import Image, ImageTk
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
import keyboard
import threading
import time
import customtkinter as ctk


class ModernMusicPlayer:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("BUCA ANADOLU LİSESİ")
        self.root.geometry("1000x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize pygame mixer
        pygame.mixer.init()

        # Variables
        self.songs = []
        self.current_song = None
        self.is_playing = False
        self.shortcuts_enabled = True
        self.shortcuts = {}
        self.restart_shortcut = None
        self.background_thread = None
        self.running = True

        # Create initial shortcut files if they don't exist
        self.initialize_shortcut_files()

        self.create_gui()
        self.load_shortcuts()
        self.load_restart_shortcut()
        self.start_background_thread()

    def add_song(self):
        """Add a new song to the playlist"""
        file_paths = filedialog.askopenfilenames(
            title="Müzik Dosyalarını Seç",
            filetypes=[("Müzik Dosyaları", "*.mp3 *.wav")],
        )

        for file_path in file_paths:
            if file_path:
                song_name = os.path.basename(file_path)
                # Check if song is already in playlist
                if file_path not in [song["path"] for song in self.songs]:
                    self.create_song_frame(file_path, song_name)

    def initialize_shortcut_files(self):
        """Create initial shortcut files if they don't exist"""
        if not os.path.exists("shortcuts.json"):
            with open("shortcuts.json", "w") as f:
                json.dump({}, f)

        if not os.path.exists("restart_shortcut.json"):
            with open("restart_shortcut.json", "w") as f:
                json.dump({"restart": None}, f)

    def create_gui(self):
        # Slider values
        self.fade_duration = tk.DoubleVar(value=2.0)  # Default fade duration in seconds
        # Main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Left panel - Controls
        self.left_panel = ctk.CTkFrame(self.main_container)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

        # Logo/Title
        self.title_label = ctk.CTkLabel(
            self.left_panel,
            text="BUCA ANADOLU \n LİSESİ",
            font=("Helvetica", 22, "bold"),
            text_color="#3498db",
        )
        self.title_label.pack(pady=20)

        # Control buttons
        self.create_control_buttons()

        # Duration indicator and progress bar
        # Song seek slider
        self.seek_slider = ctk.CTkSlider(
            self.left_panel, from_=0, to=100, command=self.seek_song
        )
        self.seek_slider.pack(fill=tk.X, padx=10, pady=5)

        # Fade duration slider
        self.fade_duration_slider = ctk.CTkSlider(
            self.left_panel,
            from_=0.5,
            to=5,
            variable=self.fade_duration,
            number_of_steps=9,
        )
        self.fade_duration_slider.pack(fill=tk.X, padx=10, pady=5)
        self.fade_duration_label = ctk.CTkLabel(
            self.left_panel, text="Fade Süresi (saniye)", font=("Helvetica", 12)
        )
        self.fade_duration_label.pack(pady=5)

        self.progress_frame = ctk.CTkFrame(self.left_panel)
        self.progress_frame.pack(fill=tk.X, pady=20, padx=10)

        self.time_label = ctk.CTkLabel(
            self.progress_frame, text="0:00 / 0:00", font=("Helvetica", 12)
        )
        self.time_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.set(0)

        # Right panel - Song list
        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Song list title
        self.playlist_label = ctk.CTkLabel(
            self.right_panel, text="Çalma Listesi", font=("Helvetica", 18, "bold")
        )
        self.playlist_label.pack(pady=10)

        # Song list scrollable frame
        self.create_song_list()

    def create_control_buttons(self):
        button_frame = ctk.CTkFrame(self.left_panel)
        button_frame.pack(pady=20)

        # Add song button
        self.add_button = ctk.CTkButton(
            button_frame,
            text="Şarkı Ekle",
            command=self.add_song,
            width=200,
            height=40,
            font=("Helvetica", 14),
        )
        self.add_button.pack(pady=5)

        # Shortcut button
        self.shortcut_button = ctk.CTkButton(
            button_frame,
            text="Kısayollar Aktif",
            command=self.toggle_shortcuts,
            width=200,
            height=40,
            font=("Helvetica", 14),
        )
        self.shortcut_button.pack(pady=5)

        # Restart button
        self.restart_button = ctk.CTkButton(
            button_frame,
            text="Başa Al",
            command=self.restart_song,
            width=200,
            height=40,
            font=("Helvetica", 14),
        )
        self.restart_button.pack(pady=5)

        # Restart shortcut button
        self.restart_shortcut_button = ctk.CTkButton(
            button_frame,
            text="Başa Al Kısayolu",
            command=self.set_restart_shortcut,
            width=200,
            height=40,
            font=("Helvetica", 14),
        )
        self.restart_shortcut_button.pack(pady=5)

    def create_song_list(self):
        # Scrollable frame container
        self.song_list_frame = ctk.CTkScrollableFrame(
            self.right_panel, width=600, height=400
        )
        self.song_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def delete_song(self, file_path, song_frame):
        """Delete a song from the playlist"""
        # Ask for confirmation
        if messagebox.askyesno(
            "Şarkıyı Sil", "Bu şarkıyı silmek istediğinizden emin misiniz?"
        ):
            # Stop the song if it's currently playing
            if self.current_song and self.current_song["path"] == file_path:
                pygame.mixer.music.stop()
                self.is_playing = False
                self.current_song = None
                self.time_label.configure(text="0:00 / 0:00")
                self.progress_bar.set(0)

            # Remove the song from the list
            self.songs = [song for song in self.songs if song["path"] != file_path]

            # Remove any shortcuts associated with this song
            keys_to_remove = []
            for key, path in self.shortcuts.items():
                if path == file_path:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self.shortcuts[key]
            self.save_shortcuts()

            # Remove the song frame from the GUI
            song_frame.destroy()

    def create_song_frame(self, file_path, song_name):
        song_frame = ctk.CTkFrame(self.song_list_frame)
        song_frame.pack(fill=tk.X, padx=5, pady=2)

        var = tk.BooleanVar()

        # Song name and checkbox
        song_button = ctk.CTkButton(
            song_frame,
            text=song_name,
            command=lambda p=file_path: self.toggle_song(p),
            width=300,
            height=30,
            anchor="w",
        )
        song_button.pack(side=tk.LEFT, padx=5)

        # Duration label
        length = self.get_audio_length(file_path)
        duration_label = ctk.CTkLabel(
            song_frame, text=self.format_time(length), width=70
        )
        duration_label.pack(side=tk.LEFT, padx=5)

        # Control buttons
        button_frame = ctk.CTkFrame(song_frame)
        button_frame.pack(side=tk.RIGHT, padx=5)

        # Delete button
        delete_button = ctk.CTkButton(
            button_frame,
            text="Sil",
            command=lambda: self.delete_song(file_path, song_frame),
            width=60,
            height=25,
            fg_color="#FF3B30",  # Kırmızı renk
            hover_color="#FF6B6B",  # Hover durumunda daha açık kırmızı
        )
        delete_button.pack(side=tk.LEFT, padx=2)

        rename_button = ctk.CTkButton(
            button_frame,
            text="Yeniden Adlandır",
            command=lambda: self.rename_song(file_path, song_button),
            width=120,
            height=25,
        )
        rename_button.pack(side=tk.LEFT, padx=2)

        shortcut_button = ctk.CTkButton(
            button_frame,
            text="Kısayol Ata",
            command=lambda p=file_path: self.set_shortcut(p),
            width=100,
            height=25,
        )
        shortcut_button.pack(side=tk.LEFT, padx=2)

        self.songs.append(
            {
                "path": file_path,
                "name": song_name,
                "checkbox": var,
                "position": 0,
                "length": length,
                "duration_label": duration_label,
                "button": song_button,
            }
        )

    def get_audio_length(self, file_path):
        try:
            if file_path.lower().endswith(".mp3"):
                audio = MP3(file_path)
            elif file_path.lower().endswith(".wav"):
                audio = WAVE(file_path)
            return audio.info.length
        except:
            return 0

    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"

    def update_time_label(self):
        if self.current_song and self.is_playing:
            current_pos = pygame.mixer.music.get_pos() / 1000
            if current_pos >= 0:
                total_length = self.current_song["length"]
                current_pos += self.current_song["position"]
                self.time_label.configure(
                    text=f"{self.format_time(current_pos)} / {self.format_time(total_length)}"
                )
                # Update progress bar
                if total_length > 0:
                    progress = current_pos / total_length
                    self.progress_bar.set(progress)

    def toggle_song(self, path):
        if self.current_song and self.current_song["path"] == path:
            if self.is_playing:
                self.fade_out_song()  # Fade out before pausing
                self.is_playing = False
                self.current_song["button"].configure(fg_color=("gray75", "gray30"))
            else:
                self.current_song["position"] += pygame.mixer.music.get_pos() / 1000
                self.fade_in_song()  # Fade in when resuming
                self.is_playing = True
                self.current_song["button"].configure(fg_color=["#3B8ED0", "#1F6AA5"])
        else:
            if self.current_song:
                self.current_song["position"] += pygame.mixer.music.get_pos() / 1000
                self.current_song["button"].configure(fg_color=("gray75", "gray30"))

            for song in self.songs:
                if song["path"] == path:
                    self.current_song = song
                    self.fade_in_song()  # Fade in when starting a new song
                    self.is_playing = True
                    song["button"].configure(fg_color=["#3B8ED0", "#1F6AA5"])
                    break

    def restart_song(self):
        if self.current_song:
            self.current_song["position"] = 0
            pygame.mixer.music.rewind()
            self.time_label.configure(
                text=f"0:00 / {self.format_time(self.current_song['length'])}"
            )
            self.progress_bar.set(0)

    def fade_out_song(self):
        if self.current_song and self.is_playing:
            fade_time = int(
                self.fade_duration.get() * 1000
            )  # Adjustable fade out duration
            pygame.mixer.music.fadeout(fade_time)
            time.sleep(fade_time / 1000)
            pygame.mixer.music.pause()

    def seek_song(self, value):
        if self.current_song:
            new_position = float(value) / 100 * self.current_song["length"]
            self.current_song["position"] = new_position
            if self.is_playing:
                pygame.mixer.music.play(start=new_position)

    def fade_in_song(self):
        if self.current_song:
            path = self.current_song["path"]
            position = self.current_song["position"]
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(start=position, fade_ms=2000)

    def rename_song(self, file_path, song_button):
        song = next((s for s in self.songs if s["path"] == file_path), None)
        if song:
            new_name = simpledialog.askstring(
                "Yeniden Adlandır", "Yeni şarkı adı:", initialvalue=song["name"]
            )
            if new_name:
                song["name"] = new_name
                song_button.configure(text=new_name)

    def set_shortcut(self, path):
        def save_shortcut(event):
            key = event.keysym
            self.shortcuts[key] = path
            self.save_shortcuts()
            shortcut_window.destroy()
            messagebox.showinfo(
                "Kısayol Atandı", f"'{key}' tuşu bu şarkı için kısayol olarak atandı."
            )

        shortcut_window = ctk.CTkToplevel(self.root)
        shortcut_window.title("Kısayol Ata")
        shortcut_window.geometry("300x150")

        label = ctk.CTkLabel(
            shortcut_window,
            text="Bir tuşa basın (örn: a, b, space)",
            font=("Helvetica", 14),
        )
        label.pack(pady=20)

        shortcut_window.bind("<Key>", save_shortcut)

    def set_restart_shortcut(self):
        def save_shortcut(event):
            key = event.keysym
            self.restart_shortcut = key
            self.save_restart_shortcut()
            shortcut_window.destroy()
            messagebox.showinfo(
                "Kısayol Atandı", f"'{key}' tuşu başa alma kısayolu olarak atandı."
            )

        shortcut_window = ctk.CTkToplevel(self.root)
        shortcut_window.title("Başa Alma Kısayolu")
        shortcut_window.geometry("300x150")

        label = ctk.CTkLabel(
            shortcut_window,
            text="Bir tuşa basın (örn: r, home)",
            font=("Helvetica", 14),
        )
        label.pack(pady=20)

        shortcut_window.bind("<Key>", save_shortcut)

    def background_listener(self):
        while self.running:
            if self.shortcuts_enabled:
                for key in self.shortcuts:
                    if keyboard.is_pressed(key):
                        path = self.shortcuts[key]
                        self.root.after(0, lambda p=path: self.handle_shortcut(p))
                        time.sleep(0.2)

                if self.restart_shortcut and keyboard.is_pressed(self.restart_shortcut):
                    self.root.after(0, self.restart_song)
                    time.sleep(0.2)

            if self.is_playing:
                self.root.after(0, self.update_time_label)
            time.sleep(0.1)

    def handle_shortcut(self, path):
        """Handle the song playback for a given shortcut."""
        for song in self.songs:
            if song["path"] == path:
                if self.current_song and self.current_song["path"] == path:
                    # If the current song is already playing, toggle its state
                    self.toggle_song(path)
                else:
                    # Stop the current song and play the selected one
                    if self.current_song:
                        self.current_song["position"] += (
                            pygame.mixer.music.get_pos() / 1000
                        )
                        self.current_song["button"].configure(
                            fg_color=("gray75", "gray30")
                        )
                    self.current_song = song
                    self.fade_in_song()  # Fade in the selected song
                    self.is_playing = True
                    song["button"].configure(fg_color=["#3B8ED0", "#1F6AA5"])
                break

    def toggle_shortcuts(self):
        """Toggle shortcut activation state."""
        self.shortcuts_enabled = not self.shortcuts_enabled
        text = "Kısayollar Aktif" if self.shortcuts_enabled else "Kısayollar Pasif"
        self.shortcut_button.configure(text=text)

    def save_shortcuts(self):
        """Save the shortcuts to a JSON file."""
        with open("shortcuts.json", "w") as f:
            json.dump(self.shortcuts, f)

    def load_shortcuts(self):
        """Load the shortcuts from a JSON file."""
        try:
            with open("shortcuts.json", "r") as f:
                content = f.read()
                if content.strip():  # Check if file is not empty
                    self.shortcuts = json.loads(content)
                else:
                    self.shortcuts = {}
                    # Initialize with empty dictionary if file is empty
                    with open("shortcuts.json", "w") as f:
                        json.dump({}, f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.shortcuts = {}
            # Create new file with empty dictionary if error occurs
            with open("shortcuts.json", "w") as f:
                json.dump({}, f)

    def save_restart_shortcut(self):
        """Save the restart shortcut to a JSON file."""
        with open("restart_shortcut.json", "w") as f:
            json.dump({"restart": self.restart_shortcut}, f)

    def load_restart_shortcut(self):
        """Load the restart shortcut from a JSON file."""
        try:
            with open("restart_shortcut.json", "r") as f:
                content = f.read()
                if content.strip():  # Check if file is not empty
                    data = json.loads(content)
                    self.restart_shortcut = data.get("restart")
                else:
                    self.restart_shortcut = None
                    # Initialize with default values if file is empty
                    with open("restart_shortcut.json", "w") as f:
                        json.dump({"restart": None}, f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.restart_shortcut = None
            # Create new file with default values if error occurs
            with open("restart_shortcut.json", "w") as f:
                json.dump({"restart": None}, f)

    def start_background_thread(self):
        """Start the background thread for listening to shortcuts."""
        self.background_thread = threading.Thread(target=self.background_listener)
        self.background_thread.daemon = True
        self.background_thread.start()

    def on_closing(self):
        """Handle application closing events."""
        self.running = False
        if self.background_thread:
            self.background_thread.join(timeout=1.0)
        self.root.destroy()

    def run(self):
        """Run the main application loop."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


if __name__ == "__main__":
    player = ModernMusicPlayer()
    player.run()
