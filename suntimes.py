import ephem
import pytz
import copy
from datetime import datetime, timedelta
import numpy as np

import timezone


def is_dst(zonename):
    tz = pytz.timezone(zonename)
    now = pytz.utc.localize(datetime.utcnow())
    return now.astimezone(tz).dst() != timedelta(0)

# set up relevant time zones
utc = pytz.timezone('UTC')
chile = pytz.timezone('America/Santiago')
pacific = pytz.timezone('US/Pacific')
eastern = pytz.timezone('US/Eastern')

favorite_zones = [chile, eastern, pacific]
favorite_labels = ['Chile', 'EDT', 'PDT'] if is_dst('US/Eastern') else ['Chile', 'EST', 'PST']

#set up for ephem calcs:
def _gemini():
    gemini = ephem.Observer()
    gemini.lat='-30:14:26.7'
    gemini.lon='-70:44:12.006'
    gemini.elevation=2722
    gemini.temp=0
    gemini.pressure=726
    gemini.horizon = '-1:45'  # earth's horizon is below local horizontal if you're on a mountain.
    return gemini

gemsouth = _gemini()
gemsouth_twi = _gemini()
gemsouth_twi.horizon='-12'

def delta_to_now(sometime):
    deltat = (sometime - ephem.now()) # in days
    delta_hour = int(np.floor(deltat*24))
    delta_min = int(np.round((deltat-delta_hour/24)*24*60))
    return delta_hour,delta_min


def format_time(dt, tz):
    tmp = dt.astimezone(tz).strftime('%I:%M %p')
    return tmp[1:] if tmp[0]=='0' else tmp # drop leading zeros

def utc_to_multizone(date_utc):
    if date_utc.tzinfo is None: # assume input is UTC if given a naiive datetime
        date_utc = utc.localize(date_utc)
    times = [format_time(date_utc,tz)+" "+label for tz, label in zip(favorite_zones, favorite_labels)]
    return ", ".join(times)


def sunrise_time_response():
    gemsouth.date = ephem.now()
    gemsouth_twi.date = ephem.now()

    risetime = gemsouth.next_rising(ephem.Sun())
    twitime = gemsouth_twi.next_rising(ephem.Sun(), use_center=True)
    return ("Next sunrise at Gemini South is {}, which is {} h {} m from now.".format(utc_to_multizone(risetime.datetime()), *delta_to_now(risetime)) +
            "\nAnd 12 deg twilight is at {}".format(utc_to_multizone(twitime.datetime()) ) )



def sunset_time_response():
    gemsouth.date = ephem.now()
    gemsouth_twi.date = ephem.now()
    settime = gemsouth.next_setting(ephem.Sun())

    twitime = gemsouth_twi.next_setting(ephem.Sun(), use_center=True)
    return ("Next sunset at Gemini South is {}, which is {} h {} m from now.".format(utc_to_multizone(settime.datetime()), *delta_to_now(settime)) +
            "\nAnd 12 deg twilight is at {}".format(utc_to_multizone(twitime.datetime()) ) )


