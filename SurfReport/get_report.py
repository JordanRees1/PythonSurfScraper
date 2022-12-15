# Get Surf Report 
# Given a URL get the surf report details
import re
import os
import requests
import pandas as pd
import telepot as tele
from io import StringIO
from bs4 import BeautifulSoup
from datetime import date, timedelta
from azure.storage.blob import BlobServiceClient

# Current harcoded to our group. TODO make this dynamic
token = '2023059476:AAHmKVHPT_lUz55soRzBSysEJsVZifE2fgY'
chat_id = -736190449

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


# Get wave energy from surf forecast
def get_wave_energy(soup):
    count = 0 
    day = 1
    date_  = date.today()
    master = []
    
    for td in soup.find_all('td', class_=f'forecast-table__cell forecast-table-energy__cell'):
        count += 1
        
        if count == 1:
            wave_energy = int(td.text) 
        else:
            wave_energy += int(td.text)
              
        # increment day when count is multiple of 7 
        if count % 7 == 0:
            if day == 1:
                wave_energy = round(wave_energy/6)
            else:
                wave_energy = round(wave_energy/7)
                
            master.append({'Day':date_.strftime("%A"), 'Date':date_.strftime("%d/%m"), 'Energy':wave_energy})
            
            day += 1
            date_ += timedelta(days=1)
            
        # Don't need the eigth day as MSW only does 7
        if day == 8:
            break
        
    return pd.DataFrame(master)


# Generic SF parser - yet to be used but can be implimented to extract any other values
def surf_forecast_parser(soup, tag, class_, title):
    count = 0 
    day = 1
    date_  = date.today()
    master = []
    
    for td in soup.find_all(tag, class_=class_):
        count += 1
        
        print(td)
        
        master.append({'Day':date_.strftime("%A"), 'Date':date_.strftime("%d/%m"), title:td.text})
        
        # increment day when count is multiple of 7 
        if count % 14 == 0:
            day += 1
            date_ += timedelta(days=1)
            
        # Don't need the eigth day as MSW only does 7
        if day == 8:
            break
        
    return pd.DataFrame(master)


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


def score_report(df, threshold):
    
    if threshold == 'low':
        df['Score'] = 0

        df.loc[df['Avg Stars'] >= 1, 'Score'] = 2
        df.loc[df['Avg Stars'] >= 2, 'Score'] = 3
        df.loc[df['Avg Stars'] >= 3, 'Score'] = 5

        df.loc[df['Period'] > 9, 'Score'] += 0.5
        df.loc[df['Period'] > 11, 'Score'] += 1
        df.loc[df['Period'] > 14, 'Score'] += 2

        df.loc[df['Wind Direction'] == 'Offshore', 'Score'] += 2
        df.loc[df['Wind Direction'] == 'Onshore', 'Score'] -= 1.5

        df.loc[df['Wind Strength'] == 'Light', 'Score'] += 1.5
        df.loc[df['Wind Strength'] == 'Strong', 'Score'] -= 0.5
        df.loc[df['Wind Strength'] == 'Very Strong', 'Score'] -= 2

        df.loc[df['Lower Wave Size'] >= 3, 'Score'] += 1
        df.loc[df['Lower Wave Size'] >= 4, 'Score'] += 2
        df.loc[df['Higher Wave Size'] >= 4.5, 'Score'] += 1
        df.loc[df['Higher Wave Size'] >= 6, 'Score'] += 2
        
        df.loc[df['Energy'] >= 150, 'Score'] += 1
        df.loc[df['Energy'] >= 250, 'Score'] += 2
        df.loc[df['Energy'] < 100, 'Score'] -= 7.5
        

        df.loc[df['Score'] > 10, 'Score'] = 10
        df.loc[df['Score'] < 0, 'Score'] = 0
        
    else:
        df['Score'] = 0

        df.loc[df['Avg Stars'] >= 2, 'Score'] = 2
        df.loc[df['Avg Stars'] >= 3, 'Score'] = 3
        df.loc[df['Avg Stars'] >= 4, 'Score'] = 6

        df.loc[df['Period'] > 10, 'Score'] += 0.5
        df.loc[df['Period'] > 14, 'Score'] += 1
        df.loc[df['Period'] > 18, 'Score'] += 2

        df.loc[df['Wind Direction'] == 'Offshore', 'Score'] += 2
        df.loc[df['Wind Direction'] == 'Onshore', 'Score'] -= 1.5

        df.loc[df['Wind Strength'] == 'Light', 'Score'] += 1
        df.loc[df['Wind Strength'] == 'Strong', 'Score'] -= 0.5
        df.loc[df['Wind Strength'] == 'Very Strong', 'Score'] -= 1

        df.loc[df['Lower Wave Size'] > 4, 'Score'] += 1
        df.loc[df['Lower Wave Size'] > 5, 'Score'] += 2
        df.loc[df['Higher Wave Size'] > 5, 'Score'] += 1
        df.loc[df['Higher Wave Size'] > 8, 'Score'] += 2
        
        df.loc[df['Energy'] >= 200, 'Score'] += 1
        df.loc[df['Energy'] >= 400, 'Score'] += 2
        df.loc[df['Energy'] < 150, 'Score'] -= 5
        

        df.loc[df['Score'] > 10, 'Score'] = 10
        df.loc[df['Score'] < 0, 'Score'] = 0

    return df


# Returns a list of elements: Break Name, Stars, Period, Wave Height, Score and Days (list)
def summarise_report(df):
    break_ = df['Break Location'].max()
    if df['Avg Stars'].mean == 0:
        avg_stars = 0
    else:
        avg_stars = round(df['Avg Stars'].mean())
    avg_period = round(df['Period'].mean())
    avg_score = round(df['Score'].mean())
    avg_waves = round((df['Higher Wave Size'].mean() + df['Lower Wave Size'].mean())/2)
    return [break_, avg_stars, str(avg_period)+'s',str(avg_waves)+'ft', avg_score, df['Day'].values]


# Returns the site URL from dataframe in lake for a given break and site
def get_break_values(df, break_name, site):
    return df[site].loc[df['break'] == break_name].values[0]


# initalise telegram bot
def initalise_bot(token):
    bot = tele.Bot(token)
    return bot


# send a telegram message to a chat id
def send_msg(bot, chat_id, msg):
    bot.sendMessage(chat_id, msg)
    return 1


# Format message for signal
def format_msg(df):
    df = df.loc[df['Score'] > 5]

    msg = f"{df['Break Location'].max()} \n"
    for i in range(len(df)):
        msg += f"\n{df['Day'][i]} {df['Date'][i]}\n\
Size: {round((df['Higher Wave Size'][i].mean() + df['Lower Wave Size'][i].mean())/2)}ft\n\
Energy: {round(df['Energy'][i].mean())}\n\
{df['Wind Strength'][i]} {df['Wind Direction'][i]} Wind\n"    
    return msg

# TODO: Function to accept threshold and send signal message if score is above threshold


# Gets a dataframe containing all break values stored in the lake CSV file.
def get_break_urls():
    account_name = 'jordanslake'
    account_key = os.environ['lakeKey']

    # Azure blob connection string for CSV 
    conn_str = f'DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key}==;EndpointSuffix=core.windows.net'

    blob_service_client = BlobServiceClient.from_connection_string(conn_str)

    blob_client = blob_service_client.get_blob_client(container='surf-report', blob='breaks.csv')

    try:
        storedData = blob_client.download_blob()
        df = pd.read_csv(StringIO(storedData.content_as_text()))

        # If no blob exists create a new one - ErrorCode:BlobNotFound
    except:
        # create blank dataframe with columns
        df = pd.DataFrame(columns=['break', 'msw', 'surf_forecast'])

    return df