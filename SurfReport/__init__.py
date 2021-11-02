import logging
import pandas as pd
from . import get_report as surf
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    spots = req.headers.get('spots')
    spots = spots.split(',')

    logging.info(spots)

    if not spots:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            spots = req_body.get('spots')


    for spot in spots:
        soup = surf.get_webpage(spot)

        # Get surf location from page title
        surf_break = soup.findAll('h1', class_='nomargin page-title')[0].text.split('Surf')[0]

        # Create dataframe from dict and join
        df = pd.DataFrame(surf.get_day_stars(soup, 'active'))
        df['Break Location'] = surf_break
        df2 = pd.DataFrame(surf.get_day_stars(soup, 'inactive'))
        df_final = df.merge(df2)

        # Get average rating for each day (semi star = half)
        df_final['Total Stars'] = (df_final['inactive Star Count'] / 2) + df_final['active Star Count']
        df_final['Avg Stars'] = round(df_final['Total Stars'] / 8, 2)
        
        df = pd.DataFrame(surf.get_size(soup))
        df_final = df_final.merge(df)
        df = pd.DataFrame(surf.get_swell_direction(soup))
        df_final = df_final.merge(df)
        df = pd.DataFrame(surf.get_period(soup))
        df_final = df_final.merge(df)
        df = pd.DataFrame(surf.get_wind_direction(soup))
        df_final = df_final.merge(df)

        df_final = df_final.drop(columns={'Total Stars', 'inactive Star Count', 'active Star Count'})
        output = surf.format_date(df_final)
        
        scored = surf.score_report(output)

        logging.info(scored['Avg Stars'])
        logging.info(scored['Score'])
    
        if len(scored[scored['Score'] > 5]) > 0:
            surf.send_email(surf.create_message(scored))
        
    
    return func.HttpResponse(f"Reports checked.")
