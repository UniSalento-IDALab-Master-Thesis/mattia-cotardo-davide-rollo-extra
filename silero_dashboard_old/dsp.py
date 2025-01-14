import sys
from pydub import AudioSegment

def main():
    if len(sys.argv) != 3:
        print("Uso: python dsp.py <numero> <file_path>")
        return

    # Ottieni il numero e il percorso del file dagli argomenti della riga di comando
    selected_number = float(sys.argv[1])
    file_path = sys.argv[2]

    try:
        # Carica il file audio
        audio = AudioSegment.from_wav(file_path)

        # Aumenta il volume dell'audio
        audio = audio + (10 * selected_number)

        # Salva l'audio modificato
        output_file_path = f"output_volume_{selected_number}.wav"
        audio.export(output_file_path, format="wav")

        # Stampa i valori e il percorso del file salvato
        print(f"Filtro selezionato: {selected_number}")
        print(f"Nome del file originale: {file_path}")
        #print(f"File salvato con volume aumentato: {output_file_path}")

    except Exception as e:
        print(f"Errore durante l'elaborazione del file: {e}")

if __name__ == "__main__":
    main()
