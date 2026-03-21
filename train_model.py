# train_model.py
import joblib
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import os

# Model papkasini yaratish
os.makedirs("models", exist_ok=True)

# Namuna ma'lumotlar (bu yerda sizning real ma'lumotlaringiz bo'lishi kerak)
data = [
    ("SELECT * FROM users WHERE id = 1", "normal"),
    ("DROP TABLE users; --", "sql_error"),
    ("' OR '1'='1", "suspicious"),
    ("UNION SELECT * FROM passwords", "sql_error"),
    ("<script>alert('xss')</script>", "suspicious"),
    ("Hello world", "normal"),
    ("admin' --", "sql_error"),
    ("1; DROP TABLE users", "sql_error"),
]

df = pd.DataFrame(data, columns=["text", "label"])

# Model yaratish
vectorizer = TfidfVectorizer(max_features=1000)
classifier = LogisticRegression(max_iter=1000)

pipeline = Pipeline([
    ('tfidf', vectorizer),
    ('clf', classifier)
])

# Modelni o'qitish
X = df["text"]
y = df["label"]
pipeline.fit(X, y)

# Modelni saqlash
joblib.dump(pipeline, "models/sql_error_model.joblib")
print("Model muvaffaqiyatli saqlandi!")