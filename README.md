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
    name!=Etoro 
    name!=Lemon8
    name!=gumroad
    name!=Bandcamp
    name!=smule
    name!=Houzz 
    name!=Polarsteps  
    name!=Wattpad 
    name!=redbubble 

Not many people use telegram as that is a secure chat app; still do you own due diligence.

Read blackbirds git [here](https://github.com/p1ngul1n0/blackbird) | markdown on shell [scripting](https://app.radicle.xyz/nodes/iris.radicle.xyz/rad:zXuj4JY6cW16dn6usB9c9wuGJkBR/tree/markdown/scripts.md) your gonna need it.

Feel free to check out this [filter list](https://gist.github.com/airborne-commando/378af481b35edd3be53f3bc7f24724a1), defaulted to `=`
