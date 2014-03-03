IAP Service
===========
An Open Source IAP Verification service for iOS

#### Motivation ####
The motivation for writing this was the lack of good cheat detection in existing IAP verification libraries.  I've seen a lot of creative IAP hacks, but this should cover the basics.  Additionally, this server follows a "trust but verify" policy and does not attempt to escalate the war against pirates.  Instead, the goal is simply to find pirates (for whatever purpose).  The data will be stored in a database of your choosing for access in whatever way you please.

There are generally four cases where an IAP might be considered invalid:
- Apple says the receipt is invalid
- Apple says the receipt is for a different bundle than it was reported under
- It's a valid IAP for your bundle, but it was for a different user
- It's a valid IAP for your bundle and on the correct user, but they've used it more than once

#### Client ####
At some point I will be motivated to release a Client SDK for this.  However, this is what I'm expecting from your client if you get to it before I do:

    {
        "game_secret" : "a shared secret between you and the server per game",
        "ifa"         : "1ad75bdc85527914459b41f44f3af0ff",
        "ifv"         : "f43adc9fc7548eef59b9314ec88078f6",
        "receipt"     : "8f4c538fb296a31b49bd38360ce49f838f4c538fb296a31b49bd38360ce49f838f4c538fb296a31b49bd38360ce49f838f4c538fb296a31b49bd38360ce49f83==",
        "xact_id"     : "06f5d6cbfd02476834906e83816662f8",
        "bid"         : "some game bundle id",
        "bvrs"        : "1.0",
    }

Passing along extra data with the transaction is encouraged.  Examples include:
- device\_type
- device\_version
- os\_version
- level
- playtime at transaction time

Data passed that interferes with the internal usage of the verification server will be discarded.

As a special note, you will also need to download and install http://www.github.com/wizzat/pyutil in the virtualenv until I find a new name for it and upload it to pypi.

#### Changelong ####

2014-03-03, Version 0.1
- Update requirements.txt


2013-08-08, Version 0.1
- Add support for user tracking
- Add support for transaction tracking
- Add support for detecting the four basic kinds of IAP cheating.
- Add iap verification runner for batching when Apple is down.

#### TODO ####
There's a lot of directions a project like this could go.  If you want any of it, please open an issue: https://github.com/wizzat/iapservice/issues/new

- Detect Transaction ID hacks between the receipt from Apple and the receipt from the client.
- Add support for subscriptions
- Add support for revenue tracking via packages
- Switch from web.py to flask (or bottle?)
- Clean up the code.
- Analytics and Reporting
    - Display intelligible errors from Apple
    - Add public 'login' endpoint
    - Add public 'logout' endpoint
    - Add user segment endpoint
    - Add Revenue page
    - Add DAU page
    - Add basic segmentation for cohorting and payments
- Add admin panel
    - Add companies via admin panel
    - Add games via admin panel
    - Add and update packages via admin panel
