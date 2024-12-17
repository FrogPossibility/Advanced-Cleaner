import tkinter as tk
from tkinter import ttk
import shutil
import os
import tempfile
import threading
import winreg
import send2trash
import winshell
import psutil
import subprocess
from tkinter import messagebox
import ctypes
import sys
import errno
import logging

# Configurazione del logger
logging.basicConfig(filename='cleaner.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    try:
        script = sys.executable
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Errore di amministrazione", f"Impossibile avviare come amministratore: {str(e)}")
        sys.exit(1)

class CleanerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Advanced Cleaner")
        self.geometry("500x650")
        self.configure(bg="#f0f0f0")

        style = ttk.Style(self)
        style.theme_use("clam")
        
        style.configure("TButton", padding=10, relief="flat", background="#4CAF50", foreground="white")
        style.map("TButton", background=[("active", "#45a049")])

        self.folders_to_clean = {
            'Temp': tempfile.gettempdir(),
            'Windows Temp': os.path.expandvars(r'%SystemRoot%\Temp'),
            'Prefetch': os.path.expandvars(r'%SystemRoot%\Prefetch'),
            'Recycle Bin': 'RECYCLE_BIN',
            'Chrome Downloads': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Downloads'),
            'Firefox Downloads': os.path.expandvars(r'%APPDATA%\Mozilla\Firefox\Profiles'),
            'Edge Downloads': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Downloads'),
            'Windows Update Cache': os.path.expandvars(r'%SystemRoot%\SoftwareDistribution\Download'),
            'Windows Error Reports': os.path.expandvars(r'%LOCALAPPDATA%\CrashDumps'),
            'Event Logs': os.path.expandvars(r'%SystemRoot%\System32\winevt\Logs'),
            'Old Windows Updates': os.path.expandvars(r'%SystemRoot%\WinSxS\Backup'),
            'Windows Defender Cache': os.path.expandvars(r'%ProgramData%\Microsoft\Windows Defender\Scans\History'),
            'Temporary Internet Files': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Windows\INetCache'),
            'DirectX Shader Cache': os.path.expandvars(r'%LOCALAPPDATA%\D3DSCache'),
            'System Error Memory Dump Files': os.path.expandvars(r'%SystemRoot%\Minidump'),
            'Windows Installer Cache': os.path.expandvars(r'%SystemRoot%\Installer\$PatchCache$'),
            'Thumbnails Cache': os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Windows\Explorer'),
            'Windows Logs': os.path.expandvars(r'%SystemRoot%\Logs'),
            'Delivery Optimization Cache': os.path.expandvars(r'%SystemRoot%\SoftwareDistribution\DeliveryOptimization\Cache'),
            'test1': os.path.expandvars(r'C:\Users\Simone\OneDrive\Desktop\Cleaner\test_admin_file.txt'),
        }

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Advanced Cleaner", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))

        self.checkbuttons = {}
        for folder_name in self.folders_to_clean.keys():
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(main_frame, text=folder_name, variable=var)
            cb.pack(anchor="w")
            self.checkbuttons[folder_name] = var

        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.pack(pady=(20, 20))

        self.clean_button = ttk.Button(main_frame, text="Pulisci", command=self.start_cleaning)
        self.clean_button.pack(pady=(0, 10))

        self.status_label = ttk.Label(main_frame, text="Pronto", font=("Helvetica", 10))
        self.status_label.pack()

        self.space_label = ttk.Label(main_frame, text="", font=("Helvetica", 10))
        self.space_label.pack(pady=(10, 0))

        self.result_label = ttk.Label(main_frame, text="", font=("Helvetica", 10), wraplength=450, justify="center")
        self.result_label.pack(pady=(10, 0))

    def start_cleaning(self):
        self.clean_button.config(state="disabled")
        self.status_label.config(text="Calcolo spazio da eliminare...")
        self.progress['value'] = 0
        self.result_label.config(text="")
        self.space_label.config(text="")
        self.update_idletasks()

        threading.Thread(target=self.clean_system, daemon=True).start()

    def clean_system(self):
        total_files_deleted = 0
        total_files_skipped = 0
        total_space_before = 0
        total_space_after = 0

        selected_folders = [folder for folder, var in self.checkbuttons.items() if var.get()]
        total_folders = len(selected_folders)

        # Calcola lo spazio iniziale
        for folder_name in selected_folders:
            folder_path = self.folders_to_clean[folder_name]
            if folder_path != 'RECYCLE_BIN':
                total_space_before += self.get_folder_size(folder_path)
            else:
                total_space_before += self.get_recycle_bin_size()

        self.space_label.config(text=f"Spazio occupato da pulire: {self.format_size(total_space_before)}")
        self.update_idletasks()

        # Pulisce le cartelle
        for i, folder_name in enumerate(selected_folders):
            folder_path = self.folders_to_clean[folder_name]
            self.status_label.config(text=f"Pulizia di {folder_name}...")

            if folder_path == 'RECYCLE_BIN':
                self.empty_recycle_bin()
            else:
                files_deleted, files_skipped = self.clean_folder(folder_path)
                total_files_deleted += files_deleted
                total_files_skipped += files_skipped
            
            self.progress['value'] = int((i + 1) / total_folders * 100)
            self.update_idletasks()

        # Aggiunta pulizia delle cartelle degli utenti
        for user_folder in self.get_user_folders():
            self.status_label.config(text=f"Pulizia cartella utente: {user_folder}")
            files_deleted, files_skipped = self.clean_user_temp_folders(user_folder)
            total_files_deleted += files_deleted
            total_files_skipped += files_skipped

        # Calcola lo spazio dopo la pulizia
        for folder_name in selected_folders:
            folder_path = self.folders_to_clean[folder_name]
            if folder_path != 'RECYCLE_BIN':
                total_space_after += self.get_folder_size(folder_path)
            else:
                total_space_after += self.get_recycle_bin_size()

        space_freed = total_space_before - total_space_after
        result_text = f"Pulizia completata!\nTotale file eliminati: {total_files_deleted}\nTotale file saltati: {total_files_skipped}\n"
        result_text += f"Spazio liberato: {self.format_size(space_freed)}"

        self.status_label.config(text="Pulizia completata!")
        self.result_label.config(text=result_text)
        self.space_label.config(text=f"Spazio occupato pre-pulizia: {self.format_size(total_space_before)}\nSpazio occupato post-pulizia: {self.format_size(total_space_after)}")
        self.clean_button.config(state="normal")

    def get_user_folders(self):
        """Ottiene la lista delle cartelle utente."""
        user_folders = []
        base_path = r"C:\Users"
        try:
            for item in os.listdir(base_path):
                full_path = os.path.join(base_path, item)
                if os.path.isdir(full_path) and item not in ['Public', 'Default', 'Default User', 'All Users']:
                    user_folders.append(full_path)
        except Exception as e:
            logging.error(f"Errore nell'accesso alle cartelle utente: {e}")
        return user_folders

    def clean_user_temp_folders(self, user_folder):
        """Pulisce le cartelle temporanee specifiche dell'utente."""
        files_deleted = 0
        files_skipped = 0
        
        temp_folders = [
            os.path.join(user_folder, 'AppData', 'Local', 'Temp'),
            os.path.join(user_folder, 'AppData', 'Local', 'Microsoft', 'Windows', 'Temporary Internet Files'),
            os.path.join(user_folder, 'AppData', 'Local', 'Microsoft', 'Windows', 'INetCache')
        ]

        for temp_folder in temp_folders:
            if os.path.exists(temp_folder):
                deleted, skipped = self.clean_folder(temp_folder)
                files_deleted += deleted
                files_skipped += skipped

        return files_deleted, files_skipped

    def clean_folder(self, folder_path):
        """Pulisce una cartella e ritorna il numero di file eliminati e saltati."""
        files_deleted = 0
        files_skipped = 0

        if not os.path.exists(folder_path):
            return files_deleted, files_skipped

        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    self.status_label.config(text=f"Eliminazione: {file_path}")
                    self.update_idletasks()

                    # Prima prova a eliminare normalmente
                    try:
                        os.remove(file_path)
                        files_deleted += 1
                        continue
                    except PermissionError:
                        pass

                    # Se fallisce, prova con i comandi di sistema
                    try:
                        # Prendi possesso del file
                        subprocess.run(['takeown', '/F', file_path], check=True, capture_output=True)
                        
                        # Dai i permessi completi
                        subprocess.run(['icacls', file_path, '/grant', f'{os.getenv("USERNAME")}:F'], 
                                    check=True, capture_output=True)
                        
                        # Riprova a eliminare
                        os.remove(file_path)
                        files_deleted += 1
                    except:
                        files_skipped += 1
                except Exception as e:
                    logging.error(f"Errore con il file {file_path}: {str(e)}")
                    files_skipped += 1

            # Prova a eliminare le cartelle vuote
            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    os.rmdir(dir_path)
                except:
                    pass

        return files_deleted, files_skipped

    def empty_recycle_bin(self):
        try:
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        except Exception as e:
            self.status_label.config(text=f"Errore durante lo svuotamento del Cestino: {e}")

    def get_recycle_bin_size(self):
        try:
            return sum(item.size() for item in winshell.recycle_bin())
        except Exception:
            return 0

    def get_folder_size(self, folder_path):
        total_size = 0
        if not os.path.exists(folder_path):
            return total_size
            
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
        return total_size

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def update_idletasks(self):
        try:
            self.update()
        except tk.TclError:
            pass

if __name__ == "__main__":
    if not is_admin():
        run_as_admin()
    else:
        app = CleanerApp()
        app.mainloop()