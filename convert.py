import subprocess
import sys
import os
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
import pandas as pd

PATH_TO_PROJECT = "repos/project"
RESULT_PATH = "result.csv"
LOG_NAME = "log.txt"
SEPARATOR = "-"

def clone_repository(uri):
    # TODO: better exception handling
    try:
        subprocess.call(["git", "clone", uri, PATH_TO_PROJECT])
    except Exception as e:
        print("asd")

def get_git_log():
    os.chdir(PATH_TO_PROJECT)
    with open(LOG_NAME, "w") as f:
        subprocess.call([
        "git", 
        "log", 
        "--branches", 
        "--tags", 
        "--remotes", 
        "--full-history", 
        "--reverse", 
        # "--shortstat", we will deal with this later
        "--format=%h,%an,%ai,%f"], stdout=f)

def create_csv_from_git_log():
    header_names=["shaid","author","date","message","activity", "case id"]
    df = pd.read_csv(LOG_NAME, sep=",", header=None, names=header_names)

    ps = PorterStemmer()
    
    for i in df.index:
        message = None
        author = None
        df["case id"] = "case 1"

        try:
            message = str(df["message"][i]).lower()
            author = df["author"][i].lower()
        except:
            print("value is not a string")
            df["activitiy"][i] = "nonconventional"
            continue

        if is_issue(message):
            df["activity"][i] = "issue"
        elif is_bot(author):
            df["activity"][i] = "bot"
        elif not starts_with_verb(message):
            df["activity"][i] = "nonconventional"
        else:
            first_word = message.split(SEPARATOR)[0]
            df["activity"][i] = ps.stem(first_word)
    
    df.to_csv(RESULT_PATH, index=False, header=True)
        
# could be extended
def is_bot(author):
    return "bot" in author

def starts_with_verb(message):
    VERB_CODES = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ", "VERB"]
    sentence = message.replace("-", " ").capitalize() + "."
    code_for_wirst_word = nltk.pos_tag(word_tokenize(sentence))[0][1]
    asd = nltk.pos_tag(word_tokenize(sentence))
    return code_for_wirst_word in VERB_CODES

def is_issue(message: str):
    splits = message.split(SEPARATOR)
    return len(splits) > 1 and splits[1].isnumeric()

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("USAGE...")
    
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    clone_repository(sys.argv[1])
    get_git_log()
    create_csv_from_git_log()
    
