import re
import random
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
import docx2txt
import PyPDF2
import nltk

# Ensure punkt is available
nltk.download("punkt")


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
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", max_features=200)
    tfidf = vec.fit_transform([text])
    feature_names = vec.get_feature_names_out()
    scores = tfidf.toarray().flatten()
    idx = scores.argsort()[::-1]
    keywords = [feature_names[i] for i in idx if len(feature_names[i]) > 2]
    random.shuffle(keywords)
    return keywords[:top_n]


def make_cloze(sentence, keyword):
    """Replace keyword in sentence with blank for cloze question."""
    pat = re.compile(r"\b" + re.escape(keyword) + r"\b", flags=re.I)
    if pat.search(sentence):
        return pat.sub("_____", sentence, count=1)
    return None


def generate_mcq(sentence, keyword, keywords_pool, num_options=4):
    """
    Generate meaningful MCQ with proper question wording.
    Fills the keyword as a blank in the sentence.
    """
    masked_sentence = re.sub(rf"\b{re.escape(keyword)}\b", "_____", sentence, flags=re.I)
    question = f"Fill in the blank: {masked_sentence}"

    distractors = [kw for kw in keywords_pool if kw.lower() != keyword.lower() and len(kw) > 2]
    random.shuffle(distractors)
    options = distractors[:num_options - 1] + [keyword]
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
    keywords = extract_keywords(text, top_n=num_questions * 5)  # extra keywords for variety

    quiz = {"cloze": [], "mcq": []}
    used_sentences = set()

    # ----------------- Cloze Questions -----------------
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

    # ----------------- MCQs - FIXED VERSION -----------------
    mcq_generated = 0
    used_mcq_sentences = set()
    used_mcq_keywords = set()
    attempts = 0
    max_attempts = len(keywords) * len(sentences)  # Prevent infinite loop
    
    while mcq_generated < num_questions and attempts < max_attempts:
        attempts += 1
        kw = random.choice(keywords)
        
        # Skip if we've already used this keyword for MCQ
        if kw in used_mcq_keywords:
            continue
            
        # Find sentences containing this keyword that haven't been used for MCQ
        available_sentences = [s for s in sentences 
                             if kw.lower() in s.lower() 
                             and s not in used_mcq_sentences]
        
        if not available_sentences:
            continue
            
        s = random.choice(available_sentences)
        
        # Generate MCQ
        mcq_question = generate_mcq(s, kw, keywords)
        
        # Ensure we have enough options
        if len(mcq_question["options"]) >= 2:  # At least correct answer + 1 distractor
            quiz["mcq"].append(mcq_question)
            used_mcq_sentences.add(s)
            used_mcq_keywords.add(kw)
            mcq_generated += 1

    # If we still don't have enough MCQs, try with relaxed constraints
    if len(quiz["mcq"]) < num_questions:
        remaining_needed = num_questions - len(quiz["mcq"])
        
        # Reset used keywords but keep used sentences
        for kw in keywords:
            if kw not in used_mcq_keywords and remaining_needed > 0:
                available_sentences = [s for s in sentences 
                                     if kw.lower() in s.lower() 
                                     and s not in used_mcq_sentences]
                
                if available_sentences:
                    s = random.choice(available_sentences)
                    mcq_question = generate_mcq(s, kw, keywords)
                    
                    if len(mcq_question["options"]) >= 2:
                        quiz["mcq"].append(mcq_question)
                        used_mcq_sentences.add(s)
                        used_mcq_keywords.add(kw)
                        remaining_needed -= 1

    return quiz