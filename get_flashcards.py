"Main app to get flashcards for web"

import os, json
import pandas as pd
from flask import Flask
from flask.ext.cors import CORS
import subprocess
from nltk.stem.porter import PorterStemmer
#pip install -U flask-cors

app = Flask(__name__)

CORS(app)

def extract_concepts(user_text):
    '''extract concepts from user input '''
    import nltk
    from nltk.corpus import stopwords
    import pandas as pd
    import numpy as np
    
    def split_lexicon_keywords(lexicon):
        lst = []
        for keyword in lexicon:
            try:
                for token in keyword.split(" "):
                    if unicode(token) not in stopwords.words():
                        lst.append(token)
            except: AttributeError
        return lst

    def to_lowercase(math_list):
        # lower case all math words 
        word_list = []
        for word in math_list:
            try:
                word_list.append(word.lower())
            except: AttributeError
        return word_list
    
    
    # get math lexicons
    df_cal = pd.read_csv("data/calculus_lexicon.csv", header=None)
    df_alg = pd.read_csv("data/algebra_lexicon.csv", header=None)
    df_trig = pd.read_csv("data/trigonometry_lexicon.csv", header=None)
    df_geo = pd.read_csv("data/geometry_lexicon.csv", header=None)
    
    cal = df_cal[df_cal.columns].values[0]
    alg = df_alg[df_alg.columns].values[0]
    trig = df_trig[df_trig.columns].values[0]
    geo = df_geo[df_geo.columns].values[0]
    
    # split lexicon terms to increase diversity of math terms
    cal  = split_lexicon_keywords(cal)
    alg  = split_lexicon_keywords(alg)
    trig = split_lexicon_keywords(trig)
    geo  = split_lexicon_keywords(geo)
    
    cal  = to_lowercase(cal)
    alg  = to_lowercase(alg)
    trig = to_lowercase(trig)
    geo  = to_lowercase(geo)
    
    # tokenize syllabus 
    tokens = nltk.tokenize.regexp_tokenize(user_text, r'[\w+]+')

    # filter out stop words for user_text, create unigrams and bigrams
    unigrams = [word for word in tokens if word.lower() not in stopwords.words()]
    bigrams_tuples = [bigram for bigram in nltk.bigrams(unigrams)]
    
    # join bigrams tuples into bigram terms
    bigrams = [ " ".join(bigram)  for bigram in bigrams_tuples ]
    
    # extract keyowrds from syllabus
    bigram_keywords = [word for word in bigrams if word in cal or word in alg or word in trig or word in geo]
    unigram_keywords = [word for word in unigrams if word in cal or word in alg or word in trig or word in geo]
    
    # return a single list of keywords
    # return np.unique(unigram_keywords + bigram_keywords).tolist()

    concepts = np.unique(unigram_keywords + bigram_keywords).tolist()

    import requests
    import ast

    auth=('82a698f0-8d8c-42f9-9c7d-1e4b97eebd52','50KJG6jdgZ6h')

    all_concepts = []
    for c in concepts:
        c = c.capitalize()
        url = 'https://gateway.watsonplatform.net/concept-insights/api/v2/graphs/wikipedia/en-20120601/concepts/'\
             + c +'/related_concepts'
        r = requests.get(url, auth=auth)
        if r.status_code == 200:
            all_concepts.append(ast.literal_eval(r.content))

    results = []
    threshold = 0.977
    for c in all_concepts:
        li_temp = c['concepts']
        for d in li_temp:
            if d['score'] > threshold:
    #             print (d['concept']['label'], d['score'])
                results.append(d['concept']['label'])


    print "RESULTS: ",results
    return results

def scan_data_and_return_json(concepts):
    
    response = []
    path_to_json = 'data/'
    
    json_files = [s for s in os.listdir(path_to_json) if s.endswith('.json')]

    concept_files = []
    for concept in concepts:
        for json_file in json_files:
            if json_file.startswith(concept):
                concept_files.append(json_file)
                
    print concept_files
    for concept_file in concept_files:
        with open(os.path.join(path_to_json, concept_file)) as f:
            response.append(json.load(f))
    return json.dumps(response)

@app.route("/<category>")
def get_flashcards(category):

    def gen_concepts_to_mine(L):
        start, end = L[0], L[-1]
        return sorted(set(range(start, end + 1)).difference(L))

    #Comment this to make it look into data folder
    path_to_json = 'data/'
    
    category = category.split('=')[1].replace('\n',' ')

    # if len(category.split(' ')) > 1:
    #     concepts = extract_concepts(category)
    # else:
    #     concepts = [category]

    print 'CATEGORY: ',category
    concepts = extract_concepts(category)
    
    porter_stemmer = PorterStemmer()
    stemmed_concepts = [porter_stemmer.stem(concept) for concept in concepts]

    print 'STEMMED CONCEPTS: ',stemmed_concepts
    print 'CONCEPTS: ',concepts

    # First, look to see if we've already mined these concepts
    concepts_to_mine = []
    for i,concept in enumerate(stemmed_concepts):
        existing_file = False
        for fname in os.listdir(path_to_json):
            if fname.endswith('.json') and concept in fname:
                existing_file = True
                break
        if not existing_file:
            concepts_to_mine.append(concepts[i])
    
    print 'CONCEPTS TO MINE: ',concepts_to_mine
    # If we haven't already mined concept do it now
    for concept in concepts_to_mine:
        p = subprocess.Popen("python mine_wordnet.py " + "'" + concept + "'", stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
    
    return scan_data_and_return_json(stemmed_concepts)
 
if __name__ == '__main__':
    app.run()