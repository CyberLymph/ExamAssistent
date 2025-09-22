import csv
import os
import pandas as pd # type: ignore
from didactic_critiria import CRITERIA  # <-- nimmt die Kriterien aus deinem Modul

class EvaluationSystem:
    def __init__(self, criteria: dict = None, output_dir="evaluations"):
        """
        criteria: Dict mit {Kriterium: Gewicht}
        Falls None, werden die Kriterien aus didactic_critiria.py geladen.
        """
        if criteria is None:
            if isinstance(CRITERIA, dict):
                self.criteria = CRITERIA
            elif isinstance(CRITERIA, list):
                # Wenn nur eine Liste, automatisch Gewicht 1
                self.criteria = {c: 1 for c in CRITERIA}
            else:
                raise ValueError("CRITERIA muss Dict oder Liste sein.")
        else:
            self.criteria = criteria

        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def evaluate_task(self, task_name: str, results: dict) -> dict:
        """
        results: Dict mit {Kriterium: Status}, Status = "ja", "teilweise", "nein"
        """
        total_points = 0
        max_points = sum(self.criteria.values())
        breakdown = {}

        for crit, weight in self.criteria.items():
            status = results.get(crit, "nein").lower()
            if status == "ja":
                score = weight
            elif status == "teilweise":
                score = weight / 2
            else:
                score = 0
            breakdown[crit] = {"status": status, "points": score}
            total_points += score

        return {
            "task": task_name,
            "score": total_points,
            "max_score": max_points,
            "percent": round((total_points / max_points) * 100, 2),
            "details": breakdown
        }

    def compare_tasks(self, evaluations: list, filename="comparison.csv"):
        """
        evaluations: Liste von Evaluationsdicts (von evaluate_task)
        Erstellt eine Vergleichsmatrix als CSV und Pandas DataFrame
        """
        data = []
        for e in evaluations:
            row = {
                "Aufgabe": e["task"],
                "Gesamtpunkte": e["score"],
                "Max": e["max_score"],
                "Prozent": e["percent"]
            }
            for crit, detail in e["details"].items():
                row[f"{crit} (Punkte)"] = detail["points"]
                row[f"{crit} (Status)"] = detail["status"]
            data.append(row)

        df = pd.DataFrame(data)
        csv_path = os.path.join(self.output_dir, filename)
        df.to_csv(csv_path, index=False, encoding="utf-8")
        return df
