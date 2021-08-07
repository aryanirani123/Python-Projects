import gspread

from oauth2client.service_account import ServiceAccountCredentials

from pprint import pprint

scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json",scope)
client = gspread.authorize(creds)

sheet = client.open("Students Marks ").sheet1



#Getting data from the sheet
data = sheet.get_all_records()

print(data)


#Get the specific row, column and cell from the sheet

row = sheet.row_values(3)
col = sheet.col_values(3)
cell = sheet.cell(1,2).value

pprint(cell)

#Inserting data in your sheet 

insertRow = ["Zayn","Malik",12]
sheet.insert_row(insertRow,7)
print("The row has been added")
sheet.delete_row(2)
print("The row has been deleted")
