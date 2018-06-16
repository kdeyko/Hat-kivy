# -*- coding: utf-8 -*-

import requests
import webbrowser
import gettext
import locale
import json
import os
from random import shuffle
from shutil import copyfile

from kivy.app import App
from kivy.properties import ObjectProperty, DictProperty, StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.image import Image
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.lang import Observable
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.utils import platform

if platform == 'android':
    try:
        import jnius
    except ImportError:
        Logger.critical('looks like it\'s not Android')
try:
    import sys
    reload(sys)
    sys.setdefaultencoding('utf8')
except (ImportError, NameError):
    print('Cannot import module sys, looks like it\'s Python3')


url_version = 'http://hat-kivy.atwebpages.com/content_version'
url_content = {
    'en': 'http://hat-kivy.atwebpages.com/content_en.txt',
    'ru': 'http://hat-kivy.atwebpages.com/content_ru.txt'
}


class Lang(Observable):
    observers = []
    lang = None

    def __init__(self):
        super(Lang, self).__init__()
        self.ugettext = None

    def _(self, text):
        return self.ugettext(text)

    def fbind(self, name, func, args, **kwargs):
        if name == "_":
            self.observers.append((func, args, kwargs))
        else:
            return super(Lang, self).fbind(name, func, *args, **kwargs)

    def funbind(self, name, func, args, **kwargs):
        if name == "_":
            key = (func, args, kwargs)
            if key in self.observers:
                self.observers.remove(key)
        else:
            return super(Lang, self).funbind(name, func, *args, **kwargs)

    def popup_unbind(self, widget):
        def check(widget, checked):
            if widget == checked:
                self.observers.remove(value)
            for child in widget.children:
                check(child, checked)
        for value in reversed(self.observers):
            func, args, kwargs = value
            check(widget, args[0])

    def switch_lang(self, lang):
        locales = gettext.translation('hat', 'lang', languages=[lang])
        self.ugettext = locales.gettext

        # update all the kv rules attached to this text
        for func, largs, kwargs in self.observers:
            func(largs, None, None)


tr = Lang()

languages = {'en': 'English', 'ru': 'Russian'}

roundTexts = ['''\
[b]\
ROUND 1

TALK \
[/b]

In this round you should explain words from the Hat using just your [b]TALKING[/b] skills.
Do NOT use words of the same root!\
''',
                  '''\
[b]\
ROUND 2

PANTOMIME\
[/b]

In this round you should explain words from the Hat using only [b]GESTURES[/b] of your body.
Complete silence!\
''',
                  '''\
[b]\
ROUND 3

ASSOCIATIONS\
[/b]

In this round you should explain words from the Hat using
[b]JUST ONE WORD.[/b]\
''']


class Context:

    instance = None

    version = None

    teams_count = 2
    rounds_count = 3

    scores = {}

    team = 1   # define first team number 1
    round = 1  # define first round number 1

    cur_score = 0  # for counting guessed words in every turn

    fulldict = []
    gamedict = []
    rounddict = []

    def clear_scores(self):
        for i in range(1, self.teams_count + 1):
            self.scores[i] = {'total': 0}
            for r in range(1, self.rounds_count + 1):
                self.scores[i]['score' + str(r)] = 0

    def get_winner(self):
        win_score = 0
        for team in range(1, self.teams_count + 1):
            next_score = self.scores[team]['total']
            if next_score > win_score:
                win_score = next_score
        for team in range(1, self.teams_count + 1):
            if self.scores[team]['total'] == win_score:
                self.scores[team]['total'] = '[color=e6e600][b]! ' + str(win_score) + ' ![/b][/color]'
            else:
                self.scores[team]['total'] = '[color=e6e600]' + str(self.scores[team]['total']) + '[/color]'


class SM(ScreenManager):
    pass


class NoInternet(Screen):
    pass


class StartMenu(Screen):
    pass


class SettingsScreen(Screen):
    pass


class LangPopup(Popup):
    def change_lang(self, instance):
        lang = ''
        if instance.text == tr._('English'):
            lang = 'en'
        if instance.text == tr._('Russian'):
            lang = 'ru'
        tr.switch_lang(lang)
        Context.instance.lang = lang
        HatApp.update_json('language', lang)
        hat.lang_name = languages[Context.instance.lang]
        tr.popup_unbind(self)
        self.dismiss()


class SoundTB(ToggleButtonBehavior, Image):
    def __init__(self, **kwargs):
        super(SoundTB, self).__init__(**kwargs)
        self.source = 'img/sound-on.png'

    def on_state(self, widget, value):
        if value == 'down':
            self.source = 'img/sound-off.png'
        else:
            self.source = 'img/sound-on.png'
        Context.instance.sound = value
        HatApp.update_json('sound', value)


class Rules(Screen):
    pass


class About(Screen):
    version = StringProperty(None)

    def on_pre_enter(self, *args):
        self.version = Context.instance.version

    @staticmethod
    def openlink(instance, link):
        webbrowser.open(link)


class RoundInfo(Screen):
    roundinfo_label = ObjectProperty(None)

    def on_pre_enter(self):

        self.roundinfo_label.text = tr._(roundTexts[Context.instance.round - 1])

        if Context.instance.round == 1:
            Context.instance.clear_scores()
            if HatApp.linecount() < Context.instance.words:
                HatApp.restore_content()
            HatApp.create_fulldict()
            shuffle(Context.instance.fulldict)

            Context.instance.gamedict = Context.instance.fulldict[:Context.instance.words]

        Context.instance.rounddict = Context.instance.gamedict[:]


class TeamNO(Screen):
    teamno_label = ObjectProperty(None)

    def on_pre_enter(self):
        self.teamno_label.text = \
            tr._('[b]Now plays the\nTeam # {num}[/b]').format(num=Context.instance.team)
        shuffle(Context.instance.rounddict)
        print(Context.instance.rounddict)  # just for testing


class Game(Screen):
    sound_timeout = SoundLoader.load('sounds/timeout.wav')
    sound_guessed = SoundLoader.load('sounds/guessed.wav')
    sound_skip = SoundLoader.load('sounds/skip.wav')

    timer = ObjectProperty(None)
    clock = None
    words_panel = ObjectProperty(None)
    cur_timer = 0
    cur_word = ''
    tempdict = []

    def __init__(self, **kwargs):
        super(Game, self).__init__(**kwargs)
        self.clock = Clock.schedule_interval(self.timer_update, 1)
        self.clock.cancel()

    def on_pre_enter(self):
        Context.instance.cur_score = 0
        self.cur_timer = Context.instance.time
        self.timer.text = tr._('Time left: ') + str(self.cur_timer)
        self.clock()
        self.update_word()

    @staticmethod
    def play_sound(sound):
        if Context.instance.sound == 'normal':
            if sound.state == 'play':
                sound.stop()
            sound.play()

    def timeout(self):
        Game.play_sound(self.sound_timeout)
        self.cur_timer = 0
        self.clock.cancel()
        for word in self.tempdict:
            Context.instance.rounddict.append(word)
        self.tempdict = []
        hat.sm.current = 'timeout'

    def update_word(self):
        if len(Context.instance.rounddict) == 0:
            if len(self.tempdict) == 0:
                self.clock.cancel()
                if Context.instance.round != 3:
                    hat.sm.current = 'endofround'
                else:
                    hat.sm.current = 'endgame'
                return
            else:
                Context.instance.rounddict = self.tempdict[:]
                self.tempdict = []
                shuffle(Context.instance.rounddict)
        self.cur_word = Context.instance.rounddict[-1]
        self.words_panel.text = self.cur_word

    def timer_update(self, dt=0):
        self.cur_timer -= 1
        if self.cur_timer == -1:
            self.timeout()
        self.timer.text = tr._('Time left: ') + str(self.cur_timer)

    def skip(self):
        Game.play_sound(self.sound_skip)
        self.tempdict.append(Context.instance.rounddict.pop())
        self.update_word()

    def guessed(self):
        Game.play_sound(self.sound_guessed)
        Context.instance.rounddict.pop()
        Context.instance.cur_score += 1
        Context.instance.scores[Context.instance.team]['score' + str(Context.instance.round)] += 1
        Context.instance.scores[Context.instance.team]['total'] += 1
        self.update_word()


class Timeout(Screen):
    cur_score = NumericProperty(None)

    def on_pre_enter(self, *args):
        self.cur_score = Context.instance.cur_score
        Context.instance.team = (Context.instance.team % Context.instance.teams_count) + 1


class EndOfRound(Screen):
    def on_enter(self, *args):
        if Context.instance.round == 1:
            HatApp.writeback_content()  # writes rest of words back to content txt file
        Context.instance.round += 1
        Context.instance.team = 1


class EndGame(Screen):
    pass


class Results(Screen):
    results_grid = ObjectProperty(None)
    round_lbl_text = ''

    @staticmethod
    def set_def():
        Context.instance.team = 1
        Context.instance.round = 1

    def on_pre_enter(self, *args):
        #
        # Testing this screen values
        #
        # Context.instance.clear_scores()
        # Context.instance.scores[1]['total'] = 46
        # Context.instance.scores[2]['total'] = 44
        # Context.instance.scores[1]['score1'] = 16
        # Context.instance.scores[1]['score2'] = 21
        # Context.instance.scores[1]['score3'] = 8
        # Context.instance.scores[2]['score1'] = 14
        # Context.instance.scores[2]['score2'] = 9
        # Context.instance.scores[2]['score3'] = 22
        #

        Context.instance.get_winner()

        round_names = ['Round 1\n[b]Talk[/b]',
                       'Round 2\n[b]Pantomime[/b]',
                       'Round 3\n[b]One Word[/b]',
                       '[color=e6e600][b]TOTAL[b][/color]']

        self.results_grid.cols = Context.instance.teams_count + 1
        self.results_grid.add_widget(Widget())

        for team in range(Context.instance.teams_count):
            team_label = Label(text=tr._('Team\n#') + str(team + 1), halign='center')
            team_label.font_size = .3 * team_label.width
            self.results_grid.add_widget(team_label)

        for r in range(Context.instance.rounds_count + 1):
            round_label = Label(text=tr._(round_names[r]), markup=True, halign='center')
            round_label.font_size = 0.2 * round_label.width
            if r == 3:
                round_label.font_size = 0.35 * round_label.width
            self.results_grid.add_widget(round_label)
            for team in range(Context.instance.teams_count):
                score_select = 'total'
                if r != 3:
                    score_select = 'score' + str(r + 1)
                score_lbl = Label(text=str(Context.instance.scores[team + 1][score_select]), markup=True)
                score_lbl.font_size = 0.4 * score_lbl.width
                self.results_grid.add_widget(score_lbl)

    def on_leave(self, *args):
        for child in self.results_grid.children[:]:
            self.results_grid.remove_widget(child)


class HatApp(App):
    words_tb_dict = DictProperty({})
    time_tb_dict = DictProperty({})
    lang_name = StringProperty()
    sound_tb = StringProperty()
    sm = None
    noinet = NoInternet()

    @staticmethod
    def update_content():
        for lang in url_content:
            filename = user_data_dir + '/content/content_' + lang + '.txt'
            Logger.critical('====================')
            Logger.critical(filename)

            cont_file = open(filename, 'w')
            r = requests.get(url_content[lang])
            r.encoding = 'utf-8'
            cont_file.write(r.text)
            cont_file.close()

            copyfile(filename, filename + '.bak')

    @staticmethod
    def linecount():
        filename = user_data_dir + '/content/content_' + Context.instance.lang + '.txt'
        return len(open(filename).readlines())

    @staticmethod
    def restore_content():
        cont_backup = user_data_dir + '/content/content_' + Context.instance.lang + '.txt.bak'
        cont_file = user_data_dir + '/content/content_' + Context.instance.lang + '.txt'
        copyfile(cont_backup, cont_file)

    @staticmethod
    def writeback_content():
        aftergamedict = Context.instance.fulldict[Context.instance.words:]
        filename = user_data_dir + '/content/content_' + Context.instance.lang + '.txt'
        cont_file = open(filename, 'w')
        for word in aftergamedict:
            cont_file.write(word)
        cont_file.close()

    @staticmethod
    def create_fulldict():
        filename = user_data_dir + '/content/content_' + Context.instance.lang + '.txt'
        cont_file = open(filename, 'r')
        Context.instance.fulldict = list(cont_file)
        cont_file.close()

    @staticmethod
    def update_json(key, val):
    	filename = user_data_dir + '/settings.json'
        with open(filename, 'r+') as f:
            settings = json.load(f)
            settings[key] = val
            f.seek(0)
            json.dump(settings, f, indent=4)
            f.truncate()

    @staticmethod
    def settings_tb(instance):
        if instance.group == 'wordsCount':
            Context.instance.words = int(instance.text)
            HatApp.update_json('words', int(instance.text))
        if instance.group == 'roundtime':
            Context.instance.time = int(instance.text)
            HatApp.update_json('time', int(instance.text))

    def press_buttons(self):
        for i in (30, 45, 60, 90):
            self.words_tb_dict[i] = 'normal'
            self.time_tb_dict[i] = 'normal'
        self.words_tb_dict[Context.instance.words] = 'down'
        self.time_tb_dict[Context.instance.time] = 'down'
        self.lang_name = languages[Context.instance.lang]
        self.sound_tb = Context.instance.sound

    @staticmethod
    def try_set_system_locale():
        def_lang = str(locale.getdefaultlocale()[0])
        if def_lang:
            if def_lang[:2] == 'ru':
                HatApp.update_json('language', def_lang[:2])
                Context.instance.lang = def_lang[:2]

    def build(self):
        Context.instance = Context()
        Context.instance.time = settings['time']
        Context.instance.words = settings['words']
        Context.instance.lang = settings['language']
        Context.instance.sound = settings['sound']

        content_folder_path = user_data_dir + '/content'
        Logger.critical(content_folder_path)

        loc_v = settings['version']
        if loc_v == 0:
            if not os.path.exists(content_folder_path):
                os.makedirs(content_folder_path)

            HatApp.try_set_system_locale()

        tr.switch_lang(Context.instance.lang)

        self.press_buttons()

        self.sm = SM()

        try:
            update_v = int(requests.get(url_version).text)
            if loc_v < update_v:
                HatApp.update_content()
                HatApp.update_json('version', update_v)
                loc_v = update_v
        except requests.exceptions.RequestException:
            if loc_v == 0:
                self.sm.current = 'noinet'

        Context.instance.version = str(loc_v)

        Window.bind(on_keyboard=self.my_key_handler)

        return self.sm

    def my_key_handler(self, window, key, *args):
        if key == 27:
            Logger.critical('Pressed Back Button!')
            if self.sm.current in ['settings', 'rules', 'about']:
                self.sm.current = 'startmenu'
            else:
                Logger.critical('Check if it\'s android')
                if platform == 'android':
                    Logger.critical('platform is Android')
                    PythonActivity = jnius.autoclass('org.renpy.android.PythonActivity')
                    Intent = jnius.autoclass('android.content.Intent')
                    intent = Intent(Intent.ACTION_MAIN)
                    intent.addCategory(Intent.CATEGORY_HOME)
                    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

                    currentActivity = jnius.cast('android.app.Activity', PythonActivity.mActivity)
                    currentActivity.startActivity(intent)
                    return True
            return True
        return False

if __name__ == "__main__":
    hat = HatApp()

    user_data_dir = App.get_running_app().user_data_dir
    settings_file = user_data_dir + '/settings.json'
    if not os.path.isfile(settings_file):
            copyfile('settings.json', settings_file)
    settings = json.load(open(settings_file, 'r'))

    hat.run()
