<p align="center">
  <img align="center" src="sabc/media/profile_pics/default.jpg">
</p>

[![CodeQL](https://github.com/envasquez/SABC/actions/workflows/codeql-analysis.yml/badge.svg?branch=master)](https://github.com/envasquez/SABC/actions/workflows/codeql-analysis.yml)
[![Django CI](https://github.com/envasquez/SABC/actions/workflows/django.yml/badge.svg)](https://github.com/envasquez/SABC/actions/workflows/django.yml)
[![Pylint](https://github.com/envasquez/SABC/actions/workflows/pylint.yml/badge.svg)](https://github.com/envasquez/SABC/actions/workflows/pylint.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

# Background
The COVID-19 pandemic wiped out a lot of tournament bass fishing in our local area (Austin, Tx) for the past couple of years. Member attendance for our Bass Fishing Club meetings and tournaments lowered & stopped completely when lockdown protocols occured. Since the lockdown, attendance has remained low and growth has slowed. We've tried various methods to increase participation but some are only effective for short periods of time. We'd like to try to leverage technology to fill in gaps of member participation while honoring: 1 member 1 vote.

*Some* of our South Austin Bass Club (SABC) process is manual & hand-written which is not archivable or mineable for data purposes. Our tournament director has kept some spreadsheets on-line (Googledocs) that we may be able injest for historical data. We can possibly use this data for insights about making more informed choices for tournament events in the future.

Lastly, our only medium for information transfer to non-members or potential members is through social media platforms (of which there are many) that come with their own maintenance overhead. Some members may not want or know how to join social media platform X just to get tournament information. We could use a neutral, (and cheap) platform to host this platform that social media can point to.


# Goals
The goal of this website application are to:
- Modernize the South Austin Bass Clubs tournament and voting process.
- Give tournament data and analytics for the club, lakes, individuals and teams
- Allow members to vote remotely on: Tournaments, Officers, and Bylaws (and more)
- Serve as a source of distributing club news, information and events to members and potential members
- Archive recent (and historical) club data
- Eliminate the need for manual process

We hope to increase member participation by modernizing our model of interaction and providing data analytics & insights. Also by allowing members to participate remotely vs. in-person exclusively will hopefully increase tournament attendance which should increase commradrie and growth.

Please see the [Wiki](https://github.com/envasquez/SABC/wiki) for an informal write-up to capture some requirements, solution space and design decisions. 

Initially, to learn more about some of Django's more modern features, I followed many of the recommendations from [this Tutorial from Corey Schafer](https://youtu.be/UmljXZIypDc) for writing a web application, and modified it to suite the club's needs. I essentially tried to learn "just enough" Django to pull all of our needs together.

Some things I found useful:
- Class Based Views
  - Pros:
    * This made entering and validating data super easy
    * Found a module called [Better Forms](https://pypi.org/project/django-betterforms/) that made dealing with multi-form views
    * I found a tables module to render table data using a CBV pattern [django-tables2](https://django-tables2.readthedocs.io/en/latest/)
  - Cons:
    * It can be tricky if you have to combine multiple forms to create an entry
    * There is a bit of magic (how Django implements CBV) to learn
- Using Pytest vs. Nosetest
    * Writing straight functions with normal asserts is super easy
    * Pytest decorators make DB integration easy
- Dockerizing everything!
  - Pros:
    * Its Docker! I don't have to run "anything" local like a Postgresql server
  - Cons:
    * Sometimes it can take a bit of overhead to rebuild containers from scratch when changing code
- Mypy type annotations ...
  - Pros:
    * Its the right thing to do!
    * I found a few bugs - or rewrote some code due to mypy feedback
  - Cons:
    * It can be hard to properly annoate Django, because it has a bit of "magic" happening in the framework
    * Need to monkey-patch things to get it annotated properly or add additional packages
    * I felt it grew in complexity - vs - reward as I was starting to have to look-up how to solve special cases and support for py3.11
***

# Questions / Comments
If you happened upon this repo and have questions, comments, concerns or suggestions; Please feel free to post them to the discussion board or open a GitHub issue. Lastly - if you're a Django guru and want to help me take things to the next level - I am ABSOLUTELY willing to learn.

For Example: If you could answer questions like: What is a useful purpose of custom "Managers" besides being some kind of syntatical sugar - I tried using them (and maybe I did it wrong) - but found that it was just easier to make self contained functions that return the queries I want ...
