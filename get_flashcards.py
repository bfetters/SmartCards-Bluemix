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
    import requests
    import ast
    import regex as re

    f = open("./bluemix_authentication.config", "r")
    auth = ast.literal_eval(f.read())

    url='https://gateway.watsonplatform.net/concept-insights/api/v2/graphs/wikipedia/en-20120601/annotate_text'
    headers = { 'Content-Type': 'text/plain'}
    r = requests.post(url,
                      headers=headers,
                      data={'body': user_text},
                      auth=auth)

    concepts = set(label['concept']['label']for label in ast.literal_eval(r.content).values()[0])

    copy = concepts.copy()
    pattern1 = '[0-9]'
    pattern2 = '\(\w+\)'

    for concept in concepts:
        # drop concepts with numerics
        r = re.search(pattern1,concept)
        if r:
            copy.discard(concept)
            continue

        r = re.search(pattern2,concept)
        if r:
            copy.discard(concept)

    concepts = list(copy)

    if len(concepts) == 0:
        concepts = [user_text]

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