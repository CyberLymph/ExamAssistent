import os
import json
from datetime import datetime
from fastapi_app.api import evaluate_task  # Beispiel: deine API für LLM-Analyse

class Automation:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def run_quality_check(self, tasks: list, criteria: list) -> dict:
        """
        Führt eine Qualitätsprüfung für eine Liste von Klausuraufgaben durch.
        tasks: Liste von Strings (Klausuraufgaben)
        criteria: Liste von Kriterien (z. B. aus didactic_critiria.py)
        """
        results = []
        for task in tasks:
            evaluation = evaluate_task(task, criteria)  # <- Anbindung ans LLM
            results.append({
                "task": task,
                "evaluation": evaluation
            })

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(tasks),
            "results": results
        }

        # Speichern als JSON
        json_path = os.path.join(self.output_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return report
