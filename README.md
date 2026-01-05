# maigret night

A GUI edition of the OSINT tool maigret, Full info can be [found here](https://github.com/soxoj/maigret/tree/main) along with the [docs](https://maigret.readthedocs.io/en/latest/quick-start.html) as this relies on the CLI as a backend, nothing much has changed in functions. Can also install it via a venv with 

    python -m venv venv && pip3 install maigret

# Install

    python3 -m venv venv && source /venv/bin/activate && pip3 install PyQt6

![image](./img/2025-12-15_00-06.png)


For blackbird (crow) you'll need to install it (git clone) inside this dir and it'll work.

For crow:

```
pip install -r requirements_GUI.txt && pip install -r requirements.txt
```

You'll first need to clone blackbird then clone maigret night, move the miagret-night dir into the blackbird dir.

    git clone https://github.com/p1ngul1n0/blackbird && cd blackbird && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && git clone https://github.com/airborne-commando/maigret-night.git && cd maigret-night && pip install -r requirements_GUI.txt && cd .. && rsync -av --exclude='.git' maigret-night/ .

Then run python

    blackbird_web.py

**Known false positives**

    ok.ru
    Chatango
    247CTF
    Znanija
    zhihu
    
    These are the results you need to look out for.
    
    Use libreoffice calc, use auto-filter.
    
    for the normies:
    
    cat!=political
    cat!=tech
    cat!=coding
    name!=ok.ru
    name!=Chatango
    name!=247CTF
    name!=Znanija
    name!=zhihu
    name!=Telegram
    name!=Gravatar
    name!=Trello
    name!=weebly
    name!=Etoro
    name!=Lemon8
    name!=gumroad
    name!=Bandcamp
    name!=smule
    name!=Houzz
    name!=Polarsteps
    name!=Wattpad
    name!=redbubble

For more in this repo see the [filterlist](./filter_list/filterlist.txt), defaulted to `=` and commented out.

Not many people use telegram as that is a secure chat app; still do you own due diligence.

Read blackbirds git [here](https://github.com/p1ngul1n0/blackbird) | markdown on shell [scripting](https://app.radicle.xyz/nodes/iris.radicle.xyz/rad:zXuj4JY6cW16dn6usB9c9wuGJkBR/tree/markdown/scripts.md) your gonna need it.

Do a dry run first, get an idea of what the person is into; then sort in blackbird et al and refine steps.

You may also comment out usernames in a username file just like you would in a filterlist.

You also now have a stand alone web app for crow; it's inside ../maigret-night/blackbird_web/blackbird_web.py

Pretty much like maigret web almost.

To install just install like you normally should with maigret night.

[Most Popular Messaging Apps - exploding topics (Duarte. October 14, 2025)](https://explodingtopics.com/blog/messaging-apps-stats)

[9 Best Secure Messaging Apps for Business Leaders and Employees - JWU (Upated March 21, 2025)](https://online.jwu.edu/blog/9-best-secure-messaging-apps-business-leaders-and-employees/)

[What my name database](https://github.com/WebBreacher/WhatsMyName/blob/main/wmn-data.json)