"""Per-project content for the capstone PDF reports (consumed by make_reports.py).

Element grammar inside each section:
  "text"                       -> a body paragraph (supports **bold**)
  ("h2", "Sub-heading")        -> a sub-heading
  ("table", [headers], [rows]) -> a table
  ("bullets", [items])         -> a bullet list
  ("callout", "text")          -> a highlighted honest note
"""

MOLECHECK = {
    "slug": "molecheck",
    "title": "MoleCheck",
    "subtitle": "On-Device AI Skin-Lesion Screening",
    "accent": "#00796B",
    "tagline": "Classifying moles as benign or malignant from a phone photo, with a "
               "model that runs entirely on the device.",
    "sections": [
        ("Executive Summary", [
            "MoleCheck is a mobile app that helps someone judge whether a mole looks benign "
            "or potentially malignant. The user photographs one skin lesion, and a "
            "convolutional neural network estimates how likely it is to be malignant. The "
            "model runs **entirely on the phone**: the photo is never uploaded, which "
            "protects privacy and lets the app work offline.",
            "On a held-out test set of 1,722 images the classifier reaches a **ROC-AUC of "
            "0.914**. Tuned for screening, it catches **90% of malignant lesions** while "
            "correctly clearing about **75% of benign** ones. The model was exported to "
            "TensorFlow Lite (verified faithful to within 0.001 probability) and embedded in "
            "a Flutter app tested end-to-end on a device.",
            "MoleCheck is an educational project, not a medical device, and is designed "
            "throughout to send users to a dermatologist rather than replace one.",
        ]),
        ("Introduction & Motivation", [
            "Skin cancer is among the most treatable cancers when caught early and most "
            "dangerous when caught late, yet access to dermatology is uneven and most people "
            "cannot tell which moles are worth showing a doctor. A phone triage aid that flags "
            "concerning lesions could lower the barrier to seeking care.",
            "The goal was to build such an aid end-to-end: train an image classifier on a "
            "public dermatology dataset, package it to run on a phone with no server, and wrap "
            "it in an app a non-expert can use. The project spans machine learning, model "
            "engineering (export and quantisation), and mobile development.",
        ]),
        ("Data", [
            "Training used the HAM10000 collection from the ISIC Archive — public "
            "dermatoscopic images of pigmented lesions (11,720 images, each labelled Benign, "
            "Malignant, or Indeterminate). The task was framed as binary classification; "
            "indeterminate images were dropped, leaving a realistically imbalanced set "
            "(~18% malignant).",
            ("h2", "Preventing data leakage"),
            "The same physical lesion is often photographed several times. Splitting those "
            "duplicates naively across train and test would let the model memorise specific "
            "lesions and post inflated scores, so the data was split **by lesion, not by "
            "image** — every photo of a lesion stays in one split.",
            ("table", ["Split", "Lesions", "Images", "Malignant %"],
             [["Train", "6,121", "8,123", "18.8%"],
              ["Validation", "1,309", "1,726", "18.1%"],
              ["Test", "1,309", "1,722", "18.2%"]]),
        ]),
        ("Methodology", [
            "The classifier is a **YOLO11s-cls** convolutional network (5.4M parameters), "
            "pretrained on ImageNet and fine-tuned on the mole data. It was chosen because it "
            "transfer-learns quickly on a modest GPU and exports cleanly to mobile formats. "
            "Training ran 40 epochs on an NVIDIA RTX 5060 Ti in about six minutes, with heavy "
            "flip/rotation/colour augmentation to combat the class imbalance and mimic the "
            "variability of real phone photos.",
        ]),
        ("Results", [
            "Plain accuracy is misleading here — always guessing 'benign' already scores ~82%. "
            "The meaningful metrics are sensitivity, specificity, and the threshold-independent "
            "ROC-AUC.",
            ("table", ["Metric", "Value", "Meaning"],
             [["ROC-AUC", "0.914", "Ranks malignant above benign well"],
              ["Sensitivity", "90.1%", "Malignant lesions correctly flagged"],
              ["Specificity", "74.7%", "Benign lesions correctly cleared"]]),
            ("h2", "Choosing the decision threshold"),
            "Missing a cancer is far worse than a false alarm, so the default 0.5 cutoff is "
            "wrong for screening. The threshold was lowered to **0.137** to reach ~90% "
            "sensitivity. The app deliberately errs toward caution.",
        ]),
        ("Deployment", [
            "Running on-device required converting PyTorch to TensorFlow Lite. Because the "
            "direct export is unsupported on Windows, the model was routed PyTorch → ONNX → "
            "onnx2tf → TFLite. Correctness was **verified, not assumed**: across 32 test images "
            "the exported model matched the original to within 0.0009 probability with "
            "identical decisions. The 20.8 MB model ships inside a Flutter app (one codebase "
            "for iOS and Android) with a three-screen disclaimer onboarding, and was tested "
            "end-to-end on an Android emulator.",
        ]),
        ("Limitations & Ethical Considerations", [
            ("bullets", [
                "Not a medical device — an educational prototype, not validated for clinical use.",
                "It misses some cancers: at 90% sensitivity, ~1 in 10 malignant lesions is not flagged.",
                "Domain shift: trained on dermatoscope images; everyday phone photos are harder.",
                "Public datasets under-represent darker skin tones — a known equity concern.",
            ]),
            "These limitations shape the design: the app is framed as a prompt to seek "
            "professional care, never a substitute for it.",
        ]),
        ("Future Work", [
            ("bullets", [
                "Fine-tune on ordinary smartphone photos to close the domain gap.",
                "Measure and mitigate performance across skin tones.",
                "Add calibrated uncertainty so the app can say 'image too low-quality to assess'.",
                "Ship the iOS build and run a small usability study.",
            ]),
        ]),
    ],
}

ECG = {
    "slug": "ecg-arrhythmia",
    "title": "ECG Arrhythmia",
    "subtitle": "Classifying Heartbeats, and the Inter-Patient Generalization Gap",
    "accent": "#c62828",
    "tagline": "A 1-D neural network that sorts heartbeats into four clinical categories — "
               "and an honest look at why 96% in the lab becomes 44% on unseen patients.",
    "sections": [
        ("Executive Summary", [
            "This project classifies individual heartbeats from an ECG into four AAMI "
            "categories — Normal, Supraventricular, Ventricular, and Fusion — using a compact "
            "**1-D convolutional network** (77,000 parameters). More than the model, the "
            "project is a case study in honest evaluation.",
            "During training, validation accuracy looked excellent. But on a **patient-"
            "independent** test set the honest result is **70% accuracy and 44% macro-recall**: "
            "the model catches 86% of ventricular beats but only 9% of supraventricular ones. "
            "That gap is the lesson.",
        ]),
        ("Introduction & Motivation", [
            "Arrhythmia detection from ECG is a classic biosignal problem. The aim was to build "
            "the full pipeline — data, model, on-device export, browser demo — while treating "
            "the evaluation with the rigour the domain demands.",
        ]),
        ("Data", [
            "The MIT-BIH Arrhythmia Database (PhysioNet) provides 48 half-hour, single-lead "
            "recordings with a cardiologist's label on every beat (~100,000 beats). Each beat "
            "was cut into a 260-sample window centred on its peak and normalised. Beats map to "
            "four AAMI classes; the tiny paced class was excluded.",
            ("callout", "Key decision: the standard **inter-patient split** (de Chazal) was "
             "used — training and test recordings come from **different patients**, so results "
             "reflect generalisation to new people, not memorised individuals."),
        ]),
        ("Methodology", [
            "A four-block 1-D CNN (77k parameters) was trained with an inverse-frequency "
            "weighted loss, because ~90% of beats are normal and a naive model would ignore "
            "the rare, important classes. The checkpoint was selected by macro-recall, not "
            "accuracy.",
        ]),
        ("Results", [
            "On the untouched test patients:",
            ("table", ["Class", "Recall", "Note"],
             [["Normal", "72%", "Majority class"],
              ["Supraventricular", "9%", "Nearly missed entirely"],
              ["Ventricular", "86%", "Caught well"],
              ["Fusion", "9%", "Very rare, hard"]]),
            "Overall: 70% accuracy, **44% macro-recall**, ROC-AUC 0.958 at the window level.",
            ("h2", "Why S and F fail"),
            "A ventricular beat has a visibly mis-shapen waveform, so a shape-reading model "
            "spots it. A supraventricular beat looks almost normal — what marks it is its "
            "**timing** (it arrives early). The model sees each beat in isolation, so it is "
            "blind to the one feature that defines the class it fails on.",
        ]),
        ("Deployment", [
            "The model was exported to a self-contained ONNX file (325 KB) that runs in the "
            "browser via WebAssembly, and to TensorFlow Lite for an Android app ('ECG Check'), "
            "both verified to match the PyTorch model to within 1e-5. A visitor picks a real "
            "unseen-patient beat and watches it classified on-device.",
        ]),
        ("Limitations & Ethical Considerations", [
            ("bullets", [
                "Not a medical device — an educational study on a research dataset.",
                "Trained on curated research beats; real-world signals are noisier.",
                "The honest 44% macro-recall shows the model is not deployable as-is — which is the point.",
            ]),
        ]),
        ("Future Work", [
            ("bullets", [
                "Add RR-interval (beat-timing) features — the missing signal for supraventricular beats.",
                "Report a full confusion analysis and calibrated confidence.",
            ]),
        ]),
    ],
}

ADHD = {
    "slug": "adhd-eeg",
    "title": "ADHD from EEG",
    "subtitle": "Reading Attention in Children's Brain Waves",
    "accent": "#7c3aed",
    "tagline": "A multi-channel network that classifies children's EEG as ADHD or control, "
               "split honestly by subject — 92% accuracy that actually holds up.",
    "sections": [
        ("Executive Summary", [
            "This project classifies 2-second windows of 19-channel children's EEG as coming "
            "from the ADHD or the control group of a research study, using a **multi-channel "
            "1-D CNN** (193,000 parameters). Because there are only 121 children but hundreds "
            "of thousands of windows, the single most important choice is the data split.",
            "Splitting **by subject** (no child appears in both training and test), the model "
            "reaches **91.7% accuracy and 0.965 ROC-AUC on 24 completely unseen children**. "
            "Unlike the ECG project, there is no collapse from validation to test — the signal "
            "genuinely transfers across people.",
        ]),
        ("Introduction & Motivation", [
            "EEG-based ADHD studies are a well-known area — and a well-known trap. Much "
            "published work splits EEG windows randomly, letting the same child appear in "
            "training and test, so the model learns to recognise individuals rather than "
            "ADHD. This project deliberately avoids that.",
            ("callout", "**ADHD is diagnosed clinically, never from a brief EEG.** This "
             "classifies research-group membership — a pattern-recognition exercise, not a "
             "diagnosis."),
        ]),
        ("Data", [
            "The Nasrabadi ADHD/Control dataset (via Kaggle) contains 19-channel EEG at 128 Hz "
            "from 61 ADHD and 60 control children (ages 7–12), recorded during a visual "
            "attention task. Signals were cut into non-overlapping 2-second (256-sample) "
            "windows, per-channel normalised, and split **by subject** — including a "
            "subject-level validation set carved from the training children.",
            ("table", ["Split", "Subjects", "Windows"],
             [["Train", "83", "5,838"],
              ["Validation", "14", "948"],
              ["Test (unseen)", "24", "1,614"]]),
        ]),
        ("Methodology", [
            "A four-block multi-channel 1-D CNN (all 19 electrodes fed together, 193k "
            "parameters) was trained with class weighting. Crucially, the model is scored at "
            "the **subject level**: each subject's window predictions are averaged into one "
            "decision, since a per-window number is optimistic when one child contributes many "
            "windows.",
        ]),
        ("Results", [
            ("table", ["Metric (unseen subjects)", "Value"],
             [["Subject-level accuracy", "91.7% (22 of 24)"],
              ["Subject-level ROC-AUC", "0.965"],
              ["Window-level accuracy", "89.0%"]]),
            "The validation and test numbers agree closely — evidence the model reads "
            "something real about the groups rather than memorising individuals.",
        ]),
        ("Deployment", [
            "Exported to ONNX (775 KB) for an in-browser demo that draws all 19 EEG channels "
            "as a clinical-style montage and classifies a chosen recording on-device, and to "
            "TensorFlow Lite for an Android app ('EEG Explorer'). Parity with PyTorch was "
            "verified to ~3e-6.",
        ]),
        ("Limitations & Ethical Considerations", [
            ("bullets", [
                "Classifies research-group membership, not a diagnosis of any individual.",
                "Only 24 test subjects: 91.7% means 22 of 24 — a wide confidence interval.",
                "One cohort, one task; real-world attention difficulties are far more varied.",
            ]),
        ]),
        ("Future Work", [
            ("bullets", [
                "Band-limit the input to find which frequencies carry the signal.",
                "Ablate electrodes to locate which scalp regions matter.",
                "Subject-level cross-validation over all 121 children to tighten the estimate.",
            ]),
        ]),
    ],
}

LEUKEMIA = {
    "slug": "leukemia",
    "title": "Leukemia Subtyping",
    "subtitle": "Sorting Blood-Smear Cells — and Why 99.8% Is a Warning",
    "accent": "#ad1457",
    "tagline": "A vision model that subtypes leukemic cells from blood smears — and a case "
               "study in why a near-perfect score can be the least trustworthy result.",
    "sections": [
        ("Executive Summary", [
            "This project sorts a single white blood cell from a smear into four classes — "
            "Benign plus three stages of B-cell acute lymphoblastic leukaemia (Early Pre-B, "
            "Pre-B, Pro-B) — with a transfer-learned vision model. It scores **99.8% accuracy** "
            "on held-out images.",
            ("callout", "That 99.8% is presented as a **red flag, not a triumph.** The dataset "
             "ships no patient identifiers, so a random split almost certainly puts the same "
             "patient's cells in both training and test — and the model can win on staining "
             "and patient artefacts rather than on leukaemia biology."),
        ]),
        ("Introduction & Motivation", [
            "Distinguishing benign look-alike cells (hematogones) from leukemic blasts, and "
            "telling the ALL subtypes apart, is subtle work even for specialists — a genuinely "
            "interesting vision problem. It is also the most clinically serious task in the "
            "series, so the honest evaluation matters most here.",
        ]),
        ("Data", [
            "The dataset (Aria et al., 2021, via Kaggle) contains 3,256 peripheral-blood-smear "
            "images of one cell each, across the four classes. Images were split 70/15/15 into "
            "train/validation/test, stratified by class.",
            ("h2", "The unavoidable caveat"),
            "This public release contains **no patient IDs** (filenames are just sequential), "
            "so a strict patient-level split is impossible. Some patient leakage between "
            "splits is therefore likely, and pretending otherwise would be the dishonest move.",
        ]),
        ("Methodology", [
            "The classifier is a YOLO11s-cls network (5.4M parameters), transfer-learned from "
            "ImageNet — the same computer-vision pipeline as MoleCheck, reused directly. "
            "Training reached 100% validation accuracy within ~30 epochs.",
        ]),
        ("Results", [
            ("table", ["Metric", "Value"],
             [["Test accuracy", "99.8%"],
              ["Macro-F1", "0.998"],
              ["Errors", "1 of 489 images"]]),
            "On most projects this would be the headline. Here it is the cue to look harder at "
            "the split: cells from one slide share staining, lighting, focus and background, "
            "and a strong model can score near-perfectly by recognising **those** cues.",
        ]),
        ("Deployment", [
            "Exported to ONNX (21 MB) for an in-browser demo (pick a real cell image, classify "
            "it on-device) and to TensorFlow Lite for an Android app ('Cell Explorer'), with "
            "predictions verified to agree with the reference model.",
        ]),
        ("Limitations & Ethical Considerations", [
            ("bullets", [
                "Not a diagnostic tool — leukaemia diagnosis needs bone-marrow analysis, flow cytometry and genetics.",
                "The headline accuracy is inflated by likely patient leakage; treat it as an upper bound.",
                "A single, specific dataset; real clinical variety is far greater.",
            ]),
        ]),
        ("Future Work", [
            "The clear next step (v2) is the **C-NMC 2019** dataset, which ships patient IDs "
            "for ~15,000 cells. Holding out whole patients — as done in the EEG project — will "
            "give a lower but far more trustworthy number. That honest result is worth more "
            "than this one.",
        ]),
    ],
}

STOCK = {
    "slug": "stock-risk",
    "title": "Stock Risk + Sentiment",
    "subtitle": "Predicting Volatility Risk — and Testing Whether Sentiment Helps",
    "accent": "#1565c0",
    "tagline": "An educational model that predicts a stock's next-week volatility risk from "
               "price and news sentiment — and the honest finding that sentiment didn't help.",
    "sections": [
        ("Executive Summary", [
            "This project predicts whether a stock's coming week will be Low, Medium, or High "
            "**volatility** (how much it moves — not which direction) from 12 price and "
            "news-sentiment features, using a small neural network. It was built mainly to "
            "answer one question honestly: does the sentiment actually add anything?",
            "The model reaches **56% accuracy on three classes** (chance is 33%), driven by "
            "the fact that volatility clusters in time. But the headline is the ablation: a "
            "**price-only** model scored **57.2%** — slightly better. **The sentiment did not "
            "help.**",
            ("callout", "This is an educational machine-learning project, **not financial "
             "advice** and not a recommendation to buy, sell, or hold anything."),
        ]),
        ("Introduction & Motivation", [
            "Predicting a stock's direction is close to a coin flip; predicting its volatility "
            "is more tractable because calm and turbulent periods cluster. The interesting "
            "question for a project called '…with sentiment' is whether a news-sentiment "
            "signal earns its place alongside price features.",
        ]),
        ("Data", [
            "Daily prices for 59 stocks came from Yahoo Finance; ticker-level news sentiment "
            "(positive/negative/neutral per article) came from a public 2023 Polygon news "
            "dataset on Kaggle. From these, 12 features were built per stock-day — trailing "
            "returns, rolling volatility, volume, drawdown, and a daily sentiment signal.",
            ("callout", "No look-ahead: every feature uses only past data, the label is the "
             "**next** week's realised volatility, and train/test are split **by time** with a "
             "gap, so no test label overlaps the training period."),
        ]),
        ("Methodology", [
            "A small multilayer perceptron (3,397 parameters) classifies the feature vector "
            "into volatility terciles. To test sentiment's value, an identical model was "
            "trained on the **same features minus the three sentiment ones**, and the two "
            "were compared on the held-out later period.",
        ]),
        ("Results", [
            ("table", ["Model (unseen period)", "Accuracy"],
             [["Price + sentiment", "56.3%"],
              ["Price only", "57.2%"],
              ["Chance (3 classes)", "33.3%"]]),
            "Volatility is genuinely predictable (well above chance), but sentiment added "
            "**-0.9 points** — nothing, within noise. That is an honest and common finding: a "
            "daily average of headline sentiment is a coarse, sparse signal, and price-based "
            "volatility features already capture most of what's predictable.",
            "Reporting the negative result — instead of quietly dropping the ablation — is the "
            "difference between a demo and an experiment.",
        ]),
        ("Deployment", [
            "Exported to a 20 KB ONNX model for an in-browser demo (pick a real stock-and-week "
            "and see the predicted risk vs. what actually happened) and to TensorFlow Lite for "
            "an Android app ('Risk Explorer'), both verified to match PyTorch to ~4e-7.",
        ]),
        ("Limitations & Ethical Considerations", [
            ("bullets", [
                "Educational only — not financial advice and not a recommendation.",
                "Predicts volatility, not direction; it is right only about half the time.",
                "One year of data and one coarse sentiment signal.",
            ]),
        ]),
        ("Future Work", [
            ("bullets", [
                "A richer sentiment signal: per-headline embeddings rather than a daily average.",
                "A longer, multi-year history spanning more market regimes.",
                "Test whether sentiment helps more for direction than for volatility.",
            ]),
        ]),
    ],
}

PENTEST = {
    "slug": "pentest-agent",
    "title": "AI Pentest Agent",
    "subtitle": "Reinforcement Learning that Learns to Find Web Vulnerabilities",
    "accent": "#15803d",
    "tagline": "An agent that learns, by trial and error, to find security bugs in a practice "
               "web app — and beats random guessing six to one. Educational, sandbox-only.",
    "sections": [
        ("Executive Summary", [
            "This project builds a tiny practice website with three security bugs on purpose, "
            "then an AI agent that learns — by trial and error, the same idea behind "
            "game-playing AI — to find all three. Once trained it finds every bug in **4 "
            "actions**; a random agent needs about **25** and often misses one.",
            ("callout", "**Educational and sandbox-only.** Everything runs against a "
             "purpose-built vulnerable app on localhost. The techniques are standard OWASP "
             "Top 10 teaching examples and must only be used on systems you own or are "
             "authorised to test."),
        ]),
        ("Introduction & Motivation", [
            "Automated scanners are fast but blind: they follow fixed scripts, miss chained "
            "issues, and cannot adapt. Recent research shows reinforcement learning can learn "
            "efficient attack paths. This project explores that idea at a scale a student can "
            "fully understand — and, importantly, explain.",
        ]),
        ("The Practice App & Vulnerabilities", [
            "The target is a ~120-line 'MiniBank' Flask app on localhost with three planted, "
            "classic flaws:",
            ("bullets", [
                "SQL injection — the login query is built by string concatenation, so a crafted username logs in without a password.",
                "Reflected XSS — the search box echoes user input into the page unescaped.",
                "IDOR (broken access control) — changing the id in a profile URL reveals another user's private data.",
            ]),
        ]),
        ("Methodology", [
            "Penetration testing is modelled as a small game (a Markov Decision Process). The "
            "state records what has been discovered; the agent chooses among **12 actions** "
            "(reconnaissance, one working payload per bug, and several realistic dead ends). "
            "Every action is a **real HTTP request**, and a bug only counts when the real "
            "response proves it.",
            "The agent is trained with **tabular Q-learning** — a 16×12 table of learned "
            "action-values that can be read and explained directly — rewarded +10 for each "
            "new bug, +2 for doing recon first, and -1 per step so shorter attacks score "
            "higher. It is not told which actions are good; it discovers them.",
        ]),
        ("Results", [
            ("table", ["Agent", "Actions to find all 3", "Success rate"],
             [["Trained (Q-learning)", "4", "100%"],
              ["Random", "~25", "50%"]]),
            "Over a few hundred practice runs the agent's average session reward climbs from "
            "deeply negative (flailing) to +28 (the clean four-step attack: recon, then one "
            "payload per bug). Learning turns flailing into a repeatable strategy — about a "
            "six-fold efficiency gain over random guessing.",
            "After finishing, the agent writes a structured penetration-test report of each "
            "finding (severity, OWASP category, impact, and remediation).",
        ]),
        ("Limitations & Ethical Considerations", [
            ("bullets", [
                "A tiny sandbox: three known bugs and twelve actions — a teaching model, not a real scanner.",
                "Sandbox-only against a purpose-built target on localhost; standard OWASP teaching payloads only.",
                "Intended solely for educational and authorised, defensive security purposes.",
            ]),
        ]),
        ("Future Work", [
            ("bullets", [
                "More vulnerability types and a second practice app to test generalisation.",
                "Wire a real language model into the report-writing and payload seams.",
                "Compare against scripted tools and non-learning baselines.",
            ]),
        ]),
    ],
}

PROJECTS = [MOLECHECK, ECG, ADHD, LEUKEMIA, STOCK, PENTEST]
