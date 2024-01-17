import requests
import json
import time
from dateutil.parser import *
from datetime import datetime as dt
import threading

# Use command createCA for creation of capture agent. Has to be done daily.

# Works
def getCutoff():
    # calculate the offset of now + 1 week
    cutoff = (round(time.time()) + 7*24*60*60)*1000
    
    print("Cutoff =",cutoff)
    return cutoff

# Works fine for now
# TODO: test for all possible presets 
def setPreset(preset, camera, verbose=False):
    if 0 <= preset and preset < 101:
        if preset < 10:
            preset = "0" + str(preset)
        url = camera + '/cgi-bin/aw_ptz?cmd=%23R' + str(preset) + '&res=1'
        if verbose:
            print("URL:" + url)
    else:
        print("Could not use the specified preset number, because it is out of range.\nThe Range is from 0 to 100 (including borders)")
        return
    
    # TODO: Actually set preset with request method
    code = requests.get(url, auth=("admin", "PASS"))
    return code

def printPlanned(cal):
    events = []
    for event in cal:
        data = event['data']
        print("\nEvent Name: ", data['agentConfig']['event.title'])
        print("Start: ", data['startDate'])
        print("End Date: ", data['endDate'])

        start = int(dt.strptime(str(parse(data['startDate'], dayfirst=True)),'%Y-%m-%d %H:%M:%S').timestamp() * 1000)
        end = int(dt.strptime(str(parse(data['endDate'], dayfirst=True)),'%Y-%m-%d %H:%M:%S').timestamp() * 1000)
        
        print(start, end, end-start)

        events.append((data['agentConfig']['event.title'], start, end))
    return events

def getCalendar(agentId, cutoff, verbose=False):
    url = "https://develop.opencast.org/recordings/calendar.json?agentid=" + str(agentId) + "&cutoff=" + str(cutoff)
    print("REQUEST:",url)

    calendar = requests.get(url, auth=("admin", "opencast"))
    if verbose:
        print("STATUS:",calendar.status_code)
        print("JSON:", calendar.json())

    events = printPlanned(calendar.json())

    return events, calendar.status_code, calendar

def loadConfig(filename):
    with open(filename, "r") as file:
        agents = json.load(file)
        print(type(agents), agents)
        return agents

def loop(ca, cam):
    # Used for fetching the calendar every 2 days
    days = 2
    # fetch planned recordings, events are just tuples of (name, start, end)
    # calendar gets returned as well, probably don't need it after all
    events, _, _ = getCalendar(ca, getCutoff())
    last_fetched = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000

    # reverse so pop returns the next event
    events = sorted(events, key=lambda x: x[1], reverse=True)
    next_event = events.pop()

    try:
        now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000
    except:
        time.sleep(0.000001)
        now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000

    print("Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")

    # Somewhere in this loop, I have to fetch the next events
    while True:
        try:
            now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000
        except:
            time.sleep(0.000001)
            now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000

        if (next_event[1] - now)/1000 == 3:
            print("3...")
        elif (next_event[1] - now)/1000 == 2:
            print("2...")
        elif (next_event[1] - now)/1000 == 1:
            print("1...")


        if now == next_event[1]:
            print("Event \'" + next_event[0] + "\' has started!")

            # Move to recording preset
            print("Move to Preset 1 for recording...")
            _ = setPreset(1, cam)
        elif now == next_event[2]:
            print("Event \'" + next_event[0] + "\' has ended!")

            # Return to home preset
            print("Return to Preset \'Home\'...")
            _ = setPreset(0, cam)
            next_event = events.pop()
            print("Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")


            # 1 day has 86400 seconds, so it should be 86400 * 1000 (for milliseconds) and this * days to fetch the plan every two days (or later if needed)  
        if now - last_fetched > (86400000*days):
            print(now, last_fetched, now-last_fetched)
            events, response, _ = getCalendar(ca, getCutoff())
            if int(response) == 200:
                days = 2
                last_fetched = now
                events = sorted(events, key=lambda x: x[1], reverse=True)
                next_event = events.pop()
                print("Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")
            else:
                print("Fetching the calendar returned something else than Code 200; Response: ", response)

                # Try fetching again in 12 hours 
                days += 0.5

                if days == 6:
                    # If the plan could not be fetched in the last 5.5 days, print a warining because there might be some bigger error 
                    print("[WARNING] The calendar coudn't be fetched in the last 5 days. Will try again tomorrow.")
        time.sleep(1.0)

def main():
    agents = loadConfig("./config.json")


    threads = list()
    for ca in list(agents.keys()):
        cam = agents[ca]
        print(ca, cam)
        x = threading.Thread(target=loop(ca, cam))
        threads.append(x)
        x.start()
    
    for index, thread in enumerate(threads):
        thread.join()
    
    # Set preset to the according number [0, 100]
    # Also set the camera when the recording should be started
    # curl -i --max-time 5 -u 'admin:PASS' 'http://camera-42-209.virtuos.uni-osnabrueck.de/cgi-bin/aw_ptz?cmd=%23R< Preset_No >&res=1'
    # --> Done with setPreset, but the max-time arg is not passed yet


if __name__ == "__main__":
    main()