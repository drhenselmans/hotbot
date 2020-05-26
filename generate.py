# This script expands a number of fcfgs

import os
import re
import nltk
import random
import time
import linecache
from nltk.parse.generate import generate
from nltk import grammar, load_parser, parse, Production
from progress.bar import Bar

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

    return(fcfggaz)

def iter_to_sample(iterator, parser, samplesize):
    # Function to generate a random sample from a large iterator without loading the entire thing into memory
    results = {} # Dictionary that will contain a sample of valid sentence structures generated from the FCFG by signature
    number_found = {} # Dictionary that will keep track of how many valid sentence structures have been found per signature
    # Iterate until the minimum amount of samples is reached
    for structure in iterator:
        if parser.parse_one(structure): # If the generated sentence structure is feature-correct:
            signature = structure[-1] # Signature is written as last word in line
            if signature not in results:
                number_found[signature] = 1
                results[signature] = [structure] # If signature is not yet a key in the dictionaries, add it
                print("Expanding "+signature)
            else:
                number_found[signature] += 1
                if len(results[signature]) < samplesize: # If number of sentence structures for signature is below sample size, append
                    results[signature].append(structure)
                    if len(results[signature]) == samplesize:
                        random.shuffle(results[signature]) # Shuffle once sample size has been reached
                else:
                    r = random.randint(0, number_found[signature])
                    # For each sentence structure that is found after sample size has been reached, 
                    # the chance of adding it into the sample is [sample size / total found]
                    # This generates a random selection from the iterator.
                    if r < samplesize:
                        results[signature][r] = structure
    print()
    for signature in results.keys():
        print("{}: {} out of {} possible sentence structures selected".format(signature, len(results[signature]), number_found[signature]))
        if number_found[signature] < samplesize:
            print("\tPossible sentence structures lower than sample size")
    return results

def expand_gazref(line, gazlist):
    # Read a sentence structure, scan it for references to gazetteers, and generate a valid expansion
    expandedline = [] # The target expanded sentence
    gazdict = {} # Dictionary that contains compiled gazetteer info, so compilation only has to happen once
    for gaz in gazlist:
        gazpath = 'gazetteers/'+gaz+'.gaz' # File where gazetteer is stored
        try:
            gazdict[gaz] = {
                    'regex': re.compile(gaz),
                    'path': gazpath,
                    'fcfg': gaz_to_fcfg(gazpath, gaz)
                    }
        except FileNotFoundError:
            print(gazpath+" not found.")
    for token in line:
        expanded = False
        for gaz in gazlist: # Check for each token whether it's one of the expandable gazetteers
            if gazdict[gaz]['regex'].match(token):
                expansionstring = "% start S\nS -> "+token+"\n"+gazdict[gaz]['fcfg'] # If gazetteer is a match...
                expansiongrammar = grammar.FeatureGrammar.fromstring(expansionstring) # Create grammar to expand it
                expansionlist = []
                for expansion in generate(expansiongrammar):
                    if nltk.FeatureChartParser(expansiongrammar).parse_one(expansion): # Test all possible expansions against feature requirements
                        expansionlist.append(expansion[0]) # And append the positives
                expandedline.append(random.choice(expansionlist)) # Select a random expansion
                expanded = True
                break # If match was found and expansion added, move to next token
        if expanded == False:
            expandedline.append(token) # If no gazetteer was matched, add the unchanged token
    return expandedline

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
            line = gazref.sub(r"'\1'", line) # Put gazetteers in quotes to substitute them later (in expand_gazref)
            target.write(line)
#        for gaz in gazlist:
#            try:
#                gazpath = 'gazetteers/'+gaz+'.gaz'
#                fcfg_gaz = gaz_to_fcfg(gazpath, gaz) # Transform gazetteer file into FCFG format
#                target.write(fcfg_gaz) # Add FCFG-formed gazetteers to end of target file
#            except FileNotFoundError:
#                print(gazpath+" not found.")
    print("FCFG for pt '"+pt+"' with tags {} ".format(gazlist)+" was written to "+targetpath)

def expand_grammar(pt, size):
    # Expanding the grammar until a certain number of valid expansions was found
    grammarpath = 'runtime/'+pt+'.fcfg'
    corpuspath = 'runtime/corpus/'+pt+'.cas'
    logpath = 'runtime/'+pt+'.log'
    grammar = nltk.data.load(grammarpath) # Load the grammar that was constructed into NLTK
    parser = nltk.FeatureChartParser(grammar) # Parse using this grammar to see if a sentence is a part of it
    if os.path.exists(corpuspath):
        os.remove(corpuspath)
    print("Selecting {} random samples per intent for {} grammar expansion...".format(size, pt))
    start = time.time()
    valid_expansions = iter_to_sample(generate(grammar), parser, size) # Function that randomly selects from valid expansions
    end = time.time()
    print("Took {} seconds.".format(end - start))
    t = 0 # Total number of generated sentences
    with open(corpuspath, 'w') as corpus, open(logpath, 'w') as log:
        for signature in valid_expansions.keys():
            i = 0 # sentences generated per PT
            while i < size:
                log.write("\nStarting new cycle for "+signature+"\n")
                for sentence_structure in valid_expansions[signature]:
                    log.write("Structure: "+' '.join(sentence_structure)+"\n")
                    sentence = expand_gazref(sentence_structure, gazlist) # Expand any gazetteer references in the sentence
                    log.write("Expand to: "+' '.join(sentence)+"\n")
                    corpus.write(pt+'\t'+' '.join(sentence[:-1])+'\t'+sentence[-1]+'\n') # Write valid expansions to corpus file
                    i += 1
                    t += 1
                    if i >= size:
                        break
        print("{} sentences written to {}".format(t, corpuspath))

#And here the only actual runtime commands. There are only 2 of these now, but the format is there to expand it.
gazlist = ['NOUN', 'VERB', 'QUALITY']

compile_grammar('question', ['NOUN', 'VERB', 'QUALITY'])
compile_grammar('statement', ['NOUN', 'VERB', 'QUALITY'])
print()
expand_grammar('question', 100)
print()
expand_grammar('statement', 100)
