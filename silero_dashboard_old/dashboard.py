import tkinter as tk
from tkinter import filedialog
import subprocess
import pygame
import threading
import time
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

def open_file():
    file_path = filedialog.askopenfilename(
        filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
    )
    if file_path:
        file_label.config(text=f"File selezionato: {file_path}")
        run_main_py(file_path)
        load_audio(file_path)

def run_main_py(file_path):
    try:
        # Eseguire il comando python main.py <file_path>
        result = subprocess.run(
            ["python", "main.py", file_path],
            capture_output=True,
            text=True
        )
        # Mostrare l'output del comando
        if result.returncode == 0:
            output_text.insert(tk.END, f"Output:\n{result.stdout}\n")
        else:
            output_text.insert(tk.END, f"Errore:\n{result.stderr}\n")
    except Exception as e:
        output_text.insert(tk.END, f"Errore durante l'esecuzione: {e}\n")

def load_audio(file_path):
    global audio_file, audio_length
    audio_file = file_path
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    audio_length = pygame.mixer.Sound(audio_file).get_length()
    progress_bar.config(to=audio_length)

def play_audio():
    if audio_file:
        pygame.mixer.music.play()
        update_progress_bar()

def pause_audio():
    pygame.mixer.music.pause()

def unpause_audio():
    pygame.mixer.music.unpause()
    update_progress_bar()

def update_progress_bar():
    def run():
        while pygame.mixer.music.get_busy():
            current_time = pygame.mixer.music.get_pos() / 1000
            progress_bar.set(current_time)
            time.sleep(0.1)
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()

def display_plot(plot_path):
    image = tk.PhotoImage(file=plot_path)
    plot_label.config(image=image)
    plot_label.image = image

def execute_dsp():
    if audio_file and selected_number.get():
        try:
            # Eseguire il comando python dsp.py <selected_number> <file_path>
            result = subprocess.run(
                ["python", "dsp.py", selected_number.get(), audio_file],
                capture_output=True,
                text=True
            )
            # Aggiungere l'output del comando alla casella di testo
            if result.returncode == 0:
                new_output = f"Output:\n{result.stdout}\n"
            else:
                new_output = f"Errore:\n{result.stderr}\n"
            
            output_text.insert(tk.END, new_output)
            output_text.yview(tk.END)  # Scorrere automaticamente verso il basso

        except Exception as e:
            # Aggiungere l'errore alla casella di testo
            output_text.insert(tk.END, f"Errore durante l'esecuzione: {e}\n")
            output_text.yview(tk.END)
    else:
        # Messaggio di errore se non è stato selezionato un file o un numero
        output_text.insert(tk.END, "Seleziona un file e un numero prima di eseguire.\n")
        output_text.yview(tk.END)

# Creare la finestra principale
root = tk.Tk()
root.title("WAV File Loader")
root.geometry("800x600")  # Impostare le dimensioni della finestra

# Variabile globale per l'audio
audio_file = None
audio_length = 0

# Variabile per il numero selezionato
selected_number = tk.StringVar(value="1")

# Creare e posizionare il pulsante di esplorazione file e i pulsanti di controllo
button_frame = tk.Frame(root)
button_frame.pack(pady=20)

button = tk.Button(button_frame, text="Esplora file", command=open_file)
button.grid(row=0, column=0, padx=5)

play_button = tk.Button(button_frame, text="Play", command=play_audio)
play_button.grid(row=0, column=1, padx=5)

pause_button = tk.Button(button_frame, text="Pause", command=pause_audio)
pause_button.grid(row=0, column=2, padx=5)

unpause_button = tk.Button(button_frame, text="Unpause", command=unpause_audio)
unpause_button.grid(row=0, column=3, padx=5)

# Creare e posizionare l'etichetta per mostrare il percorso del file
file_label = tk.Label(root, text="Nessun file selezionato")
file_label.pack(pady=10)

# Creare e posizionare la barra di avanzamento
progress_bar = tk.Scale(root, from_=0, to=audio_length, orient='horizontal', length=500)
progress_bar.pack(pady=10)

# Creare un menu a tendina per selezionare un numero da 1 a 8
number_menu = tk.OptionMenu(root, selected_number, *map(str, range(1, 9)))
number_menu.pack(pady=10)

# Creare e posizionare il pulsante "Execute"
execute_button = tk.Button(root, text="Execute", command=execute_dsp)
execute_button.pack(pady=10)

# Creare un frame per la casella di testo e la barra di scorrimento
output_frame = tk.Frame(root)
output_frame.pack(pady=10, fill=tk.BOTH, expand=True)

# Creare una casella di testo per mostrare l'output del comando
output_text = tk.Text(output_frame, wrap=tk.WORD, height=10)
output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Creare una barra di scorrimento verticale
scrollbar = tk.Scrollbar(output_frame, command=output_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Collegare la barra di scorrimento alla casella di testo
output_text.config(yscrollcommand=scrollbar.set)

# Creare un'etichetta per il grafico
plot_label = tk.Label(root)
plot_label.pack(pady=10)

# Avviare il loop principale di Tkinter
root.mainloop()
