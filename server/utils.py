import pickle
import json
import numpy as np
import pandas as pd

# Load model + encoder
with open(r"E:\Mehak Docs\path lab app\chatbot\server\model_weighted.pkl", "rb") as f:
    model = pickle.load(f)

with open(r"E:\Mehak Docs\path lab app\chatbot\server\columns.json", "r") as f:
    columns = json.load(f)

with open(r"E:\Mehak Docs\path lab app\chatbot\server\le_disease.pkl", "rb") as f:
    le = pickle.load(f)

# Load symptom severity, descriptions, and precautions
df_severity = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\Symptom-severity.csv")
df_description = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\symptom_Description.csv")
df_precaution = pd.read_csv(r"E:\Mehak Docs\path lab app\chatbot\disease prediction\symptom_precaution.csv")

# Build helper dictionaries
df_severity["Symptom"] = df_severity["Symptom"].str.strip().str.lower().str.replace(" ", "_")
severity_dict = dict(zip(df_severity["Symptom"], df_severity["weight"]))

desc_dict = dict(zip(df_description["Disease"].str.strip().str.lower(), df_description["Description"]))
precaution_dict = df_precaution.set_index("Disease").T.to_dict('list')

# Default severity for unknown symptoms
DEFAULT_SEVERITY = 1

def predict_disease(symptom_input):
    try:
        print(f"Received symptoms: {symptom_input}")
        # Step 0: Validate input
        # Step 1: Preprocess user input
        symptoms = [s.strip().lower().replace(" ", "_") for s in symptom_input.split(",") if s.strip()]
        input_vector = [severity_dict.get(col, DEFAULT_SEVERITY) if col in symptoms else 0 for col in columns]
        print("Input vector sum:", sum(input_vector))
        print("Matched symptoms:", [col for col in columns if col in symptoms])

        # Step 2: Predict the disease
        probs = model.predict_proba([input_vector])[0]
        top_indices = np.argsort(probs)[::-1][:3]
        top_diseases = [(le.inverse_transform([i])[0], round(probs[i]*100, 2)) for i in top_indices]

        # Step 3: Main prediction
        predicted_disease = top_diseases[0][0]
        confidence = top_diseases[0][1]

        # Step 4: Lookup description + precautions
        description = desc_dict.get(predicted_disease.lower(), "No description available.")
        precautions = precaution_dict.get(predicted_disease, ["No precautions available."])

        # Step 5: Format response
        response = f"🔮 Based on your symptoms, you may have: {predicted_disease} \n (Confidence: {confidence}%)\n\n"
        response += f"📘 About the disease {description}\n\n"
        response += f"🛡️ Recommended Precautions:\n"
        for i, p in enumerate(precautions):
            if isinstance(p, str) and p.strip():
                response += f"{i+1}. {p}\n"

        # Step 6: Show top 3 predictions
        response += "\n📊 Other Possible Conditions:\n"
        for disease, conf in top_diseases[1:]:
            response += f"- {disease} ({conf}%)\n"

        response += "\n👉 Please consult a licensed medical professional for a proper diagnosis."

        return response.replace("\n", "<br>")

    except Exception as e:
        return f"⚠️ Something went wrong while processing your symptoms: {str(e)}"
