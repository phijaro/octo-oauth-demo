# Octopus Energy OAuth Enrolment Demo

This app is intended as a minimal demo of how an external web
application can integrate with the Octopus Energy OAuth2/OpenID
Connect server, and invite Octopus customers to give the app’s owner
permission to access the Octopus API site on their behalf.

## Prerequisites

The app requires a [Python](https://www.python.org/) environment to
run.  It has various Python code dependencies which are listed in
`requirements.in` — pinned versions of these (and the dependencies
they require in their turn) are specified in `requirements.txt`.

Example code is included to send refresh tokens by email.  If this
code is to be used, the app will need an SMTP server to connect to.
This can be specified in the config file.

## Configuration

In order to set the application up, copy the provided
`oauth-demo-config.cfg.example` file to a file named
`oauth-demo-config.cfg` in the repo root directory, and fill in the
values.  The comments in the example config file describe what each
setting does.

## Running the app

Once the Python environment is set up, the app can be run for local
testing by calling

```
$ flask run
```

in the app root directory.  Running the app for real is beyond the
scope of this document, but some pointers are available at
https://flask.palletsprojects.com/en/3.0.x/deploying/
