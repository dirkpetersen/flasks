# Work_ID


## Chat prompt 

Prompt:Use the latest flask and Web 2.0 tech to create a single page and very pretty CRUD application that is called "Work-ID". All data should be stored in redis

The primary goal of this application is maintain a list of projects/work records. Each record has an id based on a certain pattern from env var WORK_ID_PATTERN. 
Each letter X is supposed to be replaced with a random capital alphanumeric letter or a number. Please do not use O and 0 as they can be mixed up. 
In addition to the ID the record should have a title (about 100 chars) and a description (< 1024 chars), a creation timestamp, start date and end date, a time zone (default is current). All dates should be stored as UTC times and be displayed in current times. and Boolean flag whether it's active or not and a creator email address which is basically an email address identity. 
The creator email address entered shall be stored as a cookie and used as the default identity for subsequent records. 
There are also addional single select and multi select widgets. These widgets are fed by environment variables.  for example this may be a config: 

META_SEL_1=Work Type:Generic,Internal Project,Grant Project,Department,PI-Team,Pilot
META_MSEL_2=Required Apps:Teams,Sharepoint,Filesystem,HPC
META_MSEL_3=Organization:oregonstate.edu,uoregon.edu,ohsu.edu

Just parse all the environment variables that start META_SEL_ and META_MSEL_ . Then get the value and fromt that extract the key which will be used as id in forms and as key a field iin the json record in redis.. The key is the which is the part of the value of the env var that is left of the: sign. Everything right of the : sign is a comma separated list of values to select from. convert this new key to lower case and replace spaces with underscores and use that as form_id as well as key for the this redis database. 

the single page app has 2 parts, the first part is a form that defaults to a new record with a new unique not yet saved work-id and the second is a list of records created by this identity shown in reverse order of timestamp created. This list should show at least the work-id, the title, and the META fields. If I click on a previous record, it will become the active record where i can change all fields except for the ID field and the creation timestamp 

also create a search option where it searches the entire database with all records, there must be a toggle for searching all records and only my records, I can only edit my records 



## how many IDs do i get if i use XX-XX as an ID

Alphanumeric Set (A-Z and 0-9):
Total originally: 26 letters + 10 digits = 36 characters
   After removing O and 0: 34 characters

Now, with 34 possible characters for each position in a 4-character ID:

34^4=1,336,336 combinations

## changing a key name in a json recond in redis

write lua code `redis-field-renamer.lua`, for example, if you want to rename key creator_email to creator_id

```lua
-- Scan all keys matching your desired pattern (e.g., all work:* keys)
local cursor = "0"
repeat
    local result = redis.call("SCAN", cursor, "MATCH", "work:*", "COUNT", 100)
    cursor = result[1]
    local keys = result[2]
    for _, key in ipairs(keys) do
        local value = redis.call("GET", key)
        if value then
            -- Parse the JSON value
            local json = cjson.decode(value)
            if json["creator_email"] then
                json["creator_id"] = json["creator_email"]
                json["creator_email"] = nil
                -- Save the updated JSON back to Redis
                redis.call("SET", key, cjson.encode(json))
            end
        end
    end
until cursor == "0"

```

and start 

```bash
redis-cli --eval redis-field-renamer.lua
```

## modern flask features:

 1 Implement Flask blueprints for better code organization
 2 Add type hints throughout the code
 3 Move database connection to separate module
 4 Add proper error handling with custom error pages
 5 Use Flask-CORS for cross-origin support
 6 Implement factory pattern with create_app()
 7 Better SSL context handling
 8 Separate utility functions
 9 Use modern response handling with make_response
 10 Improve code organization and maintainability