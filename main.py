from __future__ import print_function
import datetime
import pickle
import os.path
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from notion.client import NotionClient
from notion.collection import NotionDate
import re
import os
from os.path import join, dirname
from dotenv import load_dotenv

load_dotenv()

if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
else:
    creds = None

def authenticate():
    global creds

    ###TODO: put the name of your credentials file here (it's probably credentials.json)
    credentials_file = "credentials.json"

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        # Saves the credentials for future runs
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    main("request")

def main(request):
    global creds

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    ###TODO: setup vars
    notion_token = os.getenv('NOTION_TOKEN')
    notion_cal = os.getenv('NOTION_CALENDAR')
    timezone = os.getenv('TIMEZONE')
    # os.environ["TZ"] = os.getenv('TIMEZONE') # ensures synchronized timezone
    calendar_id = os.getenv('CALENDAR_ID')

    # Call Google Calendar
    service = build('calendar', 'v3', credentials=creds)

    events_result = service.events().list(calendarId=calendar_id, timeMin=datetime.datetime.utcnow().isoformat("T") + "Z",
    singleEvents=True, orderBy='updated').execute()

    events = events_result.get('items', [])

    for result in events:
        if 'description' not in result:
            result["description"] = ""

    google_event_list = [(event["summary"], event["id"], event["updated"],
                          event["start"], event["end"], event["description"])
                        for event in events]

    # Call the Notion API
    client = NotionClient(token_v2=notion_token)
    calendar = client.get_collection_view(notion_cal)

    notion_events = calendar.collection.get_rows()

    # Get Google Events now to create on Notion Cal

    # Reformatting the Notion Id list to fit our format of replacing the '-' with '1'
    notion_id_list = [event.id for event in notion_events]
    for i in range(len(notion_id_list)):
        notion_id_list[i] = list(notion_id_list[i])
        notion_id_list[i][8] = "1"
        notion_id_list[i][13] = "1"
        notion_id_list[i][18] = "1"
        notion_id_list[i][23] = "1"
        notion_id_list[i] = "".join(notion_id_list[i])

    for google_event in google_event_list:
        # summary: 0
        # id: 1
        # updated time: 2
        # start: 3
        # end: 4
        # description: 5


        if google_event[1] not in notion_id_list:
            print(google_event[0])
            # event has been created in gcal, add the event to notion
            # note: this only works if there only exists one view for your notion database
            notion_event = calendar.collection.add_row()
            notion_event.name = google_event[0]

            ###TODO: set your custom parameters
            notion_event.url = google_event[5]

            # Rebuilding the date the same way as before
            try:
                updated_start = re.sub(r"-[0-9]{2}:[0-9]{2}$", "", str(google_event[3]["dateTime"]).replace("T", " "))
                updated_start = datetime.datetime.strptime(updated_start[:-3], r"%Y-%m-%d %H:%M")
                new_date = NotionDate(updated_start)
                # notion_event.date = new_date
            except:
                updated_start = datetime.datetime.strptime(google_event[3]["date"], r"%Y-%m-%d")
                updated_start = datetime.date(updated_start.year, updated_start.month, updated_start.day)
                new_date = NotionDate(updated_start)
                # notion_event.date = new_date

            try:
                updated_end = re.sub(r"-[0-9]{2}:[0-9]{2}$", "", str(google_event[4]["dateTime"]).replace("T", " "))
                updated_end = datetime.datetime.strptime(updated_end[:-3], r"%Y-%m-%d %H:%M") - datetime.timedelta(minutes=1)
                new_date.end = updated_end
                notion_event.date = new_date
            except:
                updated_end = datetime.datetime.strptime(google_event[4]["date"], r"%Y-%m-%d")

                if updated_end == updated_start:
                    new_date.end = "None"
                else:
                    # this is what we want to run when an event starts and ends on different days!
                    print(f"changing end date for creating on notion cal: {notion_event.name}")
                    updated_end = (updated_end - datetime.timedelta(days=1)).date()
                    new_date.end = updated_end
                notion_event.date = new_date


    return "Done"

if __name__ == '__main__':
    if os.path.exists('token.pickle'):
        main("request")
    else:
        authenticate()
