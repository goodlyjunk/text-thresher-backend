# Article Parser
import sys
import os
import argparse
import re
from bs4 import BeautifulSoup
from collections import namedtuple

parser = argparse.ArgumentParser(description='Process an article or a folder \
                                              of articles.')
parser.add_argument('-f', '--file', nargs=1,
                    help='relative path to a single article')

parser.add_argument('-d', '--directory', nargs=1,
                    help='relative path to a directory of articles')

def clean(par, clean_text):
    clean_par = ''
    bracket = False
    # Remove whitespace
    par = par.replace('&#160;', '')
    par = par.replace(u'\u00A0', '')
    par = ' '.join(par.split())
    if par:
        par += '\n\n'

    return par

def clean_article_text(article):
    clean_text = ''
    for p in article.find_all('p'):
        clean_text += clean(p.text, clean_text)
    return clean_text

def get_offsets(text, delimiter, clean_text):
    offsets = []
    text = text.split(delimiter)
    for i in range(0, len(text)):
        text[i] = re.sub('[\[\]]', '', text[i])
        text[i] = " ".join(text[i].split())
        text[i] = text[i].rstrip().lstrip()
        try:
            begin = clean_text.index(text[i])
        except ValueError:
            print '[WARNING] Could not add highlight "', text[i]
            f = open('bad.txt', 'a')
            f.write((text[i] + "\n").encode('utf8'))
            f.close()
            continue
        end = begin + len(text[i])
        offsets.append([begin, end])
    return offsets

def parse_tuas(article, clean_text):
    tuas = []
    topics = []
    highlights = article.find_all('span')
    for highlight in highlights:
        try:
            topic = highlight['type-id']
        except KeyError:
            continue
        text = highlight.text
        # Delete trailing and leading whitespace
        text = text.rstrip().lstrip()
        offsets = []
        text = " ".join(text.split())
        try:
            begin = clean_text.index(text)
        except ValueError:
            print '[WARNING] Could not add highlight "', (text)
            f = open('bad.txt', 'a')
            f.write((text + "\n").encode('utf8'))
            f.close()
            continue
        end = begin + len(text)
        offsets.append([begin, end])
        # Aggregate the offsets
        if (topic in topics):
            tua = [tua for tua in tuas if tua['topic'] == topic][0]
            tua['offsets'].extend([begin, end])
        else:
            topics.append(topic)
            tua = {
                'topic': topic,
                'offsets': offsets
            }
            tuas.append(tua)
    return tuas

def parse_byline(article):
    try:
        line = article(text=re.compile(r'BYLINE'))[0]
    except IndexError:
        print '[INFO]    There is no byline'
        return '', ''
    line = line.replace('\n    BYLINE: By', '')
    try:
        author, periodical = line.split(', ')
    except ValueError:
        try:
            author, periodical = line.split(' - ')
        except ValueError:
            print '[WARNING] Could not parse byline'
            return '', ''
    return author.title(), periodical

def parse_annotators(line):
    version = re.search('v[0-9]+', line).group()
    annotators = line.replace(' ' + version + ',', '')
    return annotators, version

def parse_article(file_path):
    article = open(file_path, 'r').read()
    article = BeautifulSoup(article, 'xml').article
    paragraphs = article.find_all('p')
    annotators, version = parse_annotators(article['annotators'])
    author, periodical = parse_byline(article)
    clean_text = clean_article_text(article)
    metadata = {
        'annotators': annotators,
        'version': version,
        'date_published': article['date'],
        'article_id': file_path.split('-')[1],
        'city': article['city'].split('_')[0],
        'state': article['city'].split('_')[1],
        'author': author,
        'periodical': periodical,
    }
    return {
        'metadata': metadata,
        'text': clean_text,
        'tuas': parse_tuas(article, clean_text)
    }

def main():
    import pprint
    args = parser.parse_args()
    if args.file:
        file_path = args.file[0]
        data = parse_article(file_path)
        pprint.pprint(data)
        
    elif args.directory:
        dir_name = args.directory[0]
        articles = []
        for file_name in os.listdir(dir_name):
            if file_name.endswith(".xml"):
                print "[INFO]    Parsing", file_name
                articles.append(parse_article(os.path.join(dir_name, file_name)))
        pprint.pprint(articles)
        
    else:
        print('[ERROR]   No files specified. Aborting.')
        sys.exit()


if __name__ == '__main__':
    main()