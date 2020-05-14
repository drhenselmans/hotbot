# This script expands a number of fcfgs

import os
import re
import nltk
import random
import time
import linecache
from nltk.parse.generate import generate
from nltk import load_parser
from nltk import grammar, parse, Production
from progress.bar import Bar
from collections import defaultdict

def gaz_to_fcfg(path, name):
    # Function to convert a gazetteer with features to fcfg rules that can be read by the generator
    file=open(path, "r")
    lines=file.read().splitlines()
    file.close()
    
    d = {}
    for line in lines:
        # split into list based on separators
        sf = re.split('\[|\]|\n', line)
        # filter out empty list items
        sf = list(filter(None, sf))
        if len(sf) == 1:
            # words that do not have associated features are added to a dictionary entry with key "NULL"
            if 'NULL' not in d:
                d['NULL'] = sf
            else:
                d['NULL'] += sf
        elif len(sf) == 2:
            # words that do have associated features are added to a dictionary entry with features as key
            if sf[1] not in d:
                d[sf[1]] = [sf[0]]
            else:
                d[sf[1]] += [sf[0]]
        else:
            print("ERROR: Invalid syntax in gazetteer '"+name+".gaz'")

    fcfggaz = ""
    for key in sorted(d.keys()):
        fcfggaz += "\n"+name
        if key != "NULL":
            fcfggaz += "["+key+"]"
        fcfggaz += " -> '"+"' | '".join(d[key])+"'"

    fcfggaz = "\n"+name+" -> '"+name+"'"
    return(fcfggaz)

def iter_to_sample(iterator, parser, samplesize):
    # Function to generate a random sample from a large iterator without loading the entire thing into memory
    results = []
    x = 0
    # Iterate until the minimum amount of samples is reached
    try:
        while len(results) < samplesize:
            v = next(iterator)
            if parser.parse_one(v):
                results.append(v)
            x += 1
    except StopIteration:
        raise ValueError("Population not large enough to draw "+str(samplesize)+" grammatical samples.")
        return results
    random.shuffle(results)  # Randomize positions of matches so far
    for i, v in enumerate(iterator, x): # Continue where you left off, at x
        r = random.randint(0, i) # Random number between 0 and current iteration
        if r < samplesize: # If it happens to be between 0 and the sample size...
            if parser.parse_one(v): # AND viable for this list...
                results[r] = v  # Replace that random item. At a decreasing rate, since i increases.
    print("Randomly selected {} out of {} sentences.".format(samplesize, i))
    return results

def expand_to_sample(iterator, samplesize):
    # Test function: alternative to iter_to_sample that writes to file and then iterates over file lines until it has enough. Very slow!
    tmpfile = "runtime/question.fcfg.exp"
    if os.path.exists(tmpfile):
        os.remove(tmpfile)
    tmp = open(tmpfile, 'a+')
    for i, v in enumerate(iterator):
        tmp.write(' '.join(v)+'\n')
    randorder = random.shuffle(list(range(0,i)))
    results = []
    x = 0
    while len(results) < samplesize:
        for j, w in enumerate(tmp):
            if j == randorder[x]:
                if parser.parse_one(w):
                    results.append(w)
        x += 1
    print("Randomly selected {} out of {} sentences".format(i, samplesize))
    return results

def compile_grammar(pt, gazlist):
    # Simple text transformation that reads the 'gazetteers' and turns them into a format FCFG can read
    sourcepath = 'fcfg/'+pt+'.fcfg'
    targetpath = 'runtime/'+pt+'.fcfg'
    with open(sourcepath) as source:
        sourcelines = source.readlines() # Original FCFG in fcfg/
    if os.path.exists(targetpath):
        os.remove(targetpath)
    with open(targetpath, 'a+') as target:
        toprule = re.compile("(S -> )(\S*)")
        gazref = re.compile("([A-Z][A-Z]+(?:\[[^\]]*\])*)")
        for line in sourcelines:
            line = toprule.sub(r"\1\2 '\2'", line) # Add the names of the top rules to the end of the line for later reference
            line = gazref.sub(r"'\1'", line) # Put gazetteers in quotes to substitute them later
            target.write(line)
        for gaz in gazlist:
            try:
                gazpath = 'gazetteers/'+gaz+'.gaz'
                fcfg_gaz = gaz_to_fcfg(gazpath, gaz) # Transform gazetteer file into FCFG format
                target.write(fcfg_gaz) # Add FCFG-formed gazetteers to end of target file
            except FileNotFoundError:
                print(gazpath+" not found.")
    print("FCFG for pt '"+pt+"' with tags {} ".format(gazlist)+" was written to "+targetpath)

def expand_grammar(pt, size):
    # Expanding the grammar until a certain number of valid expansions was found
    grammarpath = 'runtime/'+pt+'.fcfg'
    corpuspath = 'runtime/corpus/'+pt+'.cas'
    grammar = nltk.data.load(grammarpath) # Load the grammar that was constructed into NLTK
    parser = nltk.FeatureChartParser(grammar) # Parse using this grammar to see if a sentence is a part of it
    if os.path.exists(corpuspath):
        os.remove(corpuspath)
    print("Selecting {} random samples for {} grammar expansion...".format(size, pt))
    start = time.time()
    valid_expansions = iter_to_sample(generate(grammar), parser, size) # Function that randomly selects from valid expansions
    end = time.time()
    print("Took {} seconds.".format(end - start))
    with open(corpuspath, 'w') as corpus:
        for v in valid_expansions:
            corpus.write(pt+'\t'+' '.join(v)+'\n') # Write valid expansions to corpus file
    print(str(size)+" sentences written to "+corpuspath)

#And here the only actual runtime commands. There are only 2 of these now, but the format is there to expand it.
compile_grammar('question', ['NOUN', 'VERB', 'QUALITY'])
compile_grammar('statement', ['NOUN', 'VERB', 'QUALITY'])
print()
expand_grammar('question', 1000)
print()
expand_grammar('statement', 1000)
