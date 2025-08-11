# import pickle
# import json
# import numpy as np
# import pandas as pd

# # Load model + encoder
# with open(r"E:\Mehak Docs\path lab app\chatbot\server\model_weighted.pkl", "rb") as f:
#     model = pickle.load(f)

# with open(r"E:\Mehak Docs\path lab app\chatbot\server\columns.json", "r") as f:
#     columns = json.load(f)

# with open(r"E:\Mehak Docs\path lab app\chatbot\server\le_disease.pkl", "rb") as f:
#     le = pickle.load(f)

# # Load symptom severity, descriptions, and precautions
# df_severity = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\Symptom-severity.csv")
# df_description = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\symptom_Description.csv")
# df_precaution = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\symptom_precaution.csv")

# # Build helper dictionaries
# df_severity["Symptom"] = df_severity["Symptom"].str.strip().str.lower().str.replace(" ", "_")
# severity_dict = dict(zip(df_severity["Symptom"], df_severity["weight"]))

# desc_dict = dict(zip(df_description["Disease"].str.strip().str.lower(), df_description["Description"]))
# precaution_dict = df_precaution.set_index("Disease").T.to_dict('list')

# # Default severity for unknown symptoms
# DEFAULT_SEVERITY = 1

# def predict_disease(symptom_input):
#     try:
#         print(f"Received symptoms: {symptom_input}")
#         # Step 0: Validate input
#         # Step 1: Preprocess user input
#         symptoms = [s.strip().lower().replace(" ", "_") for s in symptom_input.split(",") if s.strip()]
#         input_vector = [severity_dict.get(col, DEFAULT_SEVERITY) if col in symptoms else 0 for col in columns]
#         print("Input vector sum:", sum(input_vector))
#         print("Matched symptoms:", [col for col in columns if col in symptoms])

#         # Step 2: Predict the disease
#         probs = model.predict_proba([input_vector])[0]
#         top_indices = np.argsort(probs)[::-1][:3]
#         top_diseases = [(le.inverse_transform([i])[0], round(probs[i]*100, 2)) for i in top_indices]

#         # Step 3: Main prediction
#         predicted_disease = top_diseases[0][0]
#         confidence = top_diseases[0][1]

#         # Step 4: Lookup description + precautions
#         description = desc_dict.get(predicted_disease.lower(), "No description available.")
#         precautions = precaution_dict.get(predicted_disease, ["No precautions available."])

#         # Step 5: Format response
#         response = f"🔮 Based on your symptoms, you may have: {predicted_disease} \n (Confidence: {confidence}%)\n\n"
#         response += f"📘 About the disease {description}\n\n"
#         response += f"🛡️ Recommended Precautions:\n"
#         for i, p in enumerate(precautions):
#             if isinstance(p, str) and p.strip():
#                 response += f"{i+1}. {p}\n"

#         # Step 6: Show top 3 predictions
#         response += "\n📊 Other Possible Conditions:\n"
#         for disease, conf in top_diseases[1:]:
#             response += f"- {disease} ({conf}%)\n"

#         response += "\n👉 Please consult a licensed medical professional for a proper diagnosis."

#         return response.replace("\n", "<br>")

#     except Exception as e:
#         return f"⚠️ Something went wrong while processing your symptoms: {str(e)}"
import pickle
import json
import numpy as np
import pandas as pd
import re
import difflib

# ========= Load model + artifacts =========
with open(r"E:\Mehak Docs\path lab app\chatbot\server\model_weighted.pkl", "rb") as f:
    model = pickle.load(f)

with open(r"E:\Mehak Docs\path lab app\chatbot\server\columns.json", "r") as f:
    columns = json.load(f)

with open(r"E:\Mehak Docs\path lab app\chatbot\server\le_disease.pkl", "rb") as f:
    le = pickle.load(f)

# ========= Load data for severity/desc/precautions =========
df_severity = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\Symptom-severity.csv")
df_description = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\symptom_Description.csv")
df_precaution = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\symptom_precaution.csv")

# ========= Normalize artifact keys =========
# Normalize columns to lowercase underscore format for matching
columns = [c.strip().lower().replace(" ", "_") for c in columns]

# Severity mapping
df_severity["Symptom"] = df_severity["Symptom"].str.strip().str.lower().str.replace(" ", "_")
severity_dict = dict(zip(df_severity["Symptom"], df_severity["weight"]))

# Disease descriptions (lowercased keys)
desc_dict = dict(zip(df_description["Disease"].str.strip().str.lower(), df_description["Description"]))

# Precautions: map disease(lower) -> list
_prec = df_precaution.copy()
_prec["Disease_lc"] = _prec["Disease"].str.strip().str.lower()
precaution_dict = _prec.set_index("Disease_lc").drop(columns=["Disease"]).T.to_dict("list")

DEFAULT_SEVERITY = 1

# ========= Text normalization / symptom extraction =========

# Basic stopword list (extend if needed)
STOPWORDS = {
    "i","me","my","mine","myself","we","our","ours","ourselves","you","your","yours","yourself","yourselves",
    "he","him","his","himself","she","her","hers","herself","they","them","their","theirs","themselves",
    "am","is","are","was","were","be","been","being","have","has","had","do","does","did","doing",
    "a","an","the","and","or","but","so","because","that","which","who","whom","of","to","in","on","for",
    "with","at","by","from","as","about","into","over","after","before","up","down","out","off","again",
    "further","then","once","very","more","most","some","such","no","nor","not","only","own","same",
    "just","also","too","than","ever","still","yet","please","plz"
}

# Common synonyms / paraphrases -> canonical symptom
SYNONYMS = {
    "tiredness": "fatigue",
    "tired": "fatigue",
    "exhaustion": "fatigue",
    "runny nose": "runny_nose",
    "blocked nose": "congestion",
    "stuffy nose": "congestion",
    "sore throat": "sore_throat",
    "throat pain": "sore_throat",
    "stomach ache": "stomach_pain",
    "tummy pain": "stomach_pain",
    "belly pain": "abdominal_pain",
    "loose motion": "diarrhoea",
    "loose motions": "diarrhoea",
    "high temperature": "high_fever",
    "feverish": "fever",
    "body ache": "body_pain",
    "body aches": "body_pain",
    "shortness of breath": "breathlessness",
    "breath short": "breathlessness",
    "itchy": "itching",
    "coughing": "cough",
    "sneezes": "continuous_sneezing",
    "sneezing": "continuous_sneezing",
}

# Precompute patterns for multi-word symptoms
SYM_VARIANTS = [(c, re.compile(rf"\b{re.escape(c.replace('_', ' '))}\b")) for c in columns]
SYN_PHRASES = sorted([k for k in SYNONYMS if " " in k], key=len, reverse=True)

def normalize_text(txt: str) -> str:
    txt = txt.lower()
    txt = txt.replace("-", " ").replace("/", " ")
    # phrase-level synonym replacements first
    for phrase in SYN_PHRASES:
        txt = re.sub(rf"\b{re.escape(phrase)}\b", SYNONYMS[phrase].replace("_", " "), txt)
    # keep letters, commas, spaces
    txt = re.sub(r"[^a-z,\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def tokenize_clean(txt: str):
    return [w for w in txt.split() if w and w not in STOPWORDS]

def extract_symptoms_freeform(user_text: str):
    """
    Returns a list of canonical symptom column names.
    Works for comma-separated inputs and free-form sentences.
    Also handles synonyms and small typos (fuzzy).
    """
    msg_norm = normalize_text(user_text)

    # 1) Comma-separated quick path
    tokens_csv = [t.strip() for t in msg_norm.split(",") if t.strip()]
    direct_cols = []
    for tok in tokens_csv:
        cand = tok.replace(" ", "_")
        # map single-word synonyms
        if cand in SYNONYMS:
            cand = SYNONYMS[cand]
        if cand in columns:
            direct_cols.append(cand)
    if direct_cols:
        # dedupe, preserve order
        seen = set()
        ordered = []
        for c in direct_cols:
            if c not in seen:
                seen.add(c)
                ordered.append(c)
        return ordered

    matched = set()

    # 2) Multi-word scan against all known symptoms
    for col, pattern in SYM_VARIANTS:
        if pattern.search(msg_norm):
            matched.add(col)

    # 3) Token-level matches + single-word synonyms
    words = tokenize_clean(msg_norm)
    for w in words:
        if w in SYNONYMS:
            w = SYNONYMS[w]
        w_col = w.replace(" ", "_")
        if w_col in columns:
            matched.add(w_col)

    # 4) Fuzzy match (for tokens not matched), length >= 4
    col_lookup_strings = columns + [c.replace("_", " ") for c in columns]
    for w in words:
        w_col = w.replace(" ", "_")
        if w_col in columns:
            continue
        if len(w) < 4:
            continue
        best = difflib.get_close_matches(w, col_lookup_strings, n=1, cutoff=0.88)
        if best:
            b = best[0].replace(" ", "_")
            if b in columns:
                matched.add(b)

    return list(matched)

# ========= Main predictor =========

def predict_disease(symptom_input):
    try:
        print(f"Received symptoms: {symptom_input}")

        # Robust extraction (handles commas, sentences, synonyms, typos)
        symptoms = extract_symptoms_freeform(symptom_input)
        print("Matched symptoms:", symptoms)

        # Build weighted input vector
        input_vector = [
            severity_dict.get(col, DEFAULT_SEVERITY) if col in symptoms else 0
            for col in columns
        ]
        print("Input vector sum:", sum(input_vector))

        if sum(input_vector) == 0:
            return ("⚠️ I couldn't match any known symptoms. "
                    "Try simple terms like: 'itching, fever, cough' "
                    "or short phrases like 'sore throat, runny nose'.").replace("\n", "<br>")

        # Predict and build top-3
        probs = model.predict_proba([input_vector])[0]
        top_indices = np.argsort(probs)[::-1][:3]
        top_diseases = [(le.inverse_transform([i])[0], round(float(probs[i]) * 100, 2)) for i in top_indices]

        predicted_disease = top_diseases[0][0]
        confidence = top_diseases[0][1]

        # Lookups (lower for desc/prec keys)
        key_lc = predicted_disease.lower()
        description = desc_dict.get(key_lc, "No description available.")
        precautions = precaution_dict.get(key_lc, ["No precautions available."])

        # Format response
        response = (
            f"🔮 Based on your symptoms, you may have: {predicted_disease} \n (Confidence: {confidence}%)\n\n"
            f"📘 About the disease {description}\n\n"
            f"🛡️ Recommended Precautions:\n"
        )
        if isinstance(precautions, list):
            for i, p in enumerate(precautions):
                if isinstance(p, str) and p.strip():
                    response += f"{i+1}. {p}\n"
        else:
            response += f"1. {precautions}\n"

        response += "\n📊 Other Possible Conditions:\n"
        for disease, conf in top_diseases[1:]:
            response += f"- {disease} ({conf}%)\n"

        response += "\n👉 Please consult a licensed medical professional for a proper diagnosis."
        return response.replace("\n", "<br>")

    except Exception as e:
        return f"⚠️ Something went wrong while processing your symptoms: {str(e)}"
