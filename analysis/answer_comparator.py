import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer, util

class AnswerComparator:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", base_dir="analysis"):
        self.model = SentenceTransformer(model_name)
        self.base_dir = base_dir

    def analyze_and_save(self, student_answer: str, model_solution: str, chat_id: str, run_id: str):
        outdir = os.path.join(self.base_dir, str(chat_id), str(run_id))
        os.makedirs(outdir, exist_ok=True)

        # Embeddings + Score
        embeddings = self.model.encode([student_answer, model_solution])
        cosine_sim = util.cos_sim(embeddings[0], embeddings[1])
        score = float(cosine_sim.item())

        # similarity.json speichern
        sim_path = os.path.join(outdir, "similarity.json")
        with open(sim_path, "w", encoding="utf-8") as f:
            json.dump({
                "student_answer": student_answer,
                "model_solution": model_solution,
                "similarity_score": score
            }, f, indent=2, ensure_ascii=False)

        # Embeddings speichern
        emb_path = os.path.join(outdir, "embedding.npy")
        np.save(emb_path, embeddings)

        return {"similarity_score": score, "similarity_json": sim_path, "embedding_file": emb_path}
