import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import wave
import pyaudio
import threading
import subprocess
import pygame
import csv
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sileroVAD
import numpy as np
import sys
import signal
from gpiozero import OutputDevice
import time

# Configura i pin GPIO
LED_PINS = [17, 27, 22]  # Pin per i LED (GPIO 17, 27, 22)

# Crea una lista di OutputDevice per i LED
leds = [OutputDevice(pin) for pin in LED_PINS]

# Funzione per aggiornare i LED
def update_leds(value):
    # Converte il valore da 0 a 7 in binario e controlla i LED
    for i in range(3):  # Ci sono 3 LED da controllare
        if value >> (2 - i) & 1:
            leds[i].on()  # Accendi il pin
        else:
            leds[i].off()  # Spegni il pin



# Funzione per la checkbox
def on_checkbox_toggle():
    if checkbox_var.get():
        dropdown.config(state="disabled")
        # da modificare con output di silero
        update_leds(0)
    else:
        dropdown.config(state="readonly")
        if filter_var.get() == "Nessun filtro":
            update_leds(0)
        else:
            update_leds(int(filter_var.get()))

# Funzione per la selezione del filtro
def on_filter_select(event):
    if filter_var.get() == "Nessun filtro":
        update_leds(0)
    else:
        update_leds(int(filter_var.get()))


# Funzione per selezionare un file
file_path = ""
playing = False
stop_event = threading.Event()
voiced_confidences = []
empty_list = []

# Definisci una variabile globale per memorizzare il riferimento alla Label
label = None

def draw_plot(voiced_confidences, Leq_list):
    global label  # Usa la variabile globale per tenere traccia della Label
    
    # Calcola la durata in secondi
    duration_seconds = (len(voiced_confidences) * 512) / 16000
    
    # Crea un array di valori per l'asse X, con numeri che vanno da 0 a duration_seconds
    x_values = np.linspace(0, duration_seconds, len(voiced_confidences))
    
    # Pulisce il plot esistente
    ax.cla()
    ax2.cla()
    
    # Plotta i valori di voiced_confidences in corrispondenza degli x_values
    ax.plot(x_values, voiced_confidences, marker='', linestyle='-', color='blue', label="Confidenze Voce")
    
    # Plotta i valori di Leq_list sul secondo asse Y (rosso)
    x_values_leq = np.arange(1, len(Leq_list) + 1)
    ax2.plot(x_values_leq, Leq_list, lw=2, color='red', label='Liv. eq. Decibel')
    
    # Imposta il titolo e le etichette per entrambi gli assi
    ax.set_xlabel("Tempo (secondi)")
    ax.set_ylabel("", color='blue')
    ax2.set_ylabel("", color='red')
    
    # Imposta i limiti dell'asse Y per il plot blu
    ax.set_ylim(0, 1.1)
    ax.set_yticks(np.arange(0, 1.1, 0.1))
    
    # Imposta i limiti dell'asse Y per il plot rosso (con il massimo valore + 4)
    ax2.set_ylim(min(Leq_list) - 5, max(Leq_list) + 5)  # Aggiungi 4 al valore massimo di Leq_list
    
    # Imposta l'asse X come intervallo che non vada oltre duration_seconds
    ax.set_xticks(np.linspace(0, duration_seconds, int(duration_seconds) + 1))
    
    # Imposta il limite dell'asse X per il grafico rosso
    ax2.set_xlim(0, duration_seconds)  # Limitiamo l'asse X per il grafico rosso
    
    # Aggiungi le linee grigie a trattini per gli xticks e yticks
    ax.grid(True, linestyle='--', color='blue', axis='both', which='both', alpha=0.5, linewidth=0.5)
    ax2.grid(True, linestyle='--', color='red', axis='both', which='both', alpha=0.5, linewidth=0.5)
    
    # Mostra le legende per entrambi i plot
    ax.legend(loc='upper left')
    ax2.legend(loc='upper right')
    
    # Calcola i valori medi
    voiced_confidences_mean = np.mean(voiced_confidences)
    Leq_list_mean = np.mean(Leq_list)
    
    # Crea e visualizza la scritta con i valori medi sotto il grafico
    info_text = f"Media Confidenze Voce: {voiced_confidences_mean:.2f}   Media Leq: {Leq_list_mean:.2f}"
    
    # Rimuovi la Label precedente se esiste
    if label:
        label.destroy()
    
    # Aggiungi la nuova Label con il testo in nero
    label = tk.Label(frame_plot, text=info_text, font=("Helvetica", 15), fg="black")
    label.pack(pady=10)  # Aggiunge un po' di spazio sopra la scritta
    
    # Aggiorna il canvas per riflettere i cambiamenti
    canvas.draw()

def select_file():
    global file_path
    file_path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
    if file_path:
        # Mostra il path del file selezionato nell'area centrale, andando a capo se necessario
        icon_file_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-file.png").resize((40, 40))
        icon_file_photo = ImageTk.PhotoImage(icon_file_image)
        wrapped_path = wrap_text(file_path, max_width=600)
        label_path.config(text=wrapped_path, image=icon_file_photo, compound="left", padx=20)
        label_path.image = icon_file_photo

        # Abilita i bottoni di play e stop
        button_play.config(state="normal")
        button_stop.config(state="normal")

        # Esegui lo script SileroVAD
        global voiced_confidences
        voiced_confidences, Leq_list = sileroVAD.main(file_path)

        draw_plot(voiced_confidences, Leq_list)

def wrap_text(text, max_width):
    """Funzione per andare a capo se il testo supera una certa larghezza."""
    canvas = tk.Canvas(root)
    text_id = canvas.create_text(0, 0, text=text, anchor="nw", font=("Aptos", 18))
    bbox = canvas.bbox(text_id)
    width = bbox[2] - bbox[0]
    if width > max_width:
        words = text.split("/")
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line}/{word}" if current_line else word
            test_id = canvas.create_text(0, 0, text=test_line, anchor="nw", font=("Aptos", 18))
            test_width = canvas.bbox(test_id)[2] - canvas.bbox(test_id)[0]
            if test_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        canvas.destroy()
        return "\n".join(lines)
    else:
        canvas.destroy()
        return text

# Funzioni per i bottoni play e stop
import threading
import pygame
import time

# Variabili globali
playing = False
stop_event = threading.Event()
file_path = "path/to/your/audio/file.mp3"  # Sostituisci con il percorso del tuo file audio

# Funzione per avviare la riproduzione audio
def play_audio():
    global playing, stop_event
    stop_event.clear()
    playing = True
    progress_bar.stop()
    progress_bar.config(value=0)

    # Inizializza pygame mixer per la riproduzione
    pygame.mixer.init()

    # Carica il file audio
    pygame.mixer.music.load(file_path)

    # Imposta la funzione di callback quando il brano è finito
    pygame.mixer.music.set_endevent(pygame.USEREVENT)

    # Avvia la riproduzione
    pygame.mixer.music.play()

    # Avvia un thread separato per il monitoraggio del progresso
    threading.Thread(target=monitor_progress).start()

# Funzione per monitorare il progresso
def monitor_progress():
    global playing
    last_print_time = 0  # Ultimo momento in cui abbiamo stampato il progresso
    i = 0

    while playing:
        if pygame.mixer.music.get_busy():
            # Ottieni il progresso in percentuale (questo è un modo approssimativo per stimare il progresso)
            total_length = pygame.mixer.Sound(file_path).get_length()
            current_position = pygame.mixer.music.get_pos() / 1000  # Posizione in secondi
            progress_bar.config(maximum=total_length, value=current_position)

            if checkbox_var.get():
                # Ottieni il tempo corrente
                current_time = time.time()

                # Stampa solo una volta al secondo
                if current_time - last_print_time >= 1:
                    if last_print_time != 0:
                        if i + 31 <= len(voiced_confidences):
                            buffer = voiced_confidences[i:i+31]
                            buffer_mean = np.mean(buffer)  # Calcola la media del buffer
                            print(f"Media del buffer: {buffer_mean:.2f}")  # Stampa con due decimali
                            quantized = 7 - int(buffer_mean * 8)
                            update_leds(int(quantized))
                            i += 31  # Aggiorna l'indice
                        else:
                            # Calcola la media degli elementi rimanenti
                            buffer = voiced_confidences[i:]
                            buffer_mean = np.mean(buffer)
                            print(f"Media degli elementi rimanenti: {buffer_mean:.2f}")
                            quantized = 7 - int(buffer_mean * 8)
                            update_leds(int(quantized))
                            i = len(voiced_confidences)

                    last_print_time = current_time
        else:
            update_leds(0)
            break


def stop_audio():
    global stop_event
    stop_event.set()
    pygame.mixer.music.stop()

# Configurazione finestra principale
root = tk.Tk()
root.title("Dashboard")
root.geometry("1200x800")

# Barra superiore
frame_top = tk.Frame(root, bg="#3F81D0", height=120)
frame_top.pack(fill=tk.X, side=tk.TOP)

# Posizionamento dell'icona e della scritta
icon_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-logo.png").resize((160, 80))
icon_photo = ImageTk.PhotoImage(icon_image)

frame_title_icon = tk.Frame(frame_top, bg="#3F81D0")
frame_title_icon.place(relx=0.5, rely=0.5, anchor="center")

icon_label = tk.Label(frame_title_icon, image=icon_photo, bg="#3F81D0")
icon_label.pack(side=tk.LEFT, padx=10)

label_title = tk.Label(frame_title_icon, text="Debugging Dashboard", font=("Aptos", 32), bg="#3F81D0", fg="white")
label_title.pack(side=tk.LEFT, padx=10)

# Barra sinistra
frame_left = tk.Frame(root, bg="#144D6F", width=160)
frame_left.pack(fill=tk.Y, side=tk.LEFT)

# Label sopra il pulsante "Seleziona file"
label_choose_track = tk.Label(frame_left, text="Scegli la traccia audio:", font=("Aptos", 16), bg="#144D6F", fg="white")
label_choose_track.pack(pady=(20, 5), padx=20, anchor="w")

# Pulsante Seleziona file con icona
icon_folder_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-folder.png").resize((24, 24))
icon_folder_photo = ImageTk.PhotoImage(icon_folder_image)

frame_file_button = tk.Frame(frame_left, bg="#144D6F")
frame_file_button.pack(pady=5, padx=20, fill=tk.X)

button1 = tk.Button(frame_file_button, text="Seleziona file", font=("Aptos", 16), command=select_file, bg="white", fg="black", relief="flat")
button1.pack(side=tk.LEFT, fill=tk.X, expand=True)

icon_folder_label = tk.Label(frame_file_button, image=icon_folder_photo, bg="#144D6F")
icon_folder_label.pack(side=tk.LEFT, padx=10)

# Label sopra il menu a tendina
label_choose_filter = tk.Label(frame_left, text="Scegli il filtro da applicare:", font=("Aptos", 16), bg="#144D6F", fg="white")
label_choose_filter.pack(pady=(20, 5), padx=20, anchor="w")

# Menu a tendina Seleziona filtro con icona
icon_filter_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-filter.png").resize((24, 24))
icon_filter_photo = ImageTk.PhotoImage(icon_filter_image)

frame_filter_dropdown = tk.Frame(frame_left, bg="#144D6F")
frame_filter_dropdown.pack(pady=5, padx=20, fill=tk.X)

filter_options = ["Nessun filtro", "1", "2", "3", "4", "5", "6", "7"]
filter_var = tk.StringVar(value=filter_options[0])
dropdown = ttk.Combobox(frame_filter_dropdown, textvariable=filter_var, values=filter_options, font=("Aptos", 16), state="readonly")
dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
dropdown.bind("<<ComboboxSelected>>", on_filter_select)

icon_filter_label = tk.Label(frame_filter_dropdown, image=icon_filter_photo, bg="#144D6F")
icon_filter_label.pack(side=tk.LEFT, padx=10)

# Checkbox
checkbox_var = tk.BooleanVar()
checkbox = tk.Checkbutton(frame_left, text="Usa SileroVAD per\n filtraggio adattivo", font=("Aptos", 16), variable=checkbox_var, command=on_checkbox_toggle, bg="#144D6F", fg="white", selectcolor="#144D6F", activebackground="#144D6F")
checkbox.pack(pady=10, padx=20, anchor="w")

# Area centrale
frame_center = tk.Frame(root, bg="white")
frame_center.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

icon_file_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-file.png").resize((40, 40))
icon_file_photo = ImageTk.PhotoImage(icon_file_image)

frame_path_buttons = tk.Frame(frame_center, bg="white")
frame_path_buttons.pack(pady=20)

label_path = tk.Label(frame_path_buttons, text="Nessun file selezionato", font=("Aptos", 18), bg="white", fg="black", image=icon_file_photo, compound="left", padx=20, wraplength=600, justify="left")
label_path.pack(side=tk.LEFT)

# Bottoni Play e Stop
icon_play_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-play.png").resize((40, 40))
icon_play_photo = ImageTk.PhotoImage(icon_play_image)

icon_stop_image = Image.open("/home/mattia/Desktop/dashboard/icons/icon-stop.png").resize((40, 40))
icon_stop_photo = ImageTk.PhotoImage(icon_stop_image)

button_play = tk.Button(frame_path_buttons, image=icon_play_photo, command=play_audio, state="disabled", bg="white", relief="flat")
button_play.pack(side=tk.LEFT, padx=10)

button_stop = tk.Button(frame_path_buttons, image=icon_stop_photo, command=stop_audio, state="disabled", bg="white", relief="flat")
button_stop.pack(side=tk.LEFT, padx=10)

# Barra di avanzamento
progress_bar = ttk.Progressbar(frame_center, orient="horizontal", mode="determinate", length=600)    
progress_bar.pack(pady=20)

# Frame per il plot
frame_plot = tk.Frame(frame_center, bg="white")
frame_plot.pack(fill=tk.BOTH, expand=True, pady=20)

# Creazione del plot
fig = Figure(figsize=(6, 4), dpi=100)
ax = fig.add_subplot(111)
ax.plot(empty_list, marker='o', linestyle='-', color='blue')
ax.set_xlabel("Secondi")
ax.set_ylabel("Confidenza")
ax.legend()

# Creazione di un secondo asse y
ax2 = ax.twinx()  # Asse y condiviso
ax2.plot(empty_list, marker='x', linestyle='--', color='red')  # Usa i tuoi dati
ax2.set_ylabel("Livello Equivalente in db")
ax2.legend(loc='upper right')

# Embed del plot in Tkinter
canvas = FigureCanvasTkAgg(fig, master=frame_plot)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)

# Avvio del loop Tkinter
root.mainloop()
