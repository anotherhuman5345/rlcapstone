"""Per-project content for the capstone PDF reports (consumed by make_reports.py).

Written in a real high-school student's voice: first person, plain language,
still honest about the results. Element grammar inside each section:
  "text"                       -> a body paragraph (supports **bold**)
  ("h2", "Sub-heading")        -> a sub-heading
  ("table", [headers], [rows]) -> a table
  ("bullets", [items])         -> a bullet list
  ("callout", "text")          -> a highlighted honest note
"""

MOLECHECK = {
    "slug": "molecheck",
    "title": "MoleCheck",
    "subtitle": "A Phone App That Checks Moles With AI",
    "accent": "#00796B",
    "tagline": "It looks at a photo of a mole and guesses whether it's probably harmless "
               "or worth getting checked — and the AI runs right on your phone.",
    "sections": [
        ("Summary", [
            "MoleCheck is a phone app that looks at a photo of one mole and gives its best "
            "guess: does it look harmless, or like something a doctor should check? An AI model "
            "does the guessing, and the whole thing runs **on the phone itself** — the photo "
            "never gets uploaded anywhere, so it's private and works without internet.",
            "I tested it on 1,722 mole photos it had never seen before. It catches about **90% "
            "of the dangerous ones**, while correctly clearing about **75% of the harmless "
            "ones**. Its overall score for telling the two apart (called ROC-AUC, where 1.0 "
            "would be perfect) is **0.914**, which is pretty good.",
            "One thing I want to be clear about: this is a school project, not a real medical "
            "tool. The whole app is built to tell people to go see a skin doctor, not to "
            "replace one.",
        ]),
        ("Why I built this", [
            "Skin cancer is one of the most curable cancers if you catch it early, and one of "
            "the scariest if you don't. But not everyone can easily see a skin doctor, and most "
            "people have no idea which of their moles (if any) are worth worrying about. I "
            "wanted to build something that could give people a nudge to get a mole checked.",
            "My goal was to do the whole thing myself, start to finish: train an AI on real "
            "mole photos, shrink it down so it runs on a phone with no server, and put it in an "
            "actual app you can use. So the project mixes AI, some model 'plumbing', and "
            "building a real mobile app.",
        ]),
        ("The data", [
            "I trained the model on a public collection of mole photos called HAM10000 (from a "
            "big skin-image project called ISIC) — 11,720 photos, each labeled harmless or "
            "dangerous. Most of them are harmless, which matters later.",
            ("h2", "A sneaky mistake I avoided"),
            "The same mole is sometimes photographed a few times. If I let copies of the same "
            "mole end up in both my 'practice' pile and my 'test' pile, the model could "
            "basically memorize that exact mole and look way better than it really is. To stop "
            "that, I split the photos so **every picture of a given mole stays on one side "
            "only**.",
            ("table", ["Group", "Moles", "Photos", "Dangerous %"],
             [["Training", "6,121", "8,123", "18.8%"],
              ["Checking", "1,309", "1,726", "18.1%"],
              ["Testing", "1,309", "1,722", "18.2%"]]),
        ]),
        ("How it works", [
            "The model is a kind of image AI called YOLO11 (5.4 million little numbers it tunes "
            "as it learns). It already knew a lot about images before I started, so I just "
            "fine-tuned it on moles — that's called **transfer learning**, and it's why "
            "training only took about six minutes on my graphics card. I also flipped, rotated, "
            "and recolored the photos while training so the model doesn't get thrown off by "
            "different lighting or angles.",
        ]),
        ("Results", [
            "Accuracy sounds like the obvious thing to measure, but it's sneaky here: since "
            "most moles are harmless, a lazy model that just says 'harmless' every single time "
            "already scores about **82%** — while catching zero cancers. So instead I care "
            "about two things: how many dangerous moles it catches, and how many harmless ones "
            "it correctly leaves alone.",
            ("table", ["What I measured", "Score", "What it means"],
             [["ROC-AUC", "0.914", "How well it separates the two"],
              ["Catch rate", "90.1%", "Dangerous moles it flagged"],
              ["Clear rate", "74.7%", "Harmless moles it left alone"]]),
            ("h2", "How careful to make it"),
            "Missing a cancer is way worse than a false alarm — a false alarm just means "
            "someone gets a mole checked that turns out fine. So I set the model to be **extra "
            "cautious**: it would rather flag too much than miss something.",
        ]),
        ("Getting it running", [
            "To make the model run on a phone I had to convert it into a phone-friendly format. "
            "The normal way to do that didn't work on Windows, so I had to take a longer route "
            "through a couple of other formats. I didn't just trust that it still worked — I "
            "tested the converted model against the original on 32 photos, and they gave the "
            "**exact same answers every time**. Then I put it in a Flutter app (one set of code "
            "that works on both iPhone and Android), added a disclaimer you have to tap through "
            "first, and tested the whole thing on an Android phone.",
        ]),
        ("Honest limitations", [
            ("bullets", [
                "It's not a real medical device — it's a school project and hasn't been tested for actual doctor use.",
                "It misses some cancers. Catching 90% means about 1 in 10 slips through, so a 'looks fine' result is NOT a green light.",
                "It learned on special close-up medical photos, so normal phone pics are harder for it and it'll probably do worse in real life.",
                "The photos it learned from don't include enough darker skin tones, which is a real fairness problem in skin AI.",
            ]),
            "That's exactly why the app always tells you to see a real doctor instead of "
            "trusting it.",
        ]),
        ("What's next", [
            ("bullets", [
                "Train it on normal phone photos, not just medical close-ups.",
                "Test how well it works across different skin tones and fix the gaps.",
                "Let it say 'this photo is too blurry to judge' instead of guessing anyway.",
                "Finish the iPhone version and have some people actually try it.",
            ]),
        ]),
    ],
}

ECG = {
    "slug": "ecg-arrhythmia",
    "title": "ECG Heartbeats",
    "subtitle": "Reading Heartbeats With AI — and Why My 'Great' Score Was Fake",
    "accent": "#c62828",
    "tagline": "An AI that sorts heartbeats into four types — plus the big lesson about how a "
               "model can look amazing and actually be bad.",
    "sections": [
        ("Summary", [
            "This project takes single heartbeats from an ECG (the squiggly heart signal doctors "
            "record) and sorts each one into four types, including normal and a couple of "
            "dangerous kinds. I used a small AI model for it. But honestly, the real point of "
            "this project turned out to be a lesson about how testing can trick you.",
            "While it was training, the model looked great. But when I tested it the honest "
            "way — on patients it had **never seen** — it got **70% right overall**, and its "
            "fair score across all four types was only **44%**. It's good at spotting one "
            "dangerous type (86%) but almost totally misses another (9%). Figuring out why is "
            "the interesting part.",
        ]),
        ("Why I built this", [
            "Spotting heart-rhythm problems from an ECG is a classic AI problem, so I wanted to "
            "build the whole thing. But mostly I wanted to test it the *right* way, because a "
            "lot of projects online accidentally cheat at this and get fake-high scores.",
        ]),
        ("The data", [
            "I used the MIT-BIH database, a famous free collection of heart recordings where a "
            "cardiologist labeled every single beat. I cut the signal into individual beats and "
            "sorted them into four types.",
            ("callout", "The important choice: I made sure the patients in my test set were "
             "**completely different people** from the ones I trained on. That way the score "
             "shows how the model does on new people, not on people it already memorized."),
        ]),
        ("How it works", [
            "It's a small neural network (77,000 numbers). Since about 90% of beats are normal, "
            "a lazy model would just call everything normal — so I told the model to care more "
            "about the rare, important beats, and I graded it on how well it handled all four "
            "types fairly, not just overall.",
        ]),
        ("Results", [
            "Here's how it did on the patients it had never seen:",
            ("table", ["Beat type", "Caught", "Note"],
             [["Normal", "72%", "The most common type"],
              ["Supraventricular", "9%", "Almost totally missed"],
              ["Ventricular", "86%", "Caught these well"],
              ["Fusion", "9%", "Very rare, very hard"]]),
            "So: 70% right overall, but only **44%** once you weigh all four types fairly.",
            ("h2", "Why it fails on some beats"),
            "A 'ventricular' bad beat looks weirdly shaped, so a model that reads shapes catches "
            "it easily. But a 'supraventricular' bad beat looks almost like a normal one — the "
            "thing that makes it abnormal is its **timing** (it comes early). My model looks at "
            "each beat by itself with no sense of timing, so it's basically blind to the exact "
            "clue it needs. That's not a bug — it's the honest limit of how I set it up.",
        ]),
        ("Getting it running", [
            "I exported the model so it runs right inside a web browser (a tiny 325 KB file) and "
            "also made an Android app for it. Both give the same answers as the original. On the "
            "website you can pick a real heartbeat and watch it get sorted on your own device.",
        ]),
        ("Honest limitations", [
            ("bullets", [
                "Not a medical device — just a school project on a research dataset.",
                "44% isn't good enough to actually use — and showing that honestly is the whole point.",
                "Real ECGs are messier than the clean research ones I used.",
            ]),
        ]),
        ("What's next", [
            ("bullets", [
                "Add timing info (how far apart the beats are) — that's the missing clue for the type it fails on.",
                "Show a full breakdown of exactly what it mixes up with what.",
            ]),
        ]),
    ],
}

ADHD = {
    "slug": "adhd-eeg",
    "title": "ADHD from Brain Waves",
    "subtitle": "Telling ADHD vs. Not From EEG — Done the Honest Way",
    "accent": "#7c3aed",
    "tagline": "An AI that reads kids' brain-wave recordings, tested carefully so the 92% "
               "score is actually real.",
    "sections": [
        ("Summary", [
            "This project reads EEG recordings (brain-wave signals from sensors on the scalp) "
            "from kids and guesses whether each recording came from the ADHD group or the "
            "non-ADHD group of a study. I used an AI model that reads all 19 sensors at once.",
            "There are only 121 kids but tons of little recording snippets, so the biggest "
            "decision was how to split them for testing. I split **by kid** — no kid shows up "
            "in both training and testing — and the model got **91.7% right on 24 kids it had "
            "never seen**, with a strong separating score of **0.965**. Unlike my ECG project, "
            "this score actually held up under honest testing, which was a relief.",
        ]),
        ("Why I built this", [
            "EEG plus ADHD is a popular AI topic, and also a famous trap: a lot of projects mix "
            "snippets from the same kid into both training and testing, so the model just learns "
            "to recognize that specific kid instead of learning anything about ADHD. I wanted to "
            "avoid that.",
            ("callout", "To be super clear: **ADHD is diagnosed by doctors, never by a quick "
             "brain scan.** This just tells apart two groups in a research study — it's a "
             "pattern-matching demo, not a diagnosis."),
        ]),
        ("The data", [
            "I used a public dataset (from Kaggle) with brain-wave recordings from 61 kids with "
            "ADHD and 60 without, ages 7 to 12, recorded while they did an attention task. I "
            "chopped each recording into 2-second snippets and — importantly — kept every kid "
            "entirely on one side of the split.",
            ("table", ["Group", "Kids", "Snippets"],
             [["Training", "83", "5,838"],
              ["Checking", "14", "948"],
              ["Testing (new kids)", "24", "1,614"]]),
        ]),
        ("How it works", [
            "It's a neural network (193,000 numbers) that reads all 19 sensors together. And I "
            "graded it **by kid, not by snippet**: I average all of a kid's snippet-guesses "
            "into one final answer for that kid, because otherwise a kid with lots of snippets "
            "would count too much and mess up the score.",
        ]),
        ("Results", [
            ("table", ["On kids it never saw", "Score"],
             [["Right per kid", "91.7% (22 of 24)"],
              ["Separating score", "0.965"],
              ["Right per snippet", "89.0%"]]),
            "The checking score and the real test score are close, which is a good sign the "
            "model learned something real about the two groups instead of just memorizing "
            "individual kids.",
        ]),
        ("Getting it running", [
            "I put it in a web demo that draws all 19 brain-wave channels like a real hospital "
            "readout and sorts a recording on your device, plus an Android app. Both match the "
            "original model.",
        ]),
        ("Honest limitations", [
            ("bullets", [
                "It tells apart two research groups — it does NOT diagnose any real person.",
                "Only 24 test kids, so 91.7% is really '22 out of 24'. Small numbers, so the true accuracy could be higher or lower.",
                "It's one study and one task; real attention issues are way more varied.",
            ]),
        ]),
        ("What's next", [
            ("bullets", [
                "Check which brain-wave frequencies carry the signal.",
                "Turn off different sensors to see which parts of the head matter most.",
                "Test on all 121 kids in rotation to get a more solid number.",
            ]),
        ]),
    ],
}

LEUKEMIA = {
    "slug": "leukemia",
    "title": "Leukemia Blood Cells",
    "subtitle": "Sorting Blood Cells With AI — and Why 99.8% Made Me Suspicious",
    "accent": "#ad1457",
    "tagline": "A model that sorts leukemia cells from blood-smear photos — plus a lesson in "
               "why an almost-perfect score can actually be a warning sign.",
    "sections": [
        ("Summary", [
            "This project looks at a photo of one white blood cell and sorts it into four "
            "types: a healthy look-alike, plus three stages of a blood cancer called ALL "
            "(acute lymphoblastic leukemia). It scored **99.8%** on the test photos.",
            ("callout", "I'm not showing off that 99.8% — I'm **suspicious** of it. This "
             "dataset doesn't tell you which patient each cell came from, so cells from the "
             "same patient probably ended up in both training and testing. That means the "
             "model might be winning by recognizing stuff like the exact staining color, not "
             "actual cancer signs."),
        ]),
        ("Why I built this", [
            "Telling a healthy look-alike cell from a real cancer cell — and telling the cancer "
            "stages apart — is genuinely hard even for experts, so it's a cool image problem. "
            "It's also the most serious topic I worked on, so being honest about the results "
            "mattered the most here.",
        ]),
        ("The data", [
            "I used a public dataset (from Kaggle) of 3,256 blood-smear photos, each showing one "
            "cell, across the four types. I split them 70/15/15 into training / checking / "
            "testing.",
            ("h2", "The problem I couldn't fully fix"),
            "The dataset doesn't include patient IDs (the file names are just numbers), so "
            "there's **no way to guarantee** that one patient's cells stay together. That means "
            "some 'cheating' is probably baked in — and pretending it isn't would be the "
            "dishonest thing to do.",
        ]),
        ("How it works", [
            "It's the same image AI I used for MoleCheck (YOLO11), just retrained on blood "
            "cells. It hit 100% on the checking set within about 30 rounds of training — which, "
            "again, is a little *too* good.",
        ]),
        ("Results", [
            ("table", ["What I measured", "Score"],
             [["Test accuracy", "99.8%"],
              ["Fair score across types", "0.998"],
              ["Mistakes", "1 out of 489 photos"]]),
            "On most projects this would be the big headline. Here it's the red flag. Cells "
            "from the same slide share the same coloring, lighting, and background, and a strong "
            "model can score almost perfectly just by picking up on **those** instead of the "
            "actual cell.",
        ]),
        ("Getting it running", [
            "I put it in a web demo (pick a real cell photo, sort it on your device) and an "
            "Android app, both matching the original model.",
        ]),
        ("Honest limitations", [
            ("bullets", [
                "Not a diagnosis tool — real leukemia diagnosis needs lab tests like bone-marrow analysis.",
                "The 99.8% is probably inflated by the data problem above, so treat it as a best case, not reality.",
                "It's one specific dataset; real hospitals see way more variety.",
            ]),
        ]),
        ("What's next", [
            "The clear next step is a bigger dataset called C-NMC that **does** include patient "
            "IDs, so I can keep each patient's cells together (the way I did for the brain-wave "
            "project). The score will probably drop — but a lower, honest number is worth way "
            "more than this one.",
        ]),
    ],
}

STOCK = {
    "slug": "stock-risk",
    "title": "Stock Risk + News",
    "subtitle": "Guessing a Stock's Risk From Price and News — and Whether News Even Helps",
    "accent": "#1565c0",
    "tagline": "An AI that guesses if a stock will be calm or bumpy next week — plus the "
               "surprising answer to 'does adding news actually help?'",
    "sections": [
        ("Summary", [
            "This project guesses whether a stock's next week will be Low, Medium, or High "
            "risk — meaning how much it bounces around, **not** whether it goes up or down. It "
            "uses 12 clues from the stock's price history plus how positive or negative the "
            "news about it was. I mostly built it to answer one question honestly: does the "
            "news part actually help?",
            "It got **56% right** out of three choices (random guessing would be 33%), because "
            "calm and bumpy weeks tend to come in streaks. But here's the twist: when I removed "
            "the news clues completely, it scored **57%** — slightly *better*. So the news "
            "didn't help at all.",
            ("callout", "This is a school project, **not financial advice.** It doesn't tell "
             "you to buy or sell anything, and it only guesses how bumpy a stock is, not which "
             "way it'll go."),
        ]),
        ("Why I built this", [
            "Guessing whether a stock goes up or down is basically a coin flip. But guessing how "
            "*bumpy* it'll be is more doable, because calm and crazy stretches cluster together. "
            "And the whole point of a project 'with news' is to actually check whether the news "
            "part is pulling its weight — instead of just assuming it does.",
        ]),
        ("The data", [
            "I got daily prices for 59 stocks from Yahoo Finance, and news mood (positive, "
            "negative, or neutral for each article) from a public 2023 news dataset on Kaggle. "
            "From those I built 12 clues per stock per day — recent gains and losses, how bumpy "
            "it's been lately, trading volume, big drops, and a daily news-mood score.",
            ("callout", "No peeking at the future: every clue uses only past info, the thing "
             "I'm predicting is the **next** week, and I split training vs. testing **by time** "
             "so the test weeks all come after the training weeks."),
        ]),
        ("How it works", [
            "It's a tiny neural network (about 3,400 numbers) that sorts the 12 clues into Low, "
            "Medium, or High. To test whether news helps, I trained the exact same model a "
            "second time with the three news clues **removed**, and compared the two.",
        ]),
        ("Results", [
            ("table", ["Model (on weeks it never saw)", "Right"],
             [["Price + news", "56.3%"],
              ["Price only", "57.2%"],
              ["Random guessing", "33.3%"]]),
            "So the model beats random guessing by a lot — but adding news made it **0.9% "
            "worse**, basically no difference. That's actually a normal, honest result: a "
            "once-a-day average of news mood is a pretty weak, noisy signal, and the price "
            "clues already capture most of what's predictable.",
            "The tempting thing would be to quietly delete the news test and claim 'news "
            "helps!' Reporting that it didn't is the difference between a demo and a real "
            "experiment.",
        ]),
        ("Getting it running", [
            "I exported it to a tiny web demo (pick a real stock and week, see the guess vs. "
            "what actually happened) and an Android app, both matching the original.",
        ]),
        ("Honest limitations", [
            ("bullets", [
                "School project only — not financial advice, and not a recommendation.",
                "It guesses bumpiness, not direction, and it's only right about half the time.",
                "Just one year of data and a pretty rough news signal.",
            ]),
        ]),
        ("What's next", [
            ("bullets", [
                "A smarter news signal (actually reading each headline, not just averaging a mood score).",
                "More years of data covering different kinds of markets.",
                "Check if news helps more for guessing direction than bumpiness.",
            ]),
        ]),
    ],
}

PENTEST = {
    "slug": "pentest-agent",
    "title": "AI Hacking Agent",
    "subtitle": "Teaching an AI to Find Website Security Holes",
    "accent": "#15803d",
    "tagline": "An AI that learns, by trial and error, to break into a practice website — and "
               "beats random guessing six to one. Safe, practice-only.",
    "sections": [
        ("Summary", [
            "I built a tiny fake website with three security holes on purpose, then built an AI "
            "that learns to find all three — by trial and error, the same way game-playing AIs "
            "learn. Once trained, it finds every hole in just **4 moves**. Random guessing takes "
            "about **25** and usually misses one.",
            ("callout", "This is educational and totally sandboxed. Everything runs on a fake "
             "website on my own computer. These are standard practice-hacking examples (the "
             "OWASP Top 10), and you should only ever try this stuff on systems you own or are "
             "allowed to test."),
        ]),
        ("Why I built this", [
            "Normal security scanners are fast but kind of dumb — they follow a fixed script and "
            "can't adapt. I read that a type of AI called **reinforcement learning** can learn "
            "smart attack paths, so I wanted to try it at a size I could actually understand and "
            "explain.",
        ]),
        ("The practice website", [
            "The target is a tiny fake 'bank' website (about 120 lines of code) running on my "
            "computer, with three classic holes on purpose:",
            ("bullets", [
                "SQL injection — you can log in without a password by typing a trick into the username box.",
                "XSS — the search box will actually run code you type into it.",
                "Broken access control — changing a number in the web address lets you see someone else's private info.",
            ]),
        ]),
        ("How it works", [
            "I turned hacking into a simple game. The AI can pick from 12 possible moves (look "
            "around, try each attack, plus some dead-end moves that just waste time). Every move "
            "is a **real request** to the website, and it only scores when the website actually "
            "gives up a secret.",
            "It learns with something called **Q-learning** — basically a scorecard of how good "
            "each move is. It gets +10 for finding a new hole, +2 for looking around first, and "
            "−1 for every move, so shorter attacks win. Nobody tells it which moves are good; it "
            "figures that out on its own.",
        ]),
        ("Results", [
            ("table", ["Agent", "Moves to find all 3", "Found all 3"],
             [["Trained AI", "4", "100% of the time"],
              ["Random guessing", "about 25", "only 50% of the time"]]),
            "Over a few hundred practice runs, the AI goes from flailing around (a big negative "
            "score) to a clean four-move attack: look around, then one perfect move for each "
            "hole. It ends up about **six times faster** than random guessing. When it's done, "
            "it even writes up a little security report of what it found and how to fix each "
            "hole.",
        ]),
        ("Honest limitations", [
            ("bullets", [
                "It's a tiny practice setup — three known holes and twelve moves — so it's a learning demo, not a real hacking tool.",
                "It only ever touches a fake website on my own computer, using standard practice examples.",
                "It's meant purely for learning and defense — understanding how attacks work so you can stop them.",
            ]),
        ]),
        ("What's next", [
            ("bullets", [
                "Add more kinds of holes and a second practice site to see if it can adapt to something new.",
                "Hook up a language model to write better reports.",
                "Compare it against regular scanner tools.",
            ]),
        ]),
    ],
}

PROJECTS = [MOLECHECK, ECG, ADHD, LEUKEMIA, STOCK, PENTEST]
