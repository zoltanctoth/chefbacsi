#!/usr/bin/python
# -*- coding: utf-8 -*-

from will.plugin import WillPlugin
from will.decorators import respond_to, hear
from datetime import date, datetime
import json

import os
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse

blacklist = ["Calvin Bistro", "Drop", "Farger Kávézó", "Tróger Gasztró Bisztró", "Komédiás Kávéház", "Mozsár Kávézó"]
aliases = {
    "gomba": {
        "aliases": ["gomba", "gombá", "vargány", "csiperk"],
        "icon": "http://findicons.com/files/icons/2258/addictive_flavour/48/super_mario_mushroom.png"
    },
    "hal": {
        "aliases": ["hal", "ponty", "lazac", "harcsa"],
        "icon": "http://dory.trialx.com/images/search/dory-icon.png"
    },
    "rantott": {
        "aliases": ["rántott", "bécsiszelet"],
        "icon": "http://www.hetek.hu/files/images/2006/10.038/szabad/magyarorszag_rantott_hus.jpg"
    }
}


def fb_get(what):
    response = requests.get("https://graph.facebook.com/v2.3/{}/feed/?access_token={}".format(what, os.environ["FB_API_TOKEN"]))
    if "error" in response:
        raise Exception(response)
    return response


def fb_parse(response, start_time=None):
    restaurant = {}
    restaurant["info"] = []

    if start_time is None:
        start_time = datetime.combine(date.today(), datetime.min.time())  # today 00:00

    d = response.json()

    menus = []
    for message in d['data']:
        time = parse(message['created_time']).replace(tzinfo=None)
        if time < start_time:
            break
        if 'message' not in message:
            break
        content = message['message']
        menu = [s for s in content.splitlines() if s.strip()]
        menu1 = [s for s in menu if s.strip() if not s.startswith("/")]
        menu2 = [s for s in menu if s.strip() if s.startswith("/")]
        if menu1:
            menus.append(menu1)
        if menu2:
            menus.append(menu2)
    restaurant["menus"] = menus

    return restaurant


fb_setup = {
    "castrobistro": {"name": "Castro Bistro", "get": fb_get, "parse": fb_parse},
    "konyhabudapest": {"name": "Konyha", "get": fb_get, "parse": fb_parse},
    "268952226502652": {"name": "Keksz", "get": fb_get, "parse": fb_parse},
    "Pistabadeli": {"name": "Pista bá'", "get": fb_get, "parse": fb_parse}
}


def fb_menu():
    restaurants = {}
    for restaurantName in fb_setup:
        restaurant = fb_setup[restaurantName]["parse"](fb_setup[restaurantName]["get"](restaurantName), start_time=None)
        restaurants[fb_setup[restaurantName]["name"]] = restaurant

    return restaurants


def miamaimenu_get():
    response = requests.get("http://miamaimenu.com/")
    if "error" in response:
        raise Exception(response)
    return response


# {"<restaurant>": {
#    "info": [<ar>, <nyitvatartas>, ...],
#    "menus": [
#        [<menu 1 item 1>, <menu 1 item 2>, ...],
#        [<menu 2 item 1>, <menu 2 item 2>, ...],
#        ...
#    ]
# }}
def miamaimenu_parse(response):
    d = {}

    content = response.content

    soup = BeautifulSoup(content, 'html.parser')
    table = soup.find("table", class_="menu")

    trs = table.find_all("tr")
    trs.pop(0)  # drop header row
    for tr in trs:
        a = tr.find("a", class_="restaurant")
        restaurant = unicode(a.contents[0])
        d[restaurant] = {}

        info = []
        d[restaurant]["info"] = info
        tds = tr.find_all("td")
        td1 = tds[0]
        spans = td1.find_all("span")
        if spans:
            for span in spans:
                if span.contents:
                    info_piece = span.contents[0]
                    info.append(info_piece)

        tds.pop(0)  # drop first column
        menus = []
        d[restaurant]["menus"] = menus
        weekday = datetime.today().weekday()
        if len(tds) <= weekday:
            raise Exception("No menu for today?")
        td = tds[weekday]  # today td in row
        divs = td.find_all("div")
        if divs:
            menu = []
            menus.append(menu)
            for divIdx, div in enumerate(divs):
                ps = div.find_all("p")
                for p in ps:
                    if p.contents:
                        meal = p.contents[0]
                        menu.append(unicode(meal))
    return d


class ChefPlugin(WillPlugin):

    # STATIC!!!
    preferences = {}

    def prefs_to_sentence(self, nick):
        if nick not in self.preferences:
            return "@" + nick + "is a new kid on block. They should ping me with '@chef taste'!"
        else:
            ret = "Here is what @" + nick + " likes/dislikes:\n"
            for (what, sentiment) in self.preferences[nick].iteritems():
                ret += "+" if sentiment == 1 else "-"
                ret += what + " "

        return ret

    def persist_preferences(self):
        with open('preferences.json', 'w') as outfile:
            json.dump(self.preferences, outfile)

    def load_preferences(self):
        with open('preferences.json', 'r') as infile:
            json_str = infile.read()
            self.preferences = json.loads(json_str)

    def fetch_menu(self):
        fb = fb_menu()
        miamai = miamaimenu_parse(miamaimenu_get())
        fb.update(miamai)
        for name in fb.copy():
            if name in blacklist:
                del(fb[name])
        return fb

    def get_nick(self, message):
        if type(message) is not str:
            return message.sender["nick"]
        else:
            return "boy"

    def get_body(self, message):
        if type(message) is not str:
            return message["body"]
        else:
            return message

    def get_ingredients(self, text):
        ret = {}
        for (key, val) in aliases.iteritems():
            for word in val["aliases"]:
                if word.lower() in text.lower():
                    ret[key] = True

        return ret.keys()

    @hear("^(mia)?(mai)?menu")
    def miamenu(self, message, dislikes=[]):
        self.reply(message, "(chef) OK, checking the net is what we have today, hang on!")
        menu = self.fetch_menu()
        skipped = []
        if len(menu) == 0:
            self.reply(message, "(chef) Oh boy, there is nothing to eat today")
        else:
            ret = ""
            for (name, info) in menu.iteritems():
                l = ""
                if len(info["menus"]) == 0:
                    continue

                for menusets in info["menus"]:
                    l += "<ul>\n"
                    for menu in menusets:
                        l += "<li>" + unicode(menu) + "</li>\n"
                    l += "</ul>\n"

                included = True
                ing = self.get_ingredients(l)
                for dislike in dislikes:
                    if dislike.lower().strip() in ing or dislike.lower().strip(" ") in l.lower():
                        included = False
                        skipped.append(name + " (" + dislike + ")")

                icons = ""
                for i in ing:
                    icons += "&nbsp;<img src='" + aliases[i]['icon'] + "' style='margin-left: 10px; height: 17px;'>"

                if included:
                    ret += "<b>" + name + "</b>" + icons + "<br/>\n" + l

            if len(skipped) > 0:
                ret += "<br><b>Don't go here today:</b>&nbsp;<i>" + ", ".join(skipped) + "</i>\n"
            self.say(ret, message=message, html=True)

    @respond_to("^advice")
    def advice(self, message):
        self.reply(message, "eat " + str(message["body"]) + ", " + str(message.sender["nick"]) + "!")

    @respond_to("^help")
    def help(self, message):
        self.say("(chef)(chef)(chef)(chef)(chef)(chef) Hello (chef)(chef)(chef)(chef)(chef)(chef)")
        self.say("""Tell me:
^(mia)?(mai)?menu - see the menu
@chef I like <something> - so I know you like it
@chef I don't like <something> - I'll skip these when you go out together!
@chef I don't care about <something> - Tastes change, I understand.
@chef taste - your taste
@chef taste <someone> - someone else's taste
@chef I'm eating with @x @y @z - I'll prepare a list of places that you all will like!""")

    @respond_to("^taste")
    def my_info(self, message):
        self.load_preferences()
        body = self.get_body(message)
        if len(body) > len("taste") + 1:
            nick = body[len("taste") + 1:].replace("@", "")
        else:
            nick = self.get_nick(message)
            if nick not in self.preferences:
                self.reply(message, "Hi new boy, tell me more: '@chef I like this' or '@chef I don't like that'")
                return

        self.reply(message, self.prefs_to_sentence(nick))

    @respond_to("^(i|I) ")
    def personal_prefs(self, message):
        self.load_preferences()

        body = self.get_body(message)

        commands = {
            "like": 1,
            "love": 1,
            "accept": 1,
            "don't like": -1,
            "dislike": -1,
            "get digusted by": -1,
            "hate": -1,
            "don't care about": 0,
            "don't give a shit about": 0,
            "delete": 0,
            "need help with": 0,
            "gusto": 1
        }

        m = body[2:].lower()

        command = None
        for c in commands.keys():
            if m.startswith(c + " "):
                command = c
                what = m[len(c) + 1:]
        if command is None:
            self.reply(message, "I didn't quite get that, boy!")
            return

        nick = self.get_nick(message)

        sentiment = commands[command]
        if sentiment == 0:
            if nick in self.preferences and what in self.preferences[nick]:
                del(self.preferences[nick][what])
            self.reply(message, "Sometimes we should let " + what + " go. Since we cannot change reality, let us change the eyes which see reality (Tzu Ce)")
        else:
            if nick not in self.preferences:
                self.preferences[nick] = {}

            self.preferences[nick][what] = sentiment
            self.reply(message, what + " is something you " + command + ". Got ya!")

        self.persist_preferences()

    @respond_to("^(i|I)'m eating with ")
    def eating_with(self, message):
        self.load_preferences()

        words = self.get_body(message)[len("i'm eating with "):].split(" ")
        print words
        friends = [str(w[1:]) for w in words if w[0] == "@"]
        friends.append(self.get_nick(message))
        friends = list(set(friends))

        prefs = {}
        for f in friends:
            if f not in self.preferences:
                continue
            p = self.preferences[f]
            for (what, sentiment) in p.iteritems():
                if what in prefs:
                    prefs[what] = min(prefs[what], sentiment)
                else:
                    prefs[what] = sentiment

        ret = ""
        dislikes = []
        for (what, sentiment) in prefs.iteritems():
            if sentiment == -1:
                dislikes.append(what)
            ret += "+" if sentiment == 1 else "-"
            ret += what + " "

        self.say("@" + " @".join(friends) + ", This is your intersectio de cuisina: " + ret)
        return self.miamenu(message, dislikes=dislikes)
