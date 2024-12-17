with open("test_admin_file.txt", "w") as file:
    file.write("Questo è un file di test che richiede permessi di admin per essere eliminato.")


import subprocess
import os

# Modifica dei permessi per negare l'eliminazione a tutti gli utenti tranne l'amministratore
file_path = "test_admin_file.txt"
try:
    subprocess.run(['icacls', file_path, '/deny', f'{os.getlogin()}:D'], check=True)
    print(f"Permessi del file {file_path} modificati con successo!")
except subprocess.CalledProcessError as e:
    print(f"Errore durante la modifica dei permessi: {e}")
