import csv
import os

class Checklist:
    def __init__(self, output_dir="checklists"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def save_markdown(self, items: list, filename="checklist.md"):
        """
        Speichert eine Checkliste als Markdown-Datei.
        items: Liste von Strings (Kriterien oder Prüfpunkte)
        """
        md_path = os.path.join(self.output_dir, filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Checkliste für Klausuraufgaben\n\n")
            for i, item in enumerate(items, 1):
                f.write(f"- [ ] {item}\n")
        return md_path

    def save_csv(self, items: list, filename="checklist.csv"):
        """
        Speichert eine Checkliste als CSV-Datei.
        """
        csv_path = os.path.join(self.output_dir, filename)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Nr.", "Kriterium", "Erfüllt (Ja/Nein)"])
            for i, item in enumerate(items, 1):
                writer.writerow([i, item, ""])
        return csv_path



from automation import Automation
from checklist import Checklist
from didactic_critiria import CRITERIA  # falls dort deine Kriterien stehen

# Automatisierung
auto = Automation()
report = auto.run_quality_check(
    tasks=["Aufgabe 1: Definiere KI.", "Aufgabe 2: Erkläre maschinelles Lernen."],
    criteria=CRITERIA
)

# Checklisten
check = Checklist()
check.save_markdown(CRITERIA, "didactic_checklist.md")
check.save_csv(CRITERIA, "didactic_checklist.csv")
