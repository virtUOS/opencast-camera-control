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
    
    #print("Cutoff =",cutoff)
    return cutoff

# Works fine for now
# TODO: test for all possible presets 
def setPreset(preset, camera, manufacturer, verbose=False):
    if 0 <= preset and preset < 101:
        if preset < 10:
            preset = "0" + str(preset)
    else:
        print("Could not use the specified preset number, because it is out of range.\nThe Range is from 0 to 100 (including borders)")
        return

    print(camera, manufacturer)
    code = -1    
    if manufacturer == "panasonic":
        print("PANASONIC")
        url = camera + '/cgi-bin/aw_ptz?cmd=%23R' + str(preset) + '&res=1'
        if verbose:
            print("URL:" + url)
        code = requests.get(url, auth=("<user>", "<password>"))
    elif manufacturer == "sony":
        print("SONY")
        preset = int(preset)
        preset += 1
        # Presets start at 1 for Sony cameras
        url = camera + '/command/presetposition.cgi?PresetCall=' + str(preset)
        if verbose:
            print("URL:" + url)
        # TODO: This doesn't work so far and I don't know why. Getting response 401 
        code = requests.get(url, auth=("<user>", "<password>"), headers={"referer": camera + "/index.html?lang=en"})
        print(code)
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
    print("[" + agentId + "] REQUEST:",url)

    calendar = requests.get(url, auth=("admin", "opencast"))
    if verbose:
        print("STATUS:",calendar.status_code)
        print("JSON:", calendar.json())

    events = printPlanned(calendar.json())

    return events, calendar.status_code, calendar

def loadConfig(filename):
    with open(filename, "r") as file:
        agents = json.load(file)
        #print(type(agents), agents)
        return agents

def loop(agentID, url, manufacturer):
    # Used for fetching the calendar every 2 days
    days = 2
    # Two nested while True loops so I can break out of the inner one if no further events are scheduled
    while True:
        events, _, _ = getCalendar(agentID, getCutoff())

        #print(len(events))
        if len(events) != 0:

            last_fetched = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000

            # reverse so pop returns the next event
            events = sorted(events, key=lambda x: x[1], reverse=True)
            try:
                next_event = events.pop()
                now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000
                print("[" + agentID + "] Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")
            except IndexError:
                print("[" + agentID + "] Currently no further events scheduled, will check again in 10 minutes...")
                # This case should never happen because I check that before
            except:
                time.sleep(0.000001)
                now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000
                print("[" + agentID + "] Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")

            while True:
                try:
                    now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000
                except:
                    time.sleep(0.000001)
                    now = int(dt.strptime(str(parse(str(dt.now()))),'%Y-%m-%d %H:%M:%S.%f').timestamp()) * 1000

                if (next_event[1] - now)/1000 == 3:
                    print("[" + agentID + "] 3...")
                elif (next_event[1] - now)/1000 == 2:
                    print("[" + agentID + "] 2...")
                elif (next_event[1] - now)/1000 == 1:
                    print("[" + agentID + "] 1...")


                if now == next_event[1]:
                    print("[" + agentID + "] Event \'" + next_event[0] + "\' has started!")

                    # Move to recording preset
                    print("[" + agentID + "] Move to Preset 1 for recording...")
                    _ = setPreset(1, url, manufacturer, True)
                elif now == next_event[2]:
                    print("[" + agentID + "] Event \'" + next_event[0] + "\' has ended!")

                    # Return to home preset
                    print("[" + agentID + "] Return to Preset \'Home\'...")
                    _ = setPreset(0, url, manufacturer, True)
                    try:
                        next_event = events.pop()
                        print("[" + agentID + "] Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")
                    except:
                        print("[" + agentID + "] Currently no further events scheduled, will check again in 10 minutes...")
                        # Just for debugging, remove soon and replace with handling empty calendars
                        break

                    # 1 day has 86400 seconds, so it should be 86400 * 1000 (for milliseconds) and this * days to fetch the plan every two days (or later if needed)  
                if now - last_fetched > (86400000*days):
                    print(now, last_fetched, now-last_fetched)
                    events, response, _ = getCalendar(agentID, getCutoff())
                    if int(response) == 200:
                        days = 0.5
                        last_fetched = now
                        events = sorted(events, key=lambda x: x[1], reverse=True)
                        try:
                            next_event = events.pop()
                            print("[" + agentID + "] Next Planned Event is \'" + next_event[0]+"\' in " + str((next_event[1] - now)/1000) + " seconds")
                        except IndexError:
                            print("[" + agentID + "] Currently no further events scheduled, will check again in 10 minutes...")
                            # Just for debugging, remove soon and replace with handling empty calendars
                            #return
                            break
                    else:
                        print("[" + agentID + "] Fetching the calendar returned something else than Code 200; Response: ", response)

                        # Try fetching again in 12 hours 
                        days += 0.5

                    if days == 6:
                        # If the plan could not be fetched in the last 5.5 days, print a warining because there might be some bigger error 
                        print("[" + agentID + "] >>>WARNING<<< The calendar coudn't be fetched in the last 5 days. Will try again tomorrow.")
                time.sleep(1.0)
        else:
            print("[" + agentID + "] Currently no further events scheduled, will check again in 10 minutes...")
            time.sleep(600)
    


def main():
    cameras = loadConfig("./config_multipleTypes.json")

    for agentID in cameras.keys():
        print(cameras[agentID])


    threads = list()
    for agentID in list(cameras.keys()):
        url, manufacturer = cameras[agentID].values()

        print(agentID, url, manufacturer)

        print("Starting Thread for ", agentID ," @ ", url)
        x = threading.Thread(target=loop, args=(agentID, url, manufacturer))
        threads.append(x)
        x.start()
    
    # Don't need that I think. Should implement restarting of a thread if function fails for some reason
    for index, thread in enumerate(threads):
        thread.join()


if __name__ == "__main__":
    main()