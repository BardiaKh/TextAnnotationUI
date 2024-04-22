import os
import gradio as gr
import json
import re
import time
import numpy as np
import pandas as pd

if __name__ == '__main__':
    NOTES = sorted(os.listdir("./notes/"))
    HINTS = open("config/hints.md", "r").read()
    NUM_NOTES = len(NOTES)
    QUESTIONARE = json.load(open("config/questions.json", "r"))
    USERS = json.load(open("config/users.json", "r"))
    
    #---
    
    def fetch_report(idx):
        global NOTES
        with open("./notes/"+NOTES[idx], "r") as f:
            return f.read()
    
    def auth(username, password):
        if username in USERS and USERS[username] == password:
            return True
        return False
    
    def setup_screen(stats, request: gr.Request):
        global NOTES
        global NUM_NOTES
        global QUESTIONARE
        username = request.username
        stats['username'] = username
    
        if os.path.exists(f"./storage/{username}.csv"):
            df = pd.read_csv(f"./storage/{username}.csv")
    
            last_filled_index = df.last_valid_index()
            if last_filled_index is not None:
                last_note_name = df.loc[last_filled_index, 'note_name']
                current_report_idx = NOTES.index(last_note_name)
                stats['responses'] = {}
                for note_name in df['note_name'].unique():
                    note_df = df[df['note_name'] == note_name]
                    values = []
                    for q in QUESTIONARE:
                        if q["name"] in note_df.columns:
                            value = note_df[q["name"]].values[0]
                            if pd.isna(value):
                                value = q["default"]
                            values.append(value)
                        else:
                            values.append(q["default"])
    
                    stats['responses'][note_name] = values
            else:
                current_report_idx = 0
                stats['responses'] = {}
        else:
            current_report_idx = 0
            stats['responses'] = {}
    
        current_note_name = NOTES[current_report_idx].split("/")[-1]
        stats_markdown = f"Welcome **{username.title()}**!\n\nCurrent file: **{current_note_name}**\n\nProgress: **{current_report_idx + 1}/{NUM_NOTES}**\n\nLast updated: **" + time.strftime("%d/%m/%Y %H:%M:%S") + "**"
        
        stats['current_report_idx'] = current_report_idx
        
        report_text = fetch_report(current_report_idx)
        updated_stats_box = update_progress(stats_markdown, current_report_idx)
        note_name = NOTES[current_report_idx]
        responses = stats['responses']
        return report_text, updated_stats_box, stats, current_report_idx + 1, *responses.get(note_name, [q["default"] for q in QUESTIONARE])
    
    def update_progress(stats_box, current_report_idx):
        global NOTES
        global NUM_NOTES
        current_note_name = NOTES[current_report_idx].split("/")[-1]
        stats_box = re.sub(r"Progress: \*\*\d+/\d+\*\*", f"Progress: **{current_report_idx+1}/{NUM_NOTES}**", stats_box)
        stats_box = re.sub(r"Current file: \*\*.*\*\*", f"Current file: **{current_note_name}**", stats_box)
        stats_box = re.sub(r"Last updated: \*\*\d+/\d+/\d+ \d+:\d+:\d+\*\*", "Last updated: **" + time.strftime("%d/%m/%Y %H:%M:%S") + "**", stats_box)
        return stats_box
    
    #---
    
    def go_to_report(stats, stats_box, increment=None, target_idx=None, *response_vars):
        global NUM_NOTES
        current_report_idx = stats["current_report_idx"]
        stats["responses"] = update_responses_for_note(stats, *response_vars)
    
        if target_idx is not None:
            current_report_idx = max(0, min(target_idx, NUM_NOTES - 1))
        else:
            current_report_idx = max(0, min(current_report_idx + increment, NUM_NOTES - 1))
            
        stats["current_report_idx"] = current_report_idx
        return fetch_report(current_report_idx), update_progress(stats_box, current_report_idx), stats, current_report_idx+1, *get_responses_for_note(stats)
    
    def next_report(stats, stats_box, *response_vars):
        return go_to_report(stats, stats_box, 1, None, *response_vars)
    
    def prev_report(stats, stats_box, *response_vars):
        return go_to_report(stats, stats_box, -1, None, *response_vars)
    
    def jump_to_report(stats, stats_box, target_idx, *response_vars):
        global NUM_NOTES
        if target_idx is None:
            target_idx = 1
        target_idx = max(0, min(target_idx-1, NUM_NOTES))
        return go_to_report(stats, stats_box, None, target_idx, *response_vars)
    
    def get_responses_for_note(stats):
        global NOTES
        current_report_idx = stats["current_report_idx"]
        note_name = NOTES[current_report_idx]
        responses = stats["responses"]
        return responses.get(note_name, [q["default"] for q in QUESTIONARE])
    
    def update_responses_for_note(stats, *response_vars):
        global NOTES
        current_report_idx = stats["current_report_idx"]
        note_name = NOTES[current_report_idx]
        responses = stats["responses"]
        responses[note_name] = [*response_vars]
        export_responses(stats)
        return responses
    
    def export_responses(stats):
        data = []
        for note_name, responses in stats["responses"].items():
            data.append({
                "note_name": note_name,
                **dict(zip([q["name"] for q in QUESTIONARE], responses))
            })
    
        new_df = pd.DataFrame(data)
        file_path = f"./storage/{stats['username']}.csv"
    
        if os.path.exists(file_path):
            existing_df = pd.read_csv(file_path)
            merged_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['note_name'], keep='last')
            merged_df = merged_df.sort_values(by='note_name')
            merged_df.to_csv(file_path, index=False)
        else:
            new_df = new_df.sort_values(by='note_name')
            new_df.to_csv(file_path, index=False)
    
        return None
    
    #---
    
    with gr.Blocks() as demo:
        stats = gr.State(value={"username":None, "current_report_idx": 0, "responses": {}})
        with gr.Row():
            with gr.Column(scale=4):
                report = gr.TextArea(value=fetch_report(0), label="Note:", interactive=False, show_label=True, scale=2)
            with gr.Column(scale=2):
                stats_box = gr.Markdown(value= "")
                with gr.Row():
                    jump_to = gr.Slider(minimum=1, maximum=NUM_NOTES, step=1, value=1, label="Jump to:", interactive=True, scale=1)
                with gr.Row():
                    save_btn = gr.Button("💾", variant="primary", size="lg", min_width=10, scale=1)
                with gr.Row():
                    prev_btn = gr.Button("⬅️", variant="primary", size="lg", min_width=10, scale=1)
                    next_btn = gr.Button("➡️", variant="primary", size="lg", min_width=10, scale=1)
        
        with gr.Row():
            response_vars = []
            for question in QUESTIONARE:
                if question['type'] == "select":
                    response_vars.append(gr.Radio(choices=question['options'], label=question['name'], value=question['default'], type="value", interactive=True, scale=1))
    
                elif question['type'] == "text":
                    response_vars.append(gr.Textbox(lines=1, label=question['name'], value=question['default'], type="text", interactive=True, scale=1))
    
        with gr.Row():
            hints = gr.Markdown(value=HINTS)
    
        prev_btn.click(fn=prev_report, inputs=[stats, stats_box, *response_vars], outputs=[report, stats_box, stats, jump_to, *response_vars])
        next_btn.click(fn=next_report, inputs=[stats, stats_box, *response_vars], outputs=[report, stats_box, stats, jump_to, *response_vars])
        save_btn.click(fn=jump_to_report, inputs=[stats, stats_box, jump_to, *response_vars], outputs=[report, stats_box, stats, jump_to, *response_vars])
        jump_to.change(fn=jump_to_report, inputs=[stats, stats_box, jump_to, *response_vars], outputs=[report, stats_box, stats, jump_to, *response_vars])
        demo.load(setup_screen, inputs=[stats], outputs=[report, stats_box, stats, jump_to, *response_vars])
    
    demo.launch(
        auth=auth,
        inline=False,
        share=True,
        debug=True,
        server_name="0.0.0.0",
        server_port=1900,
        show_api=False,
        auth_message="Please enter your username and password to continue"
    )


##########################################################################
# This file was converted using nb2py: https://github.com/BardiaKh/nb2py #
##########################################################################
