# Get Surf Report 
# Given a URL get the surf report details
import re
import smtplib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from email.message import EmailMessage

# Get recipe list from file
def get_locations():
    return open('Surf Report/URLs.txt').readlines()

def get_webpage(page_url):
    page = requests.get(page_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup

def count_total_stars(soup, type_):
    tbody = soup.find_all('tbody')
    star_count = 0
    for body in tbody:
        count = 0
        for tr in body.find_all('tr'):
            # Get data from tag
            # if count == 1:
            #     date = tr['data-date-anchor']
            count += 1
            for li in tr.find_all('li', class_=type_):
                star_count += 1 
    
    return star_count


def get_day_stars(soup, type_):
    tbody = soup.find_all('tbody')
    daily_stars = []

    for body in tbody:
        count = 0
        star_count = 0
        for tr in body.find_all('tr'):
            # Get data from tag
            if count == 1:
                date = tr['data-date-anchor']
            count += 1
            for li in tr.find_all('li', class_=type_):
                star_count += 1 
        daily_stars.append({'Date':date, f'{type_} Star Count':star_count})

    return daily_stars


def get_period(soup):
    tbody = soup.find_all('tbody')
    daily_period = []

    for body in tbody:
        count = 0
        star_count = 0
        total_period = 0
        # for each day
        for tr in body.find_all('tr'):
            # Get data from tag
            if count == 1:
                date = tr['data-date-anchor']
            count += 1
            td_count = 0
            for td in tr.find_all('td'):
                if td_count == 4:
                    try:
                        # Get just the time in period without the 's'
                        total_period += int(td.h4.text.split('s')[0])
                    except:
                        'Opps'
                td_count += 1 
        # Return the period in seconds, divided by 8 as that is the amount of readings per day.
        daily_period.append({'Date':date, 'Period':round(total_period/8), 'Unit':'s'})

    return daily_period 


def get_size(soup):
    tbody = soup.find_all('tbody')
    results = []

    for body in tbody:
        count = 0
        star_count = 0
        small_size = 0
        big_size = 0
        # for each day
        for tr in body.find_all('tr'):
            # Get data from tag
            if count == 1:
                date = tr['data-date-anchor']
            count += 1
            td_count = 0
            for td in tr.find_all('td'):
                if td_count == 1:
                    try:
                        # Get the small wave size
                        small_size += int(td.span.text.split('-')[0])
                        # Remove the 'ft' from end [:-2] removes last two chars
                        big_size += int(td.span.text.split('-')[1][:-2])
                    except:
                        'No waves found'
                td_count += 1 
        # Return the period in seconds, divided by 8 as that is the amount of readings per day.
        results.append({'Date':date, 'Lower Wave Size':round(small_size/8,1), 'Higher Wave Size':round(big_size/8,1), 'ft/m':'ft'})

    return results 


def get_wind_direction(soup):
    tbody = soup.find_all('tbody')
    results = []
    wind_types = ['success', 'warning', 'danger']
    winds = []

    for body in tbody:
        count = 0
        star_count = 0
        strengths = []
        directions = []
        # for each day
        for tr in body.find_all('tr'):
            # Get data from tag
            if count == 1:
                date = tr['data-date-anchor']
            count += 1
            td_count = 0
            # Get the class for wind, as secondary swell affects the numbered position.
            for types in wind_types:
                for td in tr.find_all('td', class_=f'text-center last msw-js-tooltip td-square background-{types}'):
                    try:     
                        strength = td['title'].split(',')[0]
                        # Switch statement for better grouping (helps with count)
                        if strength == 'Very Light':
                            strength = 'Light'
                        if strength == 'Gentle':
                            strength = 'Light'
                        if strength == 'Fresh':
                            strength = 'Moderate'
                        if strength == 'Gale Force':
                            strength = 'Very Strong'
                        strengths.append(strength)
                        winds.append(strength)
                        direction = re.findall(r"[a-zA-Z]+",td['title'].split(',')[1])[0]
                        directions.append(direction)
                    except:
                        'Opps'
                    td_count += 1 
        try:
            common_strength = max(set(strengths), key=strengths.count)
            common_direction = max(set(directions), key=directions.count)
        except:
            'blah'
        # Return the period in seconds, divided by 8 as that is the amount of readings per day.
        results.append({'Date':date, 'Wind Strength':common_strength, 'Wind Direction':common_direction})

    return results 


def get_swell_direction(soup):
    tbody = soup.find_all('tbody')
    results = []

    for body in tbody:
        count = 0
        star_count = 0
        directions = []
        # for each day
        for tr in body.find_all('tr'):
            # Get data from tag
            if count == 1:
                date = tr['data-date-anchor']
            count += 1
            td_count = 0
            # Get the class for wind, as secondary swell affects the numbered position.
            for td in tr.find_all('td'):
                if td_count == 5:
                    try:     
                        direction = re.findall(r"[a-zA-Z]+",td['title'])
                        directions.append(direction)
                    except:
                        'Opps'
                td_count += 1 
  
        # Return the period in seconds, divided by 8 as that is the amount of readings per day.
        results.append({'Date':date, 'Swell Direction':direction})

    return results 


# TODO: Get tides, is not working as expected and must be worked on before use!
def get_tides(soup):
    tbody = soup.find_all('tbody')
    results = []

    for body in tbody:
        count = 0
        for tr in body.find_all('tr'):
            # Get data from tag
            if count == 1:
                date = tr['data-date-anchor']
            count += 1
        count = 0
        low_tide_details = []
        high_tide_details = []

        # for each day
        for tide_table in body.find_all('table', class_='table table-sm table-striped table-inverse table-tide'):
            tr_count = 0
            # Break as sunset table as the same class name
            if count > 0:
                break
            # For each row in the table (4 runs)
            for tr in tide_table.find_all('tr'):
                td_count = 0
                for td in tr.find_all('td'):
                    if td_count == 0:
                        tide_type = td.text
                    if td_count == 1:
                        try:
                            tide_time = td.text
                        except:
                            'No waves found'
                    elif td_count == 2:
                        try:
                            tide_height = td.text
                        except:
                            'No waves found'
                    td_count += 1 

                if tr_count == 0 or tr_count == 2:
                    high_tide_details.append({tide_type: tide_time, tide_type: tide_height})

                if tr_count == 1 or tr_count == 3:
                    low_tide_details.append({tide_type: tide_time, tide_type: tide_height})
                
                tr_count += 1
            count += 1   
        # Return the period in seconds, divided by 8 as that is the amount of readings per day.
        results.append({'Date':date, 'Low Tides':low_tide_details, 'High Tides':high_tide_details})

    return results

# TODO: Get wave energy from surf forecast
#  Will join by name and date 

def format_date(df):
    df['day']=df['Date'].str[-4:-2]
    df['month']=df['Date'].str[-2:]
    df['Day']=df['Date'].str[:-4]
    df['Date']=df['day']+'/'+df['month']
    df = df.drop(columns={'day','month'})
    day = df['Day']
    df = df.drop(columns={'Day'})
    df.insert(0, 'Day', day)
    return df

def x(x):
    return re.findall(r'[0-9]+', x)

def score_report(df):
    df['Score'] = 0

    df.loc[df['Avg Stars'] >= 2, 'Score'] = 2
    df.loc[df['Avg Stars'] >= 3, 'Score'] = 3
    df.loc[df['Avg Stars'] >= 4, 'Score'] = 6

    df.loc[df['Period'] > 10, 'Score'] += 1
    df.loc[df['Period'] >= 14, 'Score'] += 2
    df.loc[df['Period'] >= 18, 'Score'] += 3

    df.loc[df['Wind Direction'] == 'Offshore', 'Score'] += 2
    df.loc[df['Wind Direction'] == 'Onshore', 'Score'] -= 1

    df.loc[df['Wind Strength'] == 'Light', 'Score'] += 1.5
    df.loc[df['Wind Strength'] == 'Strong', 'Score'] -= 0.5
    df.loc[df['Wind Strength'] == 'Very Strong', 'Score'] -= 1

    df.loc[df['Lower Wave Size'] > 4, 'Score'] += 1
    df.loc[df['Lower Wave Size'] > 5, 'Score'] += 2
    df.loc[df['Higher Wave Size'] > 5, 'Score'] += 1
    df.loc[df['Higher Wave Size'] > 8, 'Score'] += 2

    df.loc[df['Score'] > 10, 'Score'] = 10

    return df

# Returns a list of elements: Break Name, Stars, Period, Wave Height, Score and Days (list)
def summarise_report(df):
    break_ = df['Break Location'].max()
    avg_stars = round(df['Avg Stars'].mean())
    avg_period = round(df['Period'].mean())
    avg_score = round(df['Score'].mean())
    avg_waves = round((df['Higher Wave Size'].mean() + df['Lower Wave Size'].mean())/2)
    return [break_, avg_stars, str(avg_period)+'s',str(avg_waves)+'ft', avg_score, df['Day'].values]

def create_message(df):
    summary = summarise_report(df[(df['Score'] > 5)])

    break_ = summary[0]
    stars = summary[1]
    period = summary[2]
    wave_height = summary[3] 
    score = summary[4]
    days = summary[5]

    output_str = f"""\nSurfs up at {break_}!!!\n\n
Waves are pumping at {wave_height} at {period}.
With an average star count of {stars} on MagicSeaweed, scoring {score}/10\n
Days to look at our {days}\n\n"""

    return output_str


def send_email(message):
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)

    msg = EmailMessage()
    msg.set_content(message)

    msg['Subject'] = f'Surfs Up!!!'
    msg['From'] = 'surfsupreports@gmail.com'
    msg['To'] = 'jordan.w@my.com'

    server.login('surfsupreports@gmail.com', 'surfbot123?')
    server.send_message(msg) 
    server.quit()