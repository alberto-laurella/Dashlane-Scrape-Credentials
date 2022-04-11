This is my first github project and is very much a work in progress, as of now it's not meant for a end user.

The idea that pushed me to start this project was to make dashlane passwords as accessible on windows as they are on android, or at least closer to that experience.
I decided to write this project in python as it's the programming language I'm most familiar with.

-----------------------------
What does this script do?
-----------------------------
My intention was to make a script that would access credentials as organically as possible.

Two Hotkey listeners are set up, one for CTRL+P and one for CTRL+V, CTRL+V listener execution is suppressed.

When CTRL+P is detected:
This script will first retrieve the Foreground window process name and store that in the variable "title".

A chrome browser will be then opened through Selenium, this browser will habve to be opened on a custom profile where a dashlane login must have been performed beforehand.
Preferably some sort of windows security authentication should be setup (in my case I set up biometric authentication).

The newly opened chrome window is hidden.

through selenium XPATH use the title will be used as a search term for the given credentials, if any info is found a tkinter prompt will show a "Ready" message.
If there is more than one result a tkinter prompt will show all results as buttons to be clicked.

The clipboard contents will be changed to the username found (if both an username and an email are found username will be preferred).
CTRL+V listener execution is allowed to go through while CTRL+P execution is suppressed.
When CTRL+V is pressed the clipboard contents will be changed to the password found and CTRL+V will be suppressed while CTRL+P will be once again active.

Additionally when the browser is created a 5 minute timer is started. When said timer runs out the browser will be closed as that's the time limit for dashlane authentication.