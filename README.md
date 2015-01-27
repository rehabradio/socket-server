# Python Websockets for rehabradio

Basic Flask-Sockets app for reporting events from a redis server

Platform
--------

* Platform: Heroku
* Language: Python 2.7
* Framework: Flask


Setup
=================

This app uses heroku foreman to load in some environmental variables, located in a `.env` file.

	DEBUG=True|False
	REDISCLOUD_URL="redis:[url]:[port]:[db]"
	SECRET_KEY=[random string]
    GOOGLE_WHITE_LISTED_DOMAINS=[comma seperated list of email domains that can access the api]


Running server
=================

Use foreman to start the server with:

	foreman start

You can vists the running application [http://localhost:5000](http://localhost:5000)
