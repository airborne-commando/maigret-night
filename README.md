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
    name!=gumroad
    name!=Bandcamp
    name!=smule
    name!=Houzz
    name!=Polarsteps
    name!=Wattpad
    name!=redbubble

# URI for spaced website names:

    name!=https://api.tracker.gg/api/v2/apex/standard/profile/origin/{account}
    name!=https://gitlab.archlinux.org/api/v4/users?username={account}
    name!=https://archiveofourown.org/users/{account}
    name!=https://forum.arduino.cc/u/{account}.json
    name!=https://projecthub.arduino.cc/{account}
    name!=https://artistsnclients.com/people/{account}
    name!=https://community.avid.com/members/{account}/default.aspx
    name!=https://www.bigo.tv/user/{account}
    name!=https://bio.site/{account}
    name!=https://bsky.app/profile/{account}
    name!=https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={account}.bsky.social
    name!=https://app.buymeacoffee.com/api/v1/check_availability
    name!=https://www.codeproject.com/Members/{account}
    name!=https://community.adobe.com/t5/forums/searchpage/tab/user?q={account}
    name!=https://www.dailykos.com/user/{account}
    name!=https://discord.com/api/v9/invites/{account}?with_counts=true&with_expiration=true
    name!=https://discord.com/api/v9/unique-username/username-attempt-unauthed
    name!=https://hub.docker.com/v2/orgs/{account}/
    name!=https://hub.docker.com/v2/users/{account}/
    name!=https://www.donationalerts.com/api/v1/user/{account}/donationpagesettings
    name!=https://community.evocms.ru/users/?search={account}
    name!=https://expressional.social/api/v1/accounts/lookup?acct={account}
    name!=https://federated.press/api/v1/accounts/lookup?acct={account}
    name!=https://filmot.com/channelsearch/{account}
    name!=https://filmot.com/unlistedSearch?channelQuery={account}&sortField=uploaddate&sortOrder=desc&
    name!=https://www.fodors.com/community/profile/{account}/forum-activity
    name!=https://fortnitetracker.com/profile/all/{account}
    name!=https://fosstodon.org/api/v1/accounts/lookup?acct={account}
    name!=https://freelancehunt.com/en/employer/{account}.html
    name!=https://freelancehunt.com/en/freelancer/{account}.html
    name!=https://www.furaffinity.net/user/{account}/
    name!=https://gamejolt.com/site-api/web/profile/@{account}/
    name!=https://gamerdvr.com/gamer/{account}
    name!=https://connect.garmin.com/modern/profile/{account}
    name!=https://genius.com/artists/{account}
    name!=https://genius.com/{account}
    name!=https://giphy.com/channel/{account}
    name!=https://api.github.com/users/{account}/gists
    name!=https://gitlab.gnome.org/api/v4/users?username={account}
    name!=https://extensions.gnome.org/accounts/profile/{account}
    name!=https://graphics.social/api/v1/accounts/lookup?acct={account}
    name!=https://greasyfork.org/en/users?q={account}
    name!=https://freelance.habr.com/freelancers/{account}/employer
    name!=https://freelance.habr.com/freelancers/{account}
    name!=https://qna.habr.com/user/{account}
    name!=https://news.ycombinator.com/user?id={account}
    name!=https://hcommons.social/api/v1/accounts/lookup?acct={account}
    name!=https://historians.social/api/v1/accounts/lookup?acct={account}
    name!=https://hometech.social/api/v1/accounts/lookup?acct={account}
    name!=https://hostux.social/api/v1/accounts/lookup?acct={account}
    name!=https://independent.academia.edu/{account}
    name!=https://imginn.com/{account}/
    name!=https://archive.org/advancedsearch.php?q={account}&output=json
    name!=https://forum.ixbt.com/users.cgi?id=info:{account}
    name!=https://joemonster.org/bojownik/{account}
    name!=https://lcwo.net/api/user_exists.php
    name!=https://libretooth.gr/api/v1/accounts/lookup?acct={account}
    name!=https://lor.sh/api/v1/accounts/lookup?acct={account}
    name!=https://malpedia.caad.fkie.fraunhofer.de/actor/{account}
    name!=https://mapstodon.space/api/v1/accounts/lookup?acct={account}
    name!=https://www.massageanywhere.com/profile/{account}
    name!=https://masto.nyc/api/v1/accounts/lookup?acct={account}
    name!=https://mastodon.social/api/v2/search?q={account}&limit=1&type=accounts
    name!=https://mastodonbooks.net/api/v1/accounts/lookup?acct={account}
    name!=https://mcname.info/en/search?q={account}
    name!=https://playerdb.co/api/player/minecraft/{account}
    name!=https://www.meetme.com/{account}
    name!=https://minecraftlist.com/players/{account}
    name!=https://www.moddb.com/html/scripts/autocomplete.php?a=username&q={account}
    name!=https://moto-trip.com/profil/{account}
    name!=https://muckrack.com/{account}
    name!=https://musician.social/api/v1/accounts/lookup?acct={account}
    name!=https://blog.myfitnesspal.com/author/{account}/
    name!=https://community.myfitnesspal.com/en/profile/{account}
    name!=https://api.niftygateway.com/user/profile-and-offchain-nifties-by-url/?profile_url={account}
    name!=https://nitecrew.rip/api/v1/accounts/lookup?acct={account}
    name!=https://onlysearch.co/api/search?keyword={account}
    name!=https://wiki.openstreetmap.org/w/api.php?action=query&format=json&list=users&ususers={account}
    name!=https://www.ourfreedombook.com/{account}
    name!=https://patriots.win/u/{account}/
    name!=https://psnprofiles.com/xhr/search/users?q={account}
    name!=https://pollev.com/proxy/api/users/{account}
    name!=https://www.pornhub.com/pornstar/{account}
    name!=https://www.pornhub.com/users/{account}
    name!=https://poweredbygay.social/api/v1/accounts/lookup?acct={account}
    name!=https://discuss.privacyguides.net/u/{account}.json
    name!=https://queer.pl/user/{account}
    name!=https://rf-archive.com/users.php?s_tag={account}
    name!=https://speakerdeck.com/{account}/
    name!=https://api.sports-tracker.com/apiserver/v1/user/name/{account}
    name!=http://www.tf2items.com/id/{account}/
    name!=https://tilde.zone/api/v1/accounts/lookup?acct={account}
    name!=https://tooting.ch/api/v1/accounts/lookup?acct={account}
    name!=https://truthsocial.com/api/v1/accounts/lookup?acct={account}
    name!=https://uefconnect.uef.fi/en/{account}/
    name!=https://www.ultimate-guitar.com/u/{account}
    name!=http://ultrasdiary.pl/u/{account}/
    name!=https://unlistedvideos.com/search.php?user={account}
    name!=https://usa.life/{account}
    name!=https://vkl.world/api/v1/accounts/lookup?acct={account}
    name!=https://vmst.io/api/v1/accounts/lookup?acct={account}
    name!=https://public-api.wordpress.com/rest/v1.1/sites/{account}.wordpress.com
    name!=https://public-api.wordpress.com/rest/v1.1/sites/{account}.wordpress.com
    name!=https://public-api.wordpress.com/rest/v1.1/sites/{account}.wordpress.com
    name!=https://login.wordpress.org/wp-json/wporg/v1/username-available/{account}
    name!=https://login.wordpress.org/wp-json/wporg/v1/username-available/{account}
    name!=https://www.xboxgamertag.com/search/{account}
    name!=https://auctions.yahoo.co.jp/follow/list/{account}
    name!=https://www.youtube.com/c/{account}/about
    name!=https://www.youtube.com/user/{account}/about
    name!=https://www.youtube.com/@{account}
    name!=https://archive.org/wayback/available?url=https://www.fotolog.com/{account}
    name!=http://archive.org/wayback/available?url=https://parler.com/profile/{account}/posts
    name!=http://archive.org/wayback/available?url=https://parler.com/profile/{account}
    name!=https://archive.org/wayback/available?url=https://www.taringa.net/{account}
    name!=http://archive.org/wayback/available?url=https://twitter.com/{account}
    name!=http://archive.org/wayback/available?url=https://twitter.com/{account}/status/*

Not many people use telegram as that is a secure chat app; still do you own due diligence.

Read blackbirds git [here](https://github.com/p1ngul1n0/blackbird) | markdown on shell [scripting](https://app.radicle.xyz/nodes/iris.radicle.xyz/rad:zXuj4JY6cW16dn6usB9c9wuGJkBR/tree/markdown/scripts.md) your gonna need it.

Feel free to check out this [filter list](https://gist.github.com/airborne-commando/378af481b35edd3be53f3bc7f24724a1), defaulted to `=`


Do a dry run first, get an idea of what the person is into; then sort in blackbird et al and refine steps.

[Most Popular Messaging Apps - exploding topics (Duarte. October 14, 2025)](https://explodingtopics.com/blog/messaging-apps-stats)

[9 Best Secure Messaging Apps for Business Leaders and Employees - JWU (Upated March 21, 2025)](https://online.jwu.edu/blog/9-best-secure-messaging-apps-business-leaders-and-employees/)

[What my name database](https://github.com/WebBreacher/WhatsMyName/blob/main/wmn-data.json)