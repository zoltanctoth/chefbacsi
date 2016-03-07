# Mr. Chef

**Mr Chef is RapidMiner Hungary's personal lunch advisor HipChat bot.**

This is a Hackathon project. Please mind the code quality ;)
Pull requests are always welcome.

![](https://upload.wikimedia.org/wikipedia/en/1/1e/SouthParkChef.png)

## How to debug restart chef?

````
ssh jenkins@jenkins.radoop.eu
screen -r chef # activate chef screen
CTRL+C
git pull
./run_will.py
CTRL+A CTRL+D # detach chef screen
logout
````

## What to do is chef is not running at all?
````
sh jenkins@jenkins.radoop.eu
screen -S chef # create chef screen
cd zoltanctoth/chefbacsi/
. env/bin/activate # activate python environment
. env_init.sh # push credentials to the environment
./run_will.py # run chef!
CTRL+A CTRL+D # detach screen
````

## Installation
````
1. Install pip:
http://pip.readthedocs.org/en/stable/installing/

2. Install virtualenv
pip install virtualenv

3. Create and activate virtualenv
virtualenv env
. env/bin/activate

4. Install packages
pip install -r requirements.txt

5. Restart virtualenv (so ipython makes it into the PATH)
deactivate
. env/bin/activate

6. Start coding
ipython notebook "miamanimenu proto.ipynb"
````
