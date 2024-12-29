# Work_ID

Prompt:Use the latest flask and Web 2.0 tech to create a single page and very pretty CRUD application that is called "Work-ID". All data should be stored in redis

The primary goal of this application is maintain a list of projects/work records. Each record has an id based on a certain pattern from env var WORK_ID_PATTERN. 
Each letter X is supposed to be replaced with a random capital alphanumeric letter or a number. Please do not use O and 0 as they can be mixed up. 
In addition to the ID the record should have a title (about 100 chars) and a description (< 1024 chars), a creation timestamp, start date and end date, a time zone (default is current). All dates should be stored as UTC times and be displayed in current times. and Boolean flag whether it's active or not and a creator email address which is basically an email address identity. 
The creator email address entered shall be stored as a cookie and used as the default identity for subsequent records. 
There are also addional single select and multi select widgets. These widgets are fed by environment variables for example this may be a config: 

META_SEL_WorkType=Generic,Internal Project,Grant Project,Operations,Pilot
META_MSEL_RequiredApps=Teams,Sharepoint,Filesystem,HPC

META_MSEL_RequiredApps is an example for a  multi select widget with 4 entries that is titled RequiredApps that can all be selected and the selected items will be tab separated in the stored field. META_SEL_WorkType is an example for a widget titled WorkType that allows only one selection. 

the single page app has 2 parts, the first part is a form that defaults to a new record with a new unique not yet saved work-id and the second is a list of records created by this identity shown in reverse order of timestamp created. This list should show at least the work-id, the title, and the META fields. If I click on a previous record, it will become the active record where i can change all fields except for the ID field and the creation timestamp 

also create a search option where it searches the entire database with all records, there must be a toggle for searching all records and only my records, I can only edit my records 

# how many IDs do i get if i use XX-XX as an ID

Alphanumeric Set (A-Z and 0-9):
Total originally: 26 letters + 10 digits = 36 characters
   After removing O and 0: 34 characters

Now, with 34 possible characters for each position in a 4-character ID:

34^4=1,336,336 combinations
