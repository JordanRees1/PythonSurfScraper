import logging
import pandas as pd
from . import get_report as surf
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    break_name = req.headers.get('break')
    threshold = req.headers.get('threshold')
    chat_id = req.headers.get('chat_id')

    if not break_name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            break_name = req_body.get('break')

    if not threshold:
        threshold = 'low'

    if not chat_id:
        chat_id = surf.chat_id

    logging.info(break_name)
    logging.info(threshold)

    df = surf.get_break_urls()

    logging.info("getting break values from data lake file")

    try:
        msw_link = surf.get_break_values(df=df, break_name=break_name, site='msw')
        sf_link = surf.get_break_values(df=df, break_name=break_name, site='surf_forecast')
    except:
        return func.HttpResponse(
            f"Cannot find {break_name}, please add this to the file in the format: break_name, msw_url, surf_forcast_url",
            status_code=404)

    logging.info("Creating telegram bot")

    # Create bot
    bot = surf.initalise_bot(surf.token)

    logging.info("Bot successfuly created")

    logging.info("Getting webpage")

    # Get MSW webpage
    soup = surf.get_webpage(msw_link)

    logging.info("Finding break")

    # Get surf location from page title
    surf_break = soup.findAll('h1', class_='nomargin page-title')[0].text.split('Surf')[0]

    logging.info("Getting break info...")

    # Create dataframe from dict and join
    df = pd.DataFrame(surf.get_day_stars(soup, 'active'))
    df['Break Location'] = surf_break
    df2 = pd.DataFrame(surf.get_day_stars(soup, 'inactive'))
    df_temp = df.merge(df2)

    # Get average rating for each day (semi star = half)
    df_temp['Total Stars'] = (df_temp['inactive Star Count'] / 2) + df_temp['active Star Count']
    df_temp['Avg Stars'] = round(df_temp['Total Stars'] / 8, 2)

    df = pd.DataFrame(surf.get_size(soup))
    df_temp = df_temp.merge(df)
    df = pd.DataFrame(surf.get_swell_direction(soup))
    df_temp = df_temp.merge(df)
    df = pd.DataFrame(surf.get_period(soup))
    df_temp = df_temp.merge(df)
    df = pd.DataFrame(surf.get_wind_direction(soup))
    df_temp = df_temp.merge(df)
    df = pd.DataFrame(surf.get_wind_speed(soup))
    df_temp = df_temp.merge(df)


    df_temp = df_temp.drop(columns={'Total Stars', 'inactive Star Count', 'active Star Count'})

    logging.info("Formatting MSW results...")

    output = surf.format_date(df_temp)

    logging.info("Getting Surf Forcast data")

    # Get the HTML for the corresponding surf forecast url
    sf_soup = surf.get_webpage(sf_link)

    # Get the wave energy from the surf forecast page
    energy = surf.get_wave_energy(sf_soup)

    logging.info("Meging...")

    output = output.merge(energy)

    logging.info("Scoring...")

    scored = surf.score_report(df=output, threshold=threshold)

    logging.info("Sending to telegram.")
    
    # Send message to telegram   
    message = surf.format_msg(scored)
    surf.send_msg(bot, chat_id, message)

    logging.info("Message sent.")
    
    return func.HttpResponse(f"Report checked {break_name} and successfuly sent to telegram.")
