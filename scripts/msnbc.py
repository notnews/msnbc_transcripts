#!/usr/bin/env python
# coding: utf-8

import os
import sys
import importlib
import scrapelib
from bs4 import BeautifulSoup
from dateutil import parser
import re
import csv
from datetime import date, timedelta

columns = ['air_date',
           'show_name',
           'headline',
           'guests',
           'url',
           'channel.name',
           'program.name',
           'uid',
           'duration',
           'year',
           'month',
           'date',
           'time',
           'timezone',
           'path',
           'wordcount',
           'subhead',
           'summary',
           'text']


def extract_transcript(html, data):
    soup = BeautifulSoup(html, "html.parser")
    datePublished = soup.find('time').text
    date = parser.parse(datePublished, fuzzy=True)
    tz = 'UTC'
    content = soup.find("div", {"class": "article-body__content"})
    asum = content.find('a', {'id': 'anchor-Summary'})
    if asum:
        summary = asum.next_sibling.text
    else:
        summary = ''
    atran = content.find('a', {'id': 'anchor-Transcript'})
    if atran:
        content = '\n'.join([e.text for e in atran.next_siblings])
    else:
        content = content.text
    try:
        print(date)
        data['channel.name'] = 'MSNBC'
        data['program.name'] = data['headline']
        data['year'] = date.year
        data['month'] = date.month
        data['date'] = date.day
        data['time'] = "%02d:%02d" % (date.hour, date.minute)
        data['timezone'] = tz
        data['subhead'] = ''
        data['summary'] = summary
        data['text'] = content
    except Exception as e:
        print(e)
    return data


if __name__ == "__main__":
    OUTPUT_FILE = "msnbc.csv"
    new_file = not os.path.exists(OUTPUT_FILE)

    f = open(OUTPUT_FILE, "a", newline='\n', encoding='utf-8')
    writer = csv.DictWriter(f, fieldnames=columns, dialect='excel')

    if new_file:
        writer.writeheader()

    s = scrapelib.Scraper(requests_per_minute=60)

    # Will be throttled to 10 HTTP requests per minute
    for p in range(1, 485):
        print('Page: ', p)
        res = s.get('https://www.msnbc.com/transcripts?sort=datePublished:asc&page=%d' % p)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.find_all("div", {"class": "transcript-card"}):
            #print(a)
            air_date = a.find("div", {"class": "transcript-card__air-date"}).text
            link = a.find("a", {"class": "transcript-card__show-name"})
            show_name = link.text
            url = link['href']
            headline = a.find("a", {"class": "transcript-card__headline"}).text
            guests = a.find("span", {"class": "transcript-card__guests"}).text
            print(air_date, url)
            data = {'air_date': air_date,
                    'show_name': show_name,
                    'headline': headline,
                    'guests': guests,
                }
            try:
                res2 = s.get(url)
                data = extract_transcript(res2.text, data)
                data['url'] = url
                writer.writerow(data)
            except Exception as e:
                print(e)
                print(url, res2.response)
        #break
    f.close()
