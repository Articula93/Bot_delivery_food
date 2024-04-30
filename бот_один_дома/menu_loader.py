from datetime import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class Food:
    def __init__(self, id, data):
        self.id=id
        self.clear_data(data)
        self.photo = data[0]
        self.days = data[1]
        self.type = data[2]
        self.name = data[3]
        self.cal = None
        self.price = 0
        self.weight = 0
        if len(data)>=5:
            self.price = float(data[4])
        if len(data)>=6:
            self.weight = str(data[5])
        if len(data)>=7:
            self.cal=str(data[6])
        self.composition = None
        if len(data)>=8:
            self.composition = str(data[7])   
        self.p = None
        self.t = None
        self.c = None
        if len(data) >=9:
            self.p = str(data[8])
        if len(data) >=10:
            self.t = str(data[9])
        if len(data) >=11:
            self.c = str(data[10])


    def clear_data(self, data):
        for i in range(len(data)):
            data[i]=data[i].strip().lower()

    def __repr__(self):
        return f"{self.days} {self.type} {self.name} {self.price} {self.cal} {self.composition} {self.p}/{self.t}/{self.c}"

class FoodLoader:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    day_week = ["пн","вт","ср","чт","пт","сб","вс"]

    def __init__(self,  doc_id, range_cell, token_file = 'token.json', credentials_file = 'credentials.json'):
        self.doc_id = doc_id
        self.range_cell = range_cell
        self.token_file = token_file
        self.credentials_file =  credentials_file
        self.creds = None
        self.number_weekday = datetime.now().weekday()
        self.menu = {}
        self.error = None
        self.columns_day = 1
    
    def get_or_refresh_credentials(self):
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)

        if not self.creds  or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())

    def parsing_data(self, values, skip_header):
        if skip_header:
            values = values[1:]
        for ind, row in enumerate(values):
            week_days_row = row[self.columns_day].strip().lower()
            if self.day_week[self.number_weekday] in week_days_row:
                id = ind+1
                food = Food(id, row)
                self.menu[id] = food
                if food.type in self.menu:
                    self.menu[food.type].append(food)
                else:
                    self.menu[food.type]=[food]


    def load_menu(self, skip_header = True):
        try:
            self.error = None
            if not self.creds:
                self.get_or_refresh_credentials()
                
            service = build('sheets', 'v4', credentials=self.creds)
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.doc_id,
                                        range=self.range_cell).execute()
            values = result.get('values', [])

            if not values:
                self.error = 'No data found'
                return
            
            self.parsing_data(values, skip_header)

        except Exception as err:
            self.error = err
        

    


def main():
    SAMPLE_SPREADSHEET_ID = '19EpIaw-xwYts4B4Ixrv2B-Mx6ln9Hloo1iVlZCaN6dY'
    SAMPLE_RANGE_NAME = 'A1:AB1000'
    fl  = FoodLoader(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
    fl.load_menu()
    if not fl.error:
        print(fl.menu)
    else:
        print(fl.error)


if __name__ == '__main__':
    main()