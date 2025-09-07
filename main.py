import re
import random
import nltk
import docx2txt
import PyPDF2
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

# -------------------- NLTK SETUP --------------------
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)

# -------------------- FILE READER --------------------
def read_file(file_path):
    """Read text, Word, or PDF file content as plain text."""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif file_path.endswith(".docx"):
        return docx2txt.process(file_path)

    elif file_path.endswith(".pdf"):
        text = ""
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        return text

    else:
        raise ValueError("Unsupported file format. Use .txt, .docx, or .pdf")

# -------------------- SANITIZER --------------------
def sanitize_text(text):
    replacements = {
        "’": "'",
        "‘": "'",
        "—": "-",
        "…": "...",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# -------------------- KEYWORD EXTRACTION --------------------
def extract_keywords(text, num_keywords=50):
    sentences = sent_tokenize(text)
    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(sentences)
    indices = X.sum(axis=0).A1.argsort()[::-1]
    keywords = [vectorizer.get_feature_names_out()[i] for i in indices]
    return keywords[:num_keywords]

# -------------------- CLOZE GENERATOR --------------------
def generate_cloze_questions(text, num_questions=5):
    sentences = sent_tokenize(text)
    cloze_questions = []

    for s in sentences:
        s = sanitize_text(s)
        if len(s.split()) < 4:  # skip too short sentences
            continue
        words = s.split()
        keyword = random.choice(words)
        if keyword.isalpha() and len(keyword) > 3:
            question = s.replace(keyword, "_____")
            cloze_questions.append({"question": question, "answer": keyword})
        if len(cloze_questions) >= num_questions:
            break

    return cloze_questions

# -------------------- MCQ GENERATOR --------------------
def generate_mcq_questions(text, num_questions=5):
    sentences = sent_tokenize(text)
    keywords = extract_keywords(text, num_keywords=50)
    mcq_questions = []
    attempts = 0
    max_attempts = num_questions * 3

    while len(mcq_questions) < num_questions and attempts < max_attempts:
        s = random.choice(sentences)
        s = sanitize_text(s)
        words = s.split()
        candidates = [w for w in words if w.isalpha() and w.lower() in keywords]
        if candidates:
            answer = random.choice(candidates)
            question = s.replace(answer, "_____")
            distractors = random.sample(
                [w for w in keywords if w.lower() != answer.lower()],
                min(3, len(keywords) - 1),
            )
            options = distractors + [answer]
            random.shuffle(options)
            mcq_questions.append({"question": question, "options": options, "answer": answer})
        attempts += 1

    return mcq_questions

# -------------------- MAIN GENERATOR --------------------
def generate_questions(file_path, num_questions=5):
    text = read_file(file_path)
    cloze = generate_cloze_questions(text, num_questions)
    mcq = generate_mcq_questions(text, num_questions)
    return cloze, mcq

# -------------------- EXPORTABLE FUNCTION --------------------
def generate_quiz(file_path, num_questions=5):
    """Generate both Cloze and MCQ quiz from the given file."""
    cloze_questions, mcq_questions = generate_questions(file_path, num_questions)
    return {
        "cloze": cloze_questions,
        "mcq": mcq_questions
    }
