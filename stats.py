import os
import gradio as gr
import json
import re
import time
import numpy as np
import pandas as pd
import requests

NOTES = sorted(os.listdir("./notes/"))
NUM_NOTES = len(NOTES)
USERS = json.load(open("config/users.json", "r"))

us = list(USERS.keys())
message = ""
for u in us:
    if os.path.exists(f"./storage/{u}.csv"):
        df = pd.read_csv(f"./storage/{u}.csv")
        notes = df['note_name'].unique()
        note_idxs = []
        for note in notes:
            note_idxs.append(NOTES.index(note))
            
        message += f"{u}: {len(note_idxs)}\n"

requests.post("https://ntfy.sh/hiti_annotations",
  data=message.encode(encoding='utf-8'),
  headers={
      "Title": "Text Annotation Update",
      "Priority": "default",
      "Tags": "loudspeaker",
      "Markdown": "yes",
  })

