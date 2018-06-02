# Hat-kivy
The Hat mobile game written with Python and Kivy.  
Main idea of the game is based on the iOS app "Shlyapa new".

The Hat - is a word game you can play with your friends.  
Historically this game is meant to be played without any electroic gadgets - you just use small pieces of paper to write down words and ordinary hat where you put those pieces.  
Now in XXI century it's much easier with the applications like mine :)  
You can find complete rules inside the app.  

### Features:
* The code is adopted to Python 2 and 3. (Android version is build with Python 2)
* Supports 2 languages: English and Russian. Other languages can be easily added.
* Game words dicts are stored on remote server, the app checks it's version at every start and download new content automagically. It means that you'll need internet connection at least for the first launch (the game will warn you in case of your device is offline at first run).
* You can set round time and words amount from predefined values.
* Words unrepeatability: the app will try to show you only new (unique) words from dictionary every new game until the dict is over. Of course words are mixing every time.

## How can I get the app?
The easiest way - grab a copy from [Releases](https://github.com/kdeyko/Hat-kivy/releases) page.  
For now the only Android APK package is available.  
Later I'll try to add iOS version too.  

## How can I compile the app?
That's a tricky question: you don't need to compile to run python script :)  
Just use regular Python (v2 and v3 are supported) interpreter on you computer.  
But I guess you want to run the app on a smartphone or tablet, then you'll have to compile it.  
You'll need to prepare some environment for that:
* Linux box 
* Python 2.7
* [Buildozer](https://github.com/kivy/buildozer)
* [Kivy](https://kivy.org/)

Actually there are lot of variants how you can compile the app, above is my setup for Android packaging.  
Please refer to [official kivy documentation](https://kivy.org/docs/guide/packaging.html) about packaging.  

## Other stuff
This game is my first real completed project.  
I know that the code is far from ideal, but I tried my best, so please don't judge me strictly.  
You are welcome to leave comments and create issues.  

Special thanks to my wife for help and inspiration.

### Donations:
The game is absolutely free to use and modification.
If you like my work I'd really appreciate your donation:  

**BTC**: 16hqyeFKLjMf8ReNQV318xk6YSQUPNUBTt  
**Yandex.Money**: 410011006623328
