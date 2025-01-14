import io
import os
import numpy as np
import torch
import torchaudio
import matplotlib.pyplot as plt
import argparse
import pyaudio
import warnings
import logging
import math
from maad import spl





'''
APPLICAZIONE DEL MODELLO E CALCOLO DEL LIVELLO EQUIVALENTE
'''


# Suppress warnings
warnings.filterwarnings("ignore")

# Suppress PyTorch logging messages
logging.getLogger('torch').setLevel(logging.WARNING)

# Argument parser for file path
parser = argparse.ArgumentParser(description="Voice Activity Detection")
parser.add_argument('file_path', type=str, help='Path to the audio file')
args = parser.parse_args()

# Load the Silero VAD model
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1 / 32768
    sound = sound.squeeze()
    return sound

                                                                            
SAMPLE_RATE = 16000                                                                             # il sample rate obiettivo. Silero VAD lavora con sample rate da 16000Hz. abbiamo 16mila valori per ogni secondo di audio
CHUNK = 512                                                                                     # un chunk di dati è composto da 512 campioni dell'audio
gai=8                                                                                           # Questo parametro rappresenta un fattore di guadagno (gain) che viene applicato al segnale audio prima del calcolo del Leq.
sens=-32                                                                                        # Questo parametro rappresenta la sensibilità del microfono in dB re 1V/Pa.

# Load the audio file
file_path = args.file_path                                                                      # prendiamo il file dagli argomenti che abbiamo passato
waveform, sample_rate = torchaudio.load(file_path)                                              # dal file carichiamo l'onda e il sample rate
duration_seconds = math.ceil(float(waveform.size(1)) / sample_rate)                             # ricaviamo la durata in secondi dell'audio dividendo il numero di campioni dell'onda, con il numero di campioni per secondo (sample rate)
num_channels = waveform.shape[0]                                                                # Otteniamo il numero di canali dell'audio e stampiamo le informazioni che abbiamo ricavato

# Resample if necessary
if sample_rate != SAMPLE_RATE:                                                                  # se il sample rate dell'audio non coincide con il sample rate a 16000, facciamo il resampling
    resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=SAMPLE_RATE)
    waveform = resampler(waveform)

# Convert to mono if stereo
if waveform.shape[0] > 1:                                                                       # se è un audio stereo, lo convertiamo a mono
    waveform = waveform.mean(dim=0, keepdim=True)

# Print audio file information                                                                  # stampiamo le informazioni sull'audio
print(f"Name: {os.path.basename(file_path)}") 
print(f"Audio Duration: {duration_seconds} seconds")
print(f"Original Sample Rate: {sample_rate} Hz")
print(f"New Sample Rate: {SAMPLE_RATE} Hz")
print(f"Original Number of Channels: {num_channels}")
print(f"New Number of Channels: 1")

# Convert to numpy array and prepare audio data
waveform_numpy = waveform.squeeze().numpy()                                                     # convertiamo l'onda in un array numpy
audio_int16 = (waveform_numpy * 32768).astype(np.int16)                                         # convertiamo l'array numpy in un array di interi
audio_float32 = int2float(audio_int16)                                                          # convertiamo l'array di interi in un array di float
voiced_confidences = []                                                                         # Lista in cui salveremo le predizioni del modello chunk per chunk
Leq_list = []                                                                                   # Lista in cui salveremo i livelli equivalenti per ogni secondo
time_points = []                                                                                # List to store time points of each chunk
num_chunks = len(audio_float32) // CHUNK                                                        # calcoliamo il numero di chunk totale che abbiamo
num_chunks_per_second = math.ceil(num_chunks / duration_seconds)                                # calcoliamo il numero di chunk che abbiamo in un secondo di audio



# Process each audio chunk to compute model prediction
for i in range(num_chunks):                                                                     # per ogni chunk
    start = i * CHUNK                                                                           # prendi il campione di inizio del chunk
    end = start + CHUNK                                                                         # prendi il campione di fine del chunk
    chunk = audio_float32[start:end]                                                            # ritagliati il chunk dall'audio in formato array di float

    # Pad with zeros if necessary
    if len(chunk) < CHUNK:                                                                      # se il chunk che abbiamo appena ritagliato è più breve della lunghezza standard di un chunk (potrebbe accadere all'ultimo chunk)
        chunk = np.pad(chunk, (0, CHUNK - len(chunk)))                                          # fai un padding di zeri per farlo arrivare alla lunghezza standard

    # Get model prediction for current chunk
    new_confidence = model(torch.from_numpy(chunk), SAMPLE_RATE).item()                         # fai la predizione sul singolo chunk
    voiced_confidences.append(new_confidence)                                                   # aggiungi la predizione alla lista
    time_points.append(start / SAMPLE_RATE)


# Process each second of the audio to compute Leq
for i in range(0, len(audio_int16), SAMPLE_RATE):                                               # prendi l'audio (in formato array di interi) e ogni SAMPLE_RATE campioni (ossia ogni secondo)
    group = audio_int16[i:i+SAMPLE_RATE]                                                        # ritagliati il pezzo di audio che ti serve
    norm= group / 32768.0                                                                       # normalizza i suoi valori così sono compresi fra -1 e +1
    w = np.hstack(norm)                                                                         # appiattisce l'array in un singolo array 1d (potrebbe essere inutile)
    Leq_result = spl.wav2leq(w, SAMPLE_RATE, gain=gai, dt=len(w)/SAMPLE_RATE, sensitivity=sens) # Calcola il livello equivalente di pressione sonora (Leq) per il segnale audio presente in w.
    Leq_result = float(Leq_result)                                                              # Converti Leq_result in float
    Leq_list.append(Leq_result)                                                                 # Aggiunge il valore calcolato di Leq_result alla lista Leq_list.








'''
CREAZIONE DEL PLOT SU PDF
'''


# Create a plot
fig, ax1 = plt.subplots(figsize=(20, 6))

# Plot voiced_confidences on the primary y-axis
ax1.plot(time_points, voiced_confidences, lw=2, color='blue', label='Voice Confidence')
ax1.set_xlim(0, len(audio_float32) / SAMPLE_RATE)
ax1.set_ylim(0, 1)
ax1.set_xlabel('Time (seconds)')
ax1.set_ylabel('Voice Confidence', color='blue')
ax1.tick_params(axis='y', labelcolor='blue')
ax1.grid(True)


# Create a secondary y-axis for Leq_list
ax2 = ax1.twinx()
ax2.plot(np.arange(1, len(Leq_list) + 1), Leq_list, lw=2, color='red', label='Leq')
ax2.set_ylim(min(Leq_list) - 5, max(Leq_list) + 5)
ax2.set_ylabel('Leq (dB)', color='red')
ax2.tick_params(axis='y', labelcolor='red')


# Title and legends
ax1.set_title('Voice Activity Detection and Leq over Time')
fig.tight_layout()

# Create 'plot' directory if it doesn't exist
output_dir = 'plot'
os.makedirs(output_dir, exist_ok=True)

# Save the plot as a PDF
base_filename = os.path.splitext(os.path.basename(file_path))[0]
pdf_file_path = os.path.join(output_dir, f"{base_filename}_with_leq.pdf")
fig.savefig(pdf_file_path)
plt.close(fig)

print(f"Created PDF with Leq: {pdf_file_path}")  # Print statement for PDF creation








'''
CREAZIONE/SCRITTURA SUL FILE CSV
'''

# creazione dell'header nel file csv
header = "File name; "
for i in range(1, duration_seconds + 1):
    header += f"second{i}_group; "
header += "groups_mean\n"

csv_file_path = "confidences.csv"

# Write the header only if it's not already present
if not os.path.isfile(csv_file_path) or (header not in open(csv_file_path).read()):
    with open(csv_file_path, 'a') as file:
        file.write(header)

# Open 'confidences.csv' in append mode
with open(csv_file_path, 'a') as file:
    file.write(os.path.basename(file_path) + ";")  # Write audio file name to CSV

# Average predictions per second and append to CSV
for i in range(0, len(voiced_confidences), num_chunks_per_second):
    group = voiced_confidences[i:i + num_chunks_per_second]
    mean_chunk = np.mean(group)
    with open(csv_file_path, 'a') as file:
        file.write(f"{mean_chunk:.5f};")  # Write the mean_chunk with 5 decimal places

# Calculate overall mean confidence and append to CSV
mean_confidence = np.mean(voiced_confidences)
print(f"Mean confidence: {mean_confidence:.5f}")
with open(csv_file_path, 'a') as file:
    file.write(f"{mean_confidence:.5f}\n")  # Write the mean confidence with 5 decimal places

# Place a blank space
with open(csv_file_path, 'a') as file:
    file.write(";")

# Average leq per second
for i in range(0, len(Leq_list)):
    with open(csv_file_path, 'a') as file:
        file.write(f"{Leq_list[i]:.1f};")  # Write the Leq value with 5 decimal places

# Calculate overall mean LEQ and append to CSV
mean_leq = np.mean(Leq_list)
print(f"Mean LEQ: {mean_leq:.1f}")
with open(csv_file_path, 'a') as file:
    file.write(f"{mean_leq:.1f}\n")  # Write the mean LEQ with 5 decimal places

print("Updated confidences.csv")  # Print statement for CSV update




print("\n")
