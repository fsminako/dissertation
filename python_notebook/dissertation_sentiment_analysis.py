# -*- coding: utf-8 -*-
"""dissertation_sentiment_analysis.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1TKrOr6-047o8VpH9j7TLYkNzOxqzhIks

# Data Import

## News Article URL Import
"""

!git clone https://github.com/fsminako/dissertation

# Commented out IPython magic to ensure Python compatibility.
# %ls dissertation/data/

import pandas as pd

df_url = pd.read_csv('dissertation/data/news_articles.csv')

df_url

"""## Articles Extraction"""

import requests
from bs4 import BeautifulSoup as bs
import os

output_dir = "dissertation/news_article"
os.makedirs(output_dir, exist_ok=True)

def fetch_article(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article {url}: {e}")
        return None

def parse_article(content):
    soup = bs(content, 'html.parser')

    # Fetch the title
    title_tag = soup.find('h1', class_='tjp-title tjp-title--single')
    if title_tag:
        title = title_tag.text.strip()
    else:
        title = "Title not found"

    # Fetch the summary
    summary_tag = soup.find('p', class_='tjp-summary tjp-summary--single')
    if summary_tag:
        summary = summary_tag.text.strip()
    else:
        summary = ""

    # Fetch the opening
    opening_tag = soup.find('div', class_='tjp-opening')
    if opening_tag:
        opening = ''.join([element.text.strip() for element in opening_tag.find_all(['h1', 'p'])])
    else:
        opening = ""

    # Fetch the content
    paragraphs = []
    for p in soup.find_all("p"):
        if p.text.strip() and not p.find_parent('div', class_='tjp-single__content-ads') and not p.find_parent('div', class_='tjp-newsletter-box'):
            paragraphs.append(p.text.strip())

    if not paragraphs:
        content = ""
    else:
        content = ' '.join(paragraphs)

    # Combine summary, opening, and content into one
    full_content = ' '.join([summary, opening, content]).strip()
    if not full_content:
        full_content = "Article content not found"

    return title, full_content

# Iterate through the URLs and fetch the articles
for url in df_url['url']:
    content = fetch_article(url)
    if content:
        title, full_content = parse_article(content)
        # Save the article to a text file
        file_name = f"{title}.txt".replace(' ', '_').replace('/', '_')  # Ensure the file name is valid
        with open(os.path.join(output_dir, file_name), 'w', encoding='utf-8') as file:
            file.write(full_content)
    else:
        print(f"Failed to fetch or parse the article from {url}")

"""## Sentence Splitter"""

!pip install llama_index.core
!pip install llama_index.readers.file

from llama_index.readers.file import FlatReader
from llama_index.core.node_parser import SentenceSplitter
from pathlib import Path

# Initialize the FlatReader
reader = FlatReader()

# Path to the directory containing the documents
directory_path = Path("dissertation/news_article/")

# Initialize an empty list to store the sentences and their file names
sentences = []

# Load data from all text files in the directory
for file_path in directory_path.glob("*.txt"):
    data = reader.load_data(file_path)
    for doc in data:
        # Initialize the SentenceSplitter for each document
        parser = SentenceSplitter(chunk_size=100, chunk_overlap=0)
        nodes = parser.get_nodes_from_documents([doc])
        for node in nodes:
            sentences.append({"file_name": file_path.name, "sentence": node})

# Create a DataFrame from the list of sentences
df = pd.DataFrame(sentences)

df

# Function to extract text after "Text:"
def extract_text_after_text_column(entry):
    try:
        # Ensure the entry is a string
        entry = str(entry)
        return entry.split('Text:')[1].strip()
    except (IndexError, AttributeError):
        return None

# Apply the function to the 'sentence' column to create a new column 'extracted_text'
df['sentence'] = df['sentence'].apply(extract_text_after_text_column)

df

"""# Data Pre-Processing

## Data Cleaning
"""

import re

#Defining the cleaning function for the content column
def cleaning(text):
    if isinstance(text, str):
        url_pattern = re.compile(r'https://\S+|www\.\S+')
        text = url_pattern.sub('', text)
        text = re.sub(r"[’]", "'", text)
        text = re.sub(r"[^a-zA-Z\s'-]", "", text)
        text = ' '.join(text.split())
        text = text.lower()
    return text

df['sentence'] = df['sentence'].apply(lambda x: cleaning(x))

#Defining the cleaning function for the file name column
def cleaning_name(text):
    if isinstance(text, str):
        text = re.sub(r".txt", "", text)
        text = re.sub(r"[^a-zA-Z\s'-]", " ", text)
        text = text.lower()
    return text

df['file_name'] = df['file_name'].apply(lambda x: cleaning_name(x))

df

"""## Tokenisation"""

import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')

from nltk.tokenize import word_tokenize
from nltk import wordpunct_tokenize
from nltk.corpus import stopwords

stop_words = stopwords.words('english')

def tokenisation(text):
    if isinstance(text, str):
        # Tokenize the text
        words = word_tokenize(text)
        # Remove stopwords
        words = [word for word in words if word not in stop_words]
        # Rejoin the words into a single string
        text = ' '.join(words)
    return text

df['sentence'] = df['sentence'].apply(tokenisation)

df

"""## Data Standardisation"""

nltk.download('wordnet')
from nltk.stem import WordNetLemmatizer, PorterStemmer, SnowballStemmer

def standardisation(text):
    # Tokenize the text
    words = word_tokenize(text)
    # Stemming
    #stemmer = PorterStemmer()
    #words = [stemmer.stem(word) for word in words]
    # Lemmatization
    lemmatizer = WordNetLemmatizer()
    words = [lemmatizer.lemmatize(word) for word in words]

    return ' '.join(words)

df['sentence'] = df['sentence'].apply(standardisation)

df

"""# Sentiment Analysis"""

# Commented out IPython magic to ensure Python compatibility.
# %pip install transformers

from transformers import pipeline

sent_pipeline = pipeline('sentiment-analysis', model='distilbert-base-uncased-finetuned-sst-2-english')

def get_sentiment_score(sentence):
    result = sent_pipeline(sentence)[0]
    return result['score'] if result['label'] == 'POSITIVE' else -result['score']

df['score'] = df['sentence'].apply(get_sentiment_score)

# Define a function to determine the label based on the score
def determine_label(score):
    return 'positive' if score > 0 else 'negative'

# Apply the function to create the 'label' column
df['label'] = df['score'].apply(determine_label)

df

df.to_csv('dissertation/analysis_reult.csv', index=False)

"""# Data Visualisation"""

label_counts = df['label'].value_counts()

positive_count = label_counts.get('positive', 0)
negative_count = label_counts.get('negative', 0)

negative_count

import matplotlib.pyplot as plt

# Data for plotting
labels = ['Positive', 'Negative']
counts = [positive_count, negative_count]

# Plotting the pie chart
plt.figure(figsize=(8, 6))
plt.pie(counts, labels=labels, colors=['lightgreen', 'lightcoral'], autopct='%1.1f%%', startangle=140)
plt.title('Public Sentiment on Mining Industry', fontweight='bold')
plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
plt.savefig('sentiment_analysis_pie_chart.png')
plt.show()