import nltk
import os
import random

supported_intents = ["question", "statement"]
dev_partition = 0.3

def load_data(fpath):
    # Load file with a number of tab-delineated intent and sentence pairs, and return it in listed form
    dataset = []
    with open(fpath) as f:
        for line in f:
            intent = line.split()[0]
            se = line.split()[1:]
            dataset.append((se, intent))
    return dataset

def sentence_features(sentence, features):
    # Extract classification features from a sentence. Input is sentence and the set of features which needs to be determined
    word_types = set(sentence)
    featurebools = {}
    for feature in features:
        # features['contains('+word+')'] = (word in word_types) # Boolean: Does sentence contain this word?
        featurebools['startswith('+feature+')'] = bool(feature == sentence[0]) # Boolean: Does sentence start with this word?
    return featurebools

def extract_feature_list(dataset):
    # Extract list of all possible word features from the sentences in a dataset
    word_set = set()
    for (se, intent) in dataset:
        word_set.add(se[0]) # Return only the starting words
#        for word in se:
#            word_set.add(word) # Return every word
    return list(word_set)

def count_types(dataset):
    # Count the number of tokens of each intent type in the dataset
    for intent_type in supported_intents:
        token_count = sum(intent_type == intent_token for (se, intent_token) in dataset)
        percent = token_count / len(dataset)
        print(intent_type+":\t{} ({:.0%})".format(token_count, percent))
    print()

def split_dev_test(dataset, features):
    # Split dataset into development and training set
    dev_size = int(len(all_data) * dev_partition)
    featureset = [(sentence_features(se, features), intent) for (se, intent) in dataset]
    
    dev_set = featureset[:dev_size]
    train_set = featureset[dev_size:]
    return (dev_set, train_set)

# Start script
all_data = []
for intent in supported_intents:
    all_data.extend(load_data("runtime/corpus/"+intent+".cas"))
    # For all supported intents specified above, read associated file and read sentence tokens and intent as 'all_data'

word_features = extract_feature_list(all_data) # Extract list of features
random.shuffle(all_data) # Shuffle data before split so intents are evenly distributed
(dev_set, train_set) = split_dev_test(all_data, word_features) # Split generated data into dev and train partitions, and add feature information

print("Total Sentences: {}\nDev: {}, Train: {}\n".format(len(all_data), len(dev_set), len(train_set)))
print("Intents in train set: ")
count_types(train_set)
print("Intents in dev set: ")
count_types(dev_set)

classifier = nltk.NaiveBayesClassifier.train(train_set) # Train Naive Bayes classifier using added features
classifier.show_most_informative_features(50) # Print most informative features for evaluation

test_data = load_data("data/test.cas") # Load separate static test file
test_set = [(sentence_features(se, word_features), intent) for (se, intent) in test_data] # Extract features from test data

print("\nDev set accuracy: {:.2%}".format(nltk.classify.accuracy(classifier, dev_set)))
print("Test set accuracy: {:.2%}\n".format(nltk.classify.accuracy(classifier, test_set)))

# Enable the following to allow manually testing the classifier after it has been trained
flag = False
#print("Type sentence to classify:")
#flag = True
while flag==True:
    print('> ', end = '') 
    user_response = input().lower()
    if user_response in ("exit", "quit", "q"):
        flag=False
        # Quit by typing an exit prompt
    else:
        print(classifier.classify(sentence_features(user_response, word_features)))
        # If not an exit prompt, classify input
