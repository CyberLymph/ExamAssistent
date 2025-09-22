import os
import json
import openai

class SemanticDeviationDetector:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def analyze_and_save(self, student_answer: str, model_solution: str,
                         chat_id: str, run_id: str, base_dir="analysis"):
        """
        Nutzt GPT für Abweichungsanalyse und speichert notes.md
        """
        outdir = os.path.join(base_dir, str(chat_id), str(run_id))
        os.makedirs(outdir, exist_ok=True)

        prompt = f"""
        Vergleiche die folgende Studenten-Antwort mit der Musterlösung.
        Beschreibe die Übereinstimmungen und Abweichungen.

        Musterlösung:
        {model_solution}

        Studenten-Antwort:
        {student_answer}
        """
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        analysis = response.choices[0].message["content"]

        # notes.md speichern
        notes_path = os.path.join(outdir, "notes.md")
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write("# Abweichungsanalyse\n\n")
            f.write(analysis)

        return {"notes_file": notes_path, "analysis": analysis}
