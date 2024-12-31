# Flask Template 

A template for a modern CRUD app using the latest Flask features 

## LLM Prompt 

Write me the most ultramodern flask app that you can imagine. It should look clean and pretty. Use Flask version version 3.1.0 or newer. It is a single page CRUD App using the latest HTML5, bootstrap 5.3, javascript (static/js/main.js and static/css/styles.css), blueprints and all the bells and whistles. 
It stores all info in Redis6 as JSON structures (REDIS_HOST, REDIS_PORT and REDIS_DB are defined as environment vars in .env). 
The app should work also on a cell phone and there should be 2 rest API functions /api/records that should give a simple list of record IDs and and /api/record/<record_id> that gives the entire json structure of a single record. There should be a search field that triggers a full text search over the json structure in redis after confirming the search terms with enter. Use redis searchas much as possible. A few more requirements: 

 1. Implement Flask blueprints for better code organization
 2. Add type hints throughout the code
 3. Move database connection to separate module database.py
 4. Add proper error handling with custom error pages
 5. Use Flask-CORS for cross-origin support
 6. Implement factory pattern with create_app()
 7. Separate config.py functions
 8. Use modern response handling with make_response
 9. Improve code organization and maintainability

--  

 Prompt Specifics here 

--


## aider command

start `aider.chat` with this command line:

```
alias aider='aider --dark-mode --vim --cache-prompts'

aider app.py database.py config.py blueprints/* templates/errors/* templates/base.html templates/index.html static/css/* static/js/*
```
