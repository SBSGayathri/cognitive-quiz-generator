import re
import random
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
import docx2txt
import PyPDF2
import nltk

# Ensure punkt and punkt_tab are available
nltk.download("punkt")
nltk.download("punkt_tab")

def load_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def load_text_from_docx(file_path):
    return docx2txt.process(file_path)

def load_text_from_pdf(file_path):
    pdf_reader = PyPDF2.PdfReader(file_path)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + " "
    return text

def preprocess_sentences(text):
    sents = sent_tokenize(text)
    random.shuffle(sents)
    return [s.strip() for s in sents if 25 < len(s.strip()) < 200]

def extract_keywords(text, top_n=30):
    vec = TfidfVectorizer(ngram_range=(1,2), stop_words="english", max_features=200)
    tfidf = vec.fit_transform([text])
    feature_names = vec.get_feature_names_out()
    scores = tfidf.toarray().flatten()
    idx = scores.argsort()[::-1]
    keywords = [feature_names[i] for i in idx if len(feature_names[i]) > 2]
    random.shuffle(keywords)
    return keywords[:top_n]

def make_cloze(sentence, keyword):
    pat = re.compile(r"\b" + re.escape(keyword) + r"\b", flags=re.I)
    if pat.search(sentence):
        return pat.sub("_____", sentence, count=1)
    return None

def generate_mcq(sentence, keyword, keywords_pool, num_options=4):
    question = f"In the context: '{sentence}', what does '{keyword}' refer to?"
    distractors = [kw for kw in keywords_pool if kw.lower() != keyword.lower() and len(kw) > 2]
    random.shuffle(distractors)
    options = distractors[:num_options-1] + [keyword]
    random.shuffle(options)
    return {"question": question, "answer": keyword, "options": options}

def generate_quiz(file_path, num_questions=5):
    ext = file_path.split(".")[-1].lower()
    if ext == "txt":
        text = load_text_from_txt(file_path)
    elif ext == "docx":
        text = load_text_from_docx(file_path)
    elif ext == "pdf":
        text = load_text_from_pdf(file_path)
    else:
        return {"cloze": [], "mcq": []}

    sentences = preprocess_sentences(text)
    keywords = extract_keywords(text, top_n=num_questions*3)

    quiz = {"cloze": [], "mcq": []}

    # Cloze questions
    used_sentences = set()
    for kw in keywords:
        random.shuffle(sentences)
        for s in sentences:
            if kw.lower() in s.lower() and s not in used_sentences:
                cloze = make_cloze(s, kw)
                if cloze:
                    quiz["cloze"].append({"question": cloze, "answer": kw})
                    used_sentences.add(s)
                    break
        if len(quiz["cloze"]) >= num_questions:
            break

    # MCQs
    for kw in keywords:
        random.shuffle(sentences)
        s = next((s for s in sentences if kw.lower() in s.lower()), sentences[0])
        quiz["mcq"].append(generate_mcq(s, kw, keywords))
        if len(quiz["mcq"]) >= num_questions:
            break

    return quiz
