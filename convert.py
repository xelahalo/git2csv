import subprocess
import sys
import os
from nltk.stem import PorterStemmer, LancasterStemmer
from nltk.tokenize import word_tokenize
import nltk
import pandas as pd
import uuid
import numpy as np
import pm4py
import re
import string

RESULT_PATH = "result"
CSV = "csv"
LOG_NAME = "log.txt"
SEPARATOR = " "
COMMON_WORDS = "common_title_words.txt"
VERB_CODES = ["VB", "VBD", "VBG", "VBN", "VBP", "VBZ", "VERB"]
common_words = []

def clone_repository(uri):
    # TODO: better exception handling
    git_name = uri.split("/")[-1]
    folder = f"repos/{git_name}"
    try:
        subprocess.call(["git", "clone", uri, folder])
    except Exception as e:
        print("asd")
    
    return folder

def get_git_log(folder):
    os.chdir(folder)
    with open(LOG_NAME, "w") as f:
        subprocess.call([
        "git", 
        "log", 
        "--branches", 
        "--tags",
        "--remotes", 
        "--full-history", 
        "--reverse", 
        "--stat",
        "--format=%h;%an;%as;%f"], stdout=f)

def get_git_log_with_stats(folder):
    os.chdir(folder)
    with open(LOG_NAME, "w") as f:
        subprocess.call([
            "git",
            "log",
            "-w",
            "--all",
            "--numstat",
            "--reverse",
            "--encoding=UTF-8",
            "--pretty=format:%H;%an;%as;%s"
        ], stdout=f)

def process_log():
    header_regex = "(.*);(.*);(\d+-\d+-\d+);(.*)"
    stats_regex = "[\d-]+\s+[\d-]+\s+([\S ]+)\s*"
    rename_regex = "(\S*)\s*=>\s*(\S*)"

    ls = LancasterStemmer()

    prev_header = None
    rows_to_append = {}
    file_case_counter = {}

    with open(LOG_NAME, "r", encoding="UTF-8") as f:
        for row in f:
            header = re.match(header_regex, row)
            if header is not None:
                shaid, author, time, sl = header.groups()
                sl = sl.lower()
                author = author.lower()
                prev_header = {"id": shaid, "author": author, "time": time, "subject_line": sl, "activity": get_activity(sl, author, ls)}
                continue

            stats = re.match(stats_regex, row)
            if stats is not None:
                filename = stats.groups()[0]
                rename_match = re.match(rename_regex, filename)

                if rename_match is not None:
                    continue
               
                key = filename
                if filename in file_case_counter.keys():
                    val = file_case_counter[filename]
                    key += f"_{str(val)}"
                    file_case_counter[filename] = val + 1
                else:
                    key += "_0"
                    file_case_counter[filename] = 1

                rows_to_append[key] = prev_header.copy()

    for key in rows_to_append.keys():
        case_id = key.rstrip(string.digits + '_')
        rows_to_append[key]["case_id"] = case_id

    df = pd.DataFrame.from_records(list(rows_to_append.values()))

    write_xes(df)

def create_xes_from_git_log():
    header_names=["id","author","time","subject_line","activity", "case id"]
    df = pd.read_csv(LOG_NAME, sep=";", header=None, names=header_names, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d")
    
    # ps = PorterStemmer()
    ls = LancasterStemmer() # lancasterstemmer seems to produce rougher stemmings, which is good in our case

    for i in df.index:
        message = None
        author = None

        df["case id"][i] = "case_" + str(df["time"][i].value)
        # df["case id"][i] = "case_" + str(df["author"][i].replace(" ", "_"))

        try:
            message = str(df["message"][i]).lower()
            author = df["author"][i].lower()
        except:
            print("value is not a string")
            df["activitiy"][i] = "nonconventional"
            continue

        df["activity"][i] = get_activity(message, author, ls)

        write_xes(df)

def write_xes(df):
    filename=str(uuid.uuid4())
    # TODO make it be aware of the traces
    for idx, chunk in enumerate(np.array_split(df, 10)):
        chunk = pm4py.format_dataframe(chunk, case_id="case_id", activity_key="activity", timestamp_key="time")
        log = pm4py.convert_to_event_log(chunk)
        pm4py.write_xes(log, f"../../results/{filename}_part{idx}.xes")
    # df = pm4py.format_dataframe(df, case_id="case_id", activity_key="activity", timestamp_key="time")
    # log = pm4py.convert_to_event_log(df)
    # pm4py.write_xes(log, f"../../results/{filename}.xes")

def get_activity(message, author, stemmer):
    if is_issue(message):
        return "issue"
    elif is_bot(author):
        return "bot"
    elif not is_conventional(message):
        return "nonconventional"
    else:
        first_word = message.split(SEPARATOR)[0]
        return stemmer.stem(first_word)

# could be extended
def is_bot(author):
    return "bot" in author

def is_conventional(message):
    if message.endswith('.') or len(message) > 50:
        return False
    
    sentence = message.capitalize() + "."
    first_word = nltk.pos_tag(word_tokenize(sentence))[0]

    return first_word[1] in VERB_CODES or first_word[0] in common_words

def is_issue(message: str):
    regex = "\[.+-\d+\].*"
    return re.match(regex, message) is not None

def load_common_words():
    with open(COMMON_WORDS, "r") as f:
        return [line.strip() for line in f.readlines()]

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("USAGE...")

    # nltk.download('punkt')
    # nltk.download('averaged_perceptron_tagger')
    common_words = load_common_words()
    folder = clone_repository(sys.argv[1])
    get_git_log_with_stats(folder)
    # create_csv_from_git_log()
    process_log()


