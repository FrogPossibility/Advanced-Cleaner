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
import logging  # Importa il modulo logging

# Configurazione del logger
logging.basicConfig(filename='cleaner.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def is_admin():
    """Controlla se lo script è in esecuzione con privilegi di amministratore."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Riavvia lo script con privilegi di amministratore."""
    try:
        script = sys.executable
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Errore di amministrazione", f"Impossibile avviare come amministratore: {str(e)}")
        sys.exit(1)

# Verifica e richiede i privilegi di amministratore
if not is_admin():
    root = tk.Tk()
    root.withdraw()  # Nasconde la finestra Tkinter durante l'elevazione
    run_as_admin()


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
            'Windows Update Cache (!)': os.path.expandvars(r'%SystemRoot%\SoftwareDistribution\Download'),

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
            'Delivery Optimization Cache': os.path.expandvars(r'%SystemRoot%\SoftwareDistribution\DeliveryOptimization\Cache')
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

    def find_process_using_file(file_path):
        """Trova il processo che sta usando il file"""
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                for f in proc.info['open_files'] or []:
                    if f.path == file_path:
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None
    
    def acquire_file_permissions(file_path):
        """Prova ad acquisire i permessi di un file utilizzando icacls"""
        try:
            # Tentativo di acquisizione dei permessi completi per il file
            result = subprocess.run(['icacls', file_path, '/grant', f'{os.getlogin()}:F'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                logging.info(f"Impossibile acquisire i permessi per {file_path}: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Errore durante l'acquisizione dei permessi per {file_path}: {str(e)}")
            return False

    def start_cleaning(self):
        self.clean_button.config(state="disabled")
        self.status_label.config(text="Calcolo spazio da eliminare...")
        self.progress['value'] = 0
        self.result_label.config(text="")
        self.space_label.config(text="")
        self.update_idletasks()

        # Start cleaning in a separate thread
        threading.Thread(target=self.clean_system, daemon=True).start()

    def clean_system(self):
        total_files_deleted = 0
        total_files_skipped = 0
        total_space_before = 0
        total_space_after = 0

        selected_folders = [folder for folder, var in self.checkbuttons.items() if var.get()]
        total_folders = len(selected_folders)

        # Calculate initial space
        for folder_name in selected_folders:
            folder_path = self.folders_to_clean[folder_name]
            if folder_path != 'RECYCLE_BIN':
                total_space_before += self.get_folder_size(folder_path)
            else:
                total_space_before += self.get_recycle_bin_size()

        self.space_label.config(text=f"Spazio occupato da pulire: {self.format_size(total_space_before)}")
        self.update_idletasks()

        # Clean folders
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

        # Calculate space after cleaning
        for folder_name in selected_folders:
            folder_path = self.folders_to_clean[folder_name]
            if folder_path != 'RECYCLE_BIN':
                total_space_after += self.get_folder_size(folder_path)
            else:
                total_space_after += self.get_recycle_bin_size()

        space_freed = total_space_before - total_space_after
        result_text = f"Pulizia completata!\nTotale file eliminati: {total_files_deleted}\nTotale file saltati: {total_files_skipped}\n"
        result_text += f"SPAZIO LIBERATO: {self.format_size(space_freed)}"
        
        self.status_label.config(text="Pulizia completata!")
        self.result_label.config(text=result_text)
        self.space_label.config(text=f"Spazio occupato pre-pulizia {self.format_size(total_space_before)}\nSpazio occupato post-pulizia: {self.format_size(total_space_after)}")
        self.clean_button.config(state="normal")

    def clean_folder(self, folder_path):
        files_deleted = 0
        files_skipped = 0

        try:
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        self.status_label.config(text=f"Eliminazione: {file_path}")
                        self.update_idletasks()
                        send2trash.send2trash(file_path)
                        files_deleted += 1
                    except Exception as e:
                        if isinstance(e, PermissionError):
                            logging.info(f"Permesso negato: {file_path}. Provo ad acquisire i permessi.")
                            
                            # Provo ad acquisire i permessi del file
                            if self.acquire_file_permissions(file_path):
                                try:
                                    send2trash.send2trash(file_path)
                                    files_deleted += 1
                                except Exception as inner_e:
                                    logging.error(f"Non è possibile eliminare il file {file_path} dopo aver acquisito i permessi: {str(inner_e)}")
                                    files_skipped += 1
                            else:
                                logging.error(f"Impossibile acquisire i permessi per {file_path}")
                                files_skipped += 1
                        elif isinstance(e, OSError):
                            logging.error(f"Errore generale con il file {file_path}: {str(e)}")
                            files_skipped += 1
                        else:
                            proc = self.find_process_using_file(file_path)
                            if proc:
                                close_program = tk.messagebox.askyesno(
                                    "Programma in esecuzione",
                                    f"Il file '{file_path}' è in uso da '{proc.name()}'. Vuoi chiudere il programma?"
                                )
                                if close_program:
                                    try:
                                        proc.terminate()
                                        proc.wait(timeout=5)  # Attendere che il processo venga chiuso
                                        send2trash.send2trash(file_path)  # Riprova ad eliminare il file
                                        files_deleted += 1
                                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                                        logging.info(f"Impossibile terminare il processo: {proc.name()}")
                                        files_skipped += 1
                                else:
                                    files_skipped += 1
                            else:
                                logging.error(f"Impossibile eliminare il file: {file_path}. Motivo sconosciuto.")
                                files_skipped += 1
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        self.status_label.config(text=f"Eliminazione: {dir_path}")
                        self.update_idletasks()
                        send2trash.send2trash(dir_path)
                        files_deleted += 1
                    except Exception as e:
                        if isinstance(e, PermissionError):
                            logging.info(f"Permesso negato: {dir_path}. Provo ad acquisire i permessi.")
                            
                            if self.acquire_file_permissions(dir_path):
                                try:
                                    send2trash.send2trash(dir_path)
                                    files_deleted += 1
                                except Exception as inner_e:
                                    logging.error(f"Non è possibile eliminare la directory {dir_path} dopo aver acquisito i permessi: {str(inner_e)}")
                                    files_skipped += 1
                            else:
                                logging.error(f"Impossibile acquisire i permessi per {dir_path}")
                                files_skipped += 1
                        else:
                            logging.error(f"Errore generale con la directory {dir_path}: {str(e)}")
                            files_skipped += 1
        except Exception as e:
            self.status_label.config(text=f"Errore nell'accesso alla directory {folder_path}: {e}")

        return files_deleted, files_skipped

    def empty_recycle_bin(self):
        try:
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        except Exception as e:
            self.status_label.config(text=f"Error emptying Recycle Bin: {e}")

    def get_recycle_bin_size(self):
        try:
            return sum(item.size() for item in winshell.recycle_bin())
        except Exception:
            return 0

    def get_folder_size(self, folder_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
        return total_size

    def format_size(self, size):
        # Convert bytes to human-readable format
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def update_idletasks(self):
        try:
            self.update()
        except tk.TclError:
            pass  # Ignore if the window has been closed


if __name__ == "__main__":
    app = CleanerApp()
    app.mainloop()