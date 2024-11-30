import os
import torch
from datasets import load_from_disk, Dataset, Audio
from collections import defaultdict
from speechbrain.pretrained import EncoderClassifier

from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech

import gc
gc.collect()

processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
# Load dataset
dataset = load_from_disk("./common_voice_dataset")
dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
# dataset = dataset.shuffle(seed=42).select(range(int(len(dataset) * 0.15)))

# Extract vocabulary and clean text
text_column = "sentence"
replacements = [
    ('ñ', 'n'), ('ü', 'u'), ('ö', 'o'), ('ä', 'a'), ('á', 'a'),
    ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('à', 'a'),
    ('è', 'e'), ('ì', 'i'), ('ò', 'o'), ('ù', 'u'),
    ('â', 'a'), ('ê', 'e'), ('î', 'i'), ('ô', 'o'), ('û', 'u'),
    ('ã', 'a'), ('õ', 'o'), ('å', 'a'), ('ë', 'e'), ('ç', 'c'),
    ('ś', 's'), ('ş', 's'), ('ț', 't'), ('þ', 't'), ('ł', 'l'),
    ('ř', 'r'), ('ž', 'z'), ('ż', 'z'), ('ß', 'ss'),
    ('ø', 'o'), ('ý', 'y'), ('ı', 'i'), ('ś', 's'),
    ('Š', 'S'), ('ź', 'z'), ('Ż', 'Z'), ('Č', 'C'),
    ('œ', 'oe'), ('æ', 'ae'), ('đ', 'd'),('K','k')
]

import re

def cleanup_text(inputs):
    text = inputs[text_column]  # Usar el nombre correcto de la columna
    # Reemplazar caracteres mapeados
    for src, dst in replacements:
        text = text.replace(src, dst)
    # Eliminar caracteres restantes no alfanuméricos
    text = re.sub(r"[^a-zA-Z0-9.,!? ]", "", text)
    inputs[text_column] = text
    return inputs

dataset = dataset.map(cleanup_text)

# Count speakers and filter dataset
speaker_counts = defaultdict(int)
for speaker_id in dataset["client_id"]:
    speaker_counts[speaker_id] += 1

def select_speaker(speaker_id):
    return 100 <= speaker_counts[speaker_id] <= 400

dataset = dataset.filter(select_speaker, input_columns=["client_id"])

# Load SpeechBrain model for speaker embeddings
spk_model_name = "speechbrain/spkrec-xvect-voxceleb"
device = "cuda" if torch.cuda.is_available() else "cpu"
speaker_model = EncoderClassifier.from_hparams(
    source=spk_model_name,
    run_opts={"device": device},
    savedir="./tmp_model_speechbrain"
)

def create_speaker_embedding(waveform):
    with torch.no_grad():
        speaker_embeddings = speaker_model.encode_batch(torch.tensor(waveform))
        speaker_embeddings = torch.nn.functional.normalize(speaker_embeddings, dim=2)
        return speaker_embeddings.squeeze().cpu().numpy()

def prepare_dataset(example):
    # Cargar los datos de audio
    audio = example["audio"]
    
    # Procesamiento del texto y del audio con el procesador
    processed = processor(
        text=example["sentence"],  # Usamos la columna "sentence" para el texto
        audio_target=audio["array"],
        sampling_rate=audio["sampling_rate"],
        return_attention_mask=False,  # Desactivamos si no es necesario
    )
    
    # Asignar los input_ids del texto procesado
    example["input_ids"] = processed["input_ids"]

    example["labels"] = processed["labels"][0]  # Tomar el primer valor si es lista
    
    # Obtener embeddings del locutor usando SpeechBrain
    example["speaker_embeddings"] = create_speaker_embedding(audio["array"])

    return example


dataset = dataset.map(prepare_dataset, remove_columns=dataset.column_names)

# Save processed dataset
dataset.save_to_disk("./processed_dataset")

