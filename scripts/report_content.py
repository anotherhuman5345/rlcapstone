"""Per-project content for the capstone PDF reports (consumed by make_reports.py).

Written in a professional, precise voice suitable for an academic application:
formal headings, technical terminology restored, biomedical framing emphasized,
and every honest limitation and negative result retained. Element grammar
inside each section:
  "text"                       -> a body paragraph (supports **bold**)
  ("h2", "Sub-heading")        -> a sub-heading
  ("table", [headers], [rows]) -> a table
  ("bullets", [items])         -> a bullet list
  ("callout", "text")          -> a highlighted note (honesty / disclaimer)
"""

MOLECHECK = {
    "slug": "molecheck",
    "title": "MoleCheck",
    "subtitle": "Privacy-Preserving Skin-Lesion Analysis",
    "accent": "#00796B",
    "tagline": "A mobile application that classifies a photographed skin lesion as lower- or "
               "higher-risk using a convolutional neural network, with all inference running "
               "on-device — no server, no upload, full offline operation.",
    "sections": [
        ("Summary", [
            "MoleCheck classifies a photograph of a single skin lesion as lower-risk (benign) or "
            "higher-risk (malignant) using a convolutional neural network. Inference runs "
            "**entirely on-device**: the model is bundled inside the application, executes on the "
            "phone's own hardware, and functions in airplane mode. Because the image never leaves "
            "the device, the design provides a strong privacy guarantee for sensitive medical "
            "imagery.",
            "Evaluated on a held-out test set of 1,722 images, the model achieves a **ROC-AUC of "
            "0.914**, detecting **90% of malignant lesions (sensitivity)** while correctly "
            "clearing **75% of benign lesions (specificity)**.",
            ("callout", "Not a medical device. MoleCheck is an educational demonstration of image "
             "classification. It cannot diagnose skin cancer or any other condition and must not "
             "inform a health decision. Anyone concerned about a mole or a skin change should "
             "consult a dermatologist."),
        ]),
        ("Motivation", [
            "Skin cancer is among the most curable cancers when detected early and among the most "
            "dangerous when it is not. Access to dermatological screening is uneven, and most "
            "people cannot judge which lesions, if any, warrant professional review. The goal of "
            "this project was to build a complete pipeline end to end: train a classifier on real "
            "dermatological images, export it to run on a phone with no server, and deliver it "
            "inside a functioning mobile application. The project therefore spans machine "
            "learning, model deployment, and mobile development.",
        ]),
        ("Dataset and labeling", [
            "Training used a public ISIC Archive collection of **11,720 dermatoscopic images** (a "
            "superset of the HAM10000 dataset). Each image's diagnosis field was mapped to a "
            "binary label — benign or malignant — with indeterminate cases excluded. The dataset "
            "is heavily imbalanced toward benign lesions, which informed both the training "
            "procedure and the choice of decision threshold.",
            ("h2", "Preventing data leakage"),
            "The same lesion is sometimes photographed more than once. Allowing multiple images "
            "of one lesion to fall on both sides of the split would let the model memorize "
            "specific lesions and report inflated performance. To prevent this, the data was "
            "partitioned so that **every image of a given lesion remains in a single split**.",
            ("table", ["Split", "Lesions", "Images", "Malignant %"],
             [["Training", "6,121", "8,123", "18.8%"],
              ["Validation", "1,309", "1,726", "18.1%"],
              ["Test", "1,309", "1,722", "18.2%"]]),
        ]),
        ("Model and training", [
            "The classifier is **YOLO11s-cls**, the classification variant of Ultralytics' "
            "YOLO11 (5.4M parameters), fine-tuned for 40 epochs on an NVIDIA RTX 5060 Ti via "
            "**transfer learning** from a pretrained backbone. A pretrained model with a clean "
            "mobile-export path was chosen deliberately: a strong, reproducible baseline that "
            "deploys reliably is more valuable here than a bespoke architecture that is difficult "
            "to ship. Standard augmentation (flips, rotations, and color jitter) was applied so "
            "the model is robust to variation in lighting and orientation.",
        ]),
        ("Results and threshold selection", [
            "Accuracy is a misleading metric on this task: because most lesions are benign, a "
            "trivial \"always benign\" classifier already attains roughly **82%** accuracy while "
            "detecting no cancers. The evaluation therefore emphasizes sensitivity (malignant "
            "lesions detected) and specificity (benign lesions correctly cleared).",
            ("table", ["Metric", "Value", "Interpretation"],
             [["ROC-AUC", "0.914", "Overall separability of the two classes"],
              ["Sensitivity", "90.1%", "Malignant lesions correctly flagged"],
              ["Specificity", "74.7%", "Benign lesions correctly cleared"]]),
            ("h2", "Prioritizing sensitivity"),
            "The default 0.5 decision threshold is inappropriate for a screening task, because "
            "the two error types are asymmetric: a false negative (a malignant lesion reported as "
            "benign) is far more costly than a false positive (a benign lesion referred for "
            "review). The operating threshold was set to **0.137**, the point at which the model "
            "detects 90% of malignant lesions while still clearing 75% of benign ones. The "
            "application is deliberately tuned to err toward recommending professional "
            "evaluation.",
        ]),
        ("Deployment and verification", [
            "On-device inference required converting the PyTorch model to TensorFlow Lite. "
            "Because the direct export path is unsupported on Windows, the model was routed "
            "through ONNX and converted with onnx2tf. Conversion correctness was **verified "
            "rather than assumed**: the exported model was evaluated against the original "
            "PyTorch model and reproduced its predictions to within 0.001 probability, with "
            "identical decisions. The model was then integrated into a **Flutter** application "
            "(a single codebase targeting Android and iOS), gated behind a first-run disclaimer "
            "acknowledgement, and tested on an Android device.",
        ]),
        ("v2 — closing the smartphone gap", [
            "The most consequential limitation of v1 is that it was trained on **dermatoscopic** "
            "images — captured through a clinical lens in contact with the skin — while the "
            "application receives an ordinary **smartphone photograph**. The 0.914 headline was "
            "therefore measured on a domain the application never encounters. v2 quantifies that "
            "mismatch and then corrects it.",
            "The evaluation set is **PAD-UFES-20**: 2,298 smartphone photographs of skin lesions "
            "from a Brazilian screening program, each carrying a patient identifier. The data is "
            "split **by patient**, using v1's benign/malignant label space; actinic keratosis is "
            "excluded because v1's source data marked it indeterminate and dropped it, so scoring "
            "it would not be a fair test of the same model. This leaves 969 patients and 1,564 "
            "images.",
            ("table", ["Model", "Evaluated on", "ROC-AUC", "Specificity at 90% sensitivity"],
             [["v1 (dermoscopy-trained)", "its own dermoscopy test", "0.914", "75%"],
              ["v1 (dermoscopy-trained)", "smartphone photographs", "0.743", "32%"],
              ["v2 (fine-tuned on smartphone)", "the same smartphone photographs", "0.920", "75%"]]),
            "On smartphone photographs the dermoscopy-trained model fell from ROC-AUC 0.914 to "
            "**0.743**, and at the 90%-sensitivity operating point its specificity collapsed to "
            "32% — it flagged roughly two-thirds of benign lesions. Fine-tuning the same model on "
            "smartphone photographs restored performance to **ROC-AUC 0.920**, matching v1's "
            "original in-domain figure but now on the images the application actually receives, "
            "with specificity back to 75%. This smartphone-trained v2 model, with a 0.368 "
            "decision threshold, is what the application and browser demonstration now run.",
            ("callout", "v2's 0.920 is the more meaningful number because it is measured on the "
             "domain the application operates in. Evaluating a model on the data it will really "
             "face — rather than the most favorable version of the task — is the principle applied "
             "throughout this portfolio."),
        ]),
        ("Fairness across skin tones", [
            "A model with strong average performance can still fail unevenly, and in dermatology "
            "the recognized concern is degraded performance on darker skin. Because PAD-UFES-20 "
            "records a Fitzpatrick skin-type for many images, v2 can be audited for this directly. "
            "A **single global decision threshold** — the 90%-sensitivity operating point — is "
            "applied to every group, and the errors are examined for disparity.",
            ("table", ["Skin type (Fitzpatrick)", "Images", "Malignant", "Sensitivity"],
             [["I–II (lighter)", "130", "123", "94.3%"],
              ["III–IV (medium)", "48", "41", "78.0%"],
              ["V–VI (darker)", "3", "3", "too few to assess"]]),
            "The model catches 94% of malignant lesions on lighter skin but only 78% on medium "
            "skin — a roughly 16-point sensitivity gap in the direction the literature warns of, "
            "with enough malignant cases in each group (123 and 41) for the difference to be a real "
            "signal. Two honest limitations bound the audit: the dataset contains almost no darker "
            "skin (three Fitzpatrick V images, no VI), so performance on the group most affected "
            "**cannot be evaluated at all**; and skin type was recorded mainly for biopsied, mostly "
            "malignant lesions, leaving too few labelled benign cases to measure per-group "
            "specificity honestly.",
            ("callout", "The uncomfortable but honest conclusion: v2 is measurably better at "
             "detecting cancer on lighter skin than on darker skin, and the available data cannot "
             "even test the darkest skin. Closing that gap requires more representative data, not a "
             "modelling adjustment."),
        ]),
        ("Limitations", [
            ("bullets", [
                "Not a medical device — an educational project, not validated for clinical use.",
                "A 90% sensitivity target still implies roughly one in ten malignant lesions is missed, so a 'lower-risk' result is not reassurance.",
                "The shipped v1 model was trained on dermatoscopic images; v2 (above) measures the resulting smartphone-domain gap and closes it, but the two use different evaluation datasets and are not a like-for-like comparison beyond the shared label definition.",
                "Public dermatology datasets under-represent darker skin tones, so performance is not guaranteed to be uniform across skin types — a recognized equity concern in dermatology AI.",
            ]),
            "These limitations are precisely why the application always directs the user to "
            "consult a dermatologist.",
        ]),
        ("Future work", [
            ("bullets", [
                "Extend training and evaluation to datasets that include darker skin (Fitzpatrick V–VI), which PAD-UFES-20 barely contains — the fairness audit above cannot assess the group most affected by the equity gap.",
                "Fuse the image with the clinical metadata PAD-UFES-20 provides (age, lesion site, whether it changed), the way a dermatologist reasons.",
                "Add an abstention option so low-quality images are declined rather than classified.",
                "Complete the iOS build and conduct informal user testing.",
            ]),
        ]),
    ],
}

ECG = {
    "slug": "ecg-arrhythmia",
    "title": "ECG Arrhythmia Classification",
    "subtitle": "Inter-Patient Generalization in Heartbeat Classification",
    "accent": "#c62828",
    "tagline": "A 1D convolutional neural network that classifies individual heartbeats into "
               "four clinical categories, and a rigorous study of the inter-patient "
               "generalization gap in which ~96% validation performance falls to 44% on "
               "previously unseen patients.",
    "sections": [
        ("Summary", [
            "This project classifies individual heartbeats from an electrocardiogram (ECG) into "
            "four AAMI categories — Normal, Supraventricular, Ventricular, and Fusion — using a "
            "**1D convolutional neural network**. Its central contribution is methodological: a "
            "rigorous demonstration of the **inter-patient generalization gap**.",
            "During training, validation macro-recall climbs above **96%** and appears excellent. "
            "Evaluated honestly on patients the model has **never seen**, however, it attains "
            "**70% accuracy** and only **44% macro-recall** — strong on ventricular beats (86%) "
            "but nearly blind to supraventricular beats (9%). Explaining that gap is the point of "
            "the study.",
            ("callout", "Not a medical device. This is an educational study of biomedical signal "
             "classification on a public research dataset. It does not diagnose cardiac "
             "conditions and must not inform any medical decision."),
        ]),
        ("Motivation", [
            "Arrhythmia classification from the ECG is a canonical biomedical machine-learning "
            "problem. The objective here was not only to build a classifier but to evaluate it "
            "**correctly** — a great deal of published and hobbyist work on this dataset "
            "inadvertently leaks patient identity across the train/test split and reports "
            "inflated performance as a result.",
        ]),
        ("Dataset and preprocessing", [
            "The project uses the **MIT-BIH Arrhythmia Database**: 48 half-hour, two-channel "
            "records with a cardiologist's annotation on every beat (~100,000 beats total). The "
            "pipeline reads the standard MLII lead, extracts a 260-sample (~0.7 s) window "
            "centered on each beat, normalizes it, and maps the fine-grained annotation symbols "
            "into the four AAMI super-classes.",
            ("callout", "The single most consequential design decision is the train/test split, "
             "which is performed **by patient, not by beat**. A by-beat split lets one patient's "
             "heartbeats appear in both partitions, so the model learns to recognize individuals "
             "rather than arrhythmias — precisely the failure mode examined here."),
        ]),
        ("Model and metric", [
            "The classifier is a compact **1D CNN** (four convolutional blocks, 77k parameters, "
            "312 KB). Because roughly 90% of beats are normal, a trivial \"always normal\" model "
            "attains 90% accuracy while detecting none of the abnormal beats that matter. The "
            "primary metric is therefore **macro-recall** — the unweighted mean of the per-class "
            "recall rates — which improves only when the model handles the rare, clinically "
            "important classes. Class weighting was applied during training for the same reason.",
        ]),
        ("Results", [
            "Performance on the 22 entirely unseen test patients:",
            ("table", ["Beat class", "Recall", "Note"],
             [["Normal", "72%", "The dominant class"],
              ["Supraventricular", "9%", "Almost entirely missed"],
              ["Ventricular", "86%", "Detected reliably"],
              ["Fusion", "9%", "Rare and difficult"]]),
            "This corresponds to 70% overall accuracy but only **44% macro-recall** once all four "
            "classes are weighted equally. The gap between the ~96% validation curve and this "
            "honest figure is the central finding of the project.",
            ("h2", "Why the model fails on supraventricular beats"),
            "The per-class breakdown is diagnostic. A ventricular beat has a distinctly abnormal "
            "waveform **morphology**, which a shape-sensitive model detects readily. A "
            "supraventricular beat is nearly identical in shape to a normal beat; its defining "
            "feature is **timing** — it occurs prematurely. Because the model processes each beat "
            "in isolation, with no representation of rhythm, it is structurally blind to the one "
            "feature that distinguishes the class it fails on. This is an honest limitation of "
            "the chosen design, not a bug.",
        ]),
        ("Deployment", [
            "The model was exported to ONNX (a 28 KB file) and runs directly in the browser "
            "demonstration, with a matching TensorFlow Lite build in the Android application. "
            "Both reproduce the original model's predictions. In the browser demonstration the "
            "user can select a real heartbeat and watch it classified on their own device.",
        ]),
        ("Limitations", [
            ("bullets", [
                "Not a medical device — an educational study on a research dataset.",
                "44% macro-recall is not usable performance — demonstrating this honestly is the purpose of the project.",
                "Real-world ECGs are noisier and more varied than the clean research recordings used here.",
            ]),
        ]),
        ("Future work (v2)", [
            "The remedy follows directly from the diagnosis: provide the model with timing "
            "information. Adding **RR-interval features** — the intervals to the preceding and "
            "following beats — would let the model perceive prematurity, the hallmark of "
            "supraventricular beats. A full confusion matrix will accompany the v2 results.",
        ]),
    ],
}

ADHD = {
    "slug": "adhd-eeg",
    "title": "ADHD Classification from EEG",
    "subtitle": "Subject-Level Generalization on Pediatric EEG",
    "accent": "#7c3aed",
    "tagline": "A multi-channel 1D convolutional neural network that classifies children's EEG "
               "recordings by study group, using a strict subject-level split so the reported "
               "performance reflects genuine generalization to unseen individuals.",
    "sections": [
        ("Summary", [
            "This project classifies pediatric EEG recordings by study group (ADHD vs. control) "
            "using a **multi-channel 1D convolutional neural network** that reads all 19 scalp "
            "electrodes simultaneously. With only 121 children but hundreds of thousands of short "
            "windows, the decisive choice was how to split the data. Using a strict "
            "**subject-level split**, the model attains **91.7% subject-level accuracy** and a "
            "**ROC-AUC of 0.965** on 24 previously unseen children.",
            "Unlike the ECG project, this result exhibits no collapse from validation to test, "
            "indicating that the ADHD-vs-control signature in this task genuinely transfers "
            "across children.",
            ("callout", "Not a diagnostic tool. ADHD is a clinical diagnosis made by "
             "professionals, never from a brief EEG. This project classifies research-cohort "
             "group membership and is strictly educational."),
        ]),
        ("Motivation", [
            "EEG-based ADHD classification is both a popular topic and a well-known methodological "
            "trap: a substantial body of published work mixes windows from the same child across "
            "training and test, so the model learns to recognize individuals rather than anything "
            "about ADHD. The aim here was to avoid that leakage and report a figure that reflects "
            "real generalization.",
        ]),
        ("Dataset", [
            "The project uses the public **Nasrabadi ADHD/Control EEG** dataset: 61 children with "
            "ADHD and 60 controls, ages 7–12, recorded across 19 electrodes (10–20 system) at "
            "128 Hz during a visual attention task. Each recording was segmented into 2-second "
            "windows, with **every child kept entirely on one side of the split**.",
            ("table", ["Split", "Children", "Windows"],
             [["Training", "83", "5,838"],
              ["Validation", "14", "948"],
              ["Test (unseen children)", "24", "1,614"]]),
        ]),
        ("Model and evaluation protocol", [
            "The classifier is a **multi-channel 1D CNN** (193k parameters, 775 KB) that reads "
            "all 19 channels jointly. Evaluation is performed **per subject, not per window**: "
            "each child's window-level predictions are averaged into a single decision for that "
            "child, so a child contributing many windows does not dominate the score. The "
            "validation set used during training is itself a separate group of children, so "
            "every reported figure measures generalization to new individuals.",
        ]),
        ("Results", [
            ("table", ["On unseen children", "Value"],
             [["Subject-level accuracy", "91.7% (22 of 24)"],
              ["ROC-AUC", "0.965"],
              ["Window-level accuracy", "89.0%"]]),
            "The validation and test figures fall in the same range, indicating that the model "
            "captures a genuine group-level signal rather than memorizing individuals. Two "
            "caveats maintain a balanced interpretation: 91.7% of 24 subjects is 22 of 24 — a "
            "small denominator with a wide confidence interval — and the model classifies "
            "**research-group membership**, not a clinical diagnosis.",
        ]),
        ("Deployment", [
            "The model runs in a browser demonstration that renders all 19 EEG channels like a "
            "clinical montage and classifies a recording on-device, with a matching TensorFlow "
            "Lite build in the Android application (EEG Explorer). Both reproduce the original "
            "model's predictions.",
        ]),
        ("Limitations", [
            ("bullets", [
                "Classifies two research groups — it does not diagnose any individual.",
                "Only 24 test subjects, so 91.7% is 22 of 24; the true accuracy could be meaningfully higher or lower.",
                "A single cohort and a single task; real-world attention difficulties are far more varied.",
            ]),
        ]),
        ("Future work (v2)", [
            "The most valuable follow-ups concern trust rather than headline accuracy: "
            "band-limiting the input to identify which **frequency bands** carry the signal, "
            "**ablating electrodes** to determine which scalp regions are informative, and "
            "running subject-level cross-validation so the headline figure rests on all 121 "
            "children rather than a single 24-subject split.",
        ]),
    ],
}

LEUKEMIA = {
    "slug": "leukemia",
    "title": "Leukemia Cell Subtyping",
    "subtitle": "Blood-Smear Classification and a Case Study in Data Leakage",
    "accent": "#ad1457",
    "tagline": "A computer-vision classifier that sorts a single white blood cell into a benign "
               "look-alike or one of three stages of B-cell acute lymphoblastic leukemia — and a "
               "case study in why a 99.8% test score can be the least trustworthy figure in the "
               "portfolio.",
    "sections": [
        ("Summary", [
            "This project classifies a photograph of a single white blood cell into four classes: "
            "a benign look-alike, plus three maturation stages of B-cell acute lymphoblastic "
            "leukemia (ALL) — Early Pre-B, Pre-B, and Pro-B. The model attains **99.8% accuracy** "
            "and a **0.998 macro-F1** on the held-out test set.",
            ("callout", "That figure is presented not as an achievement but as a **warning**. The "
             "public dataset carries no patient identifiers, so a random split almost certainly "
             "places cells from the same patient on both sides of the partition. The model may be "
             "scoring highly by recognizing per-slide staining and background rather than genuine "
             "features of leukemia."),
        ]),
        ("Motivation", [
            "Distinguishing a benign look-alike cell (hematogones) from true leukemic blasts — "
            "and separating the leukemia stages from one another — is genuinely subtle work, even "
            "for trained hematologists, which makes it a substantive computer-vision problem. It "
            "is also the most serious subject in the portfolio, so honest reporting of the result "
            "mattered most here.",
        ]),
        ("Dataset", [
            "The project uses a public peripheral-blood-smear dataset (Aria et al., 2021) of "
            "**3,256 images**, each showing a single cell across the four classes, split 70/15/15 "
            "into training / validation / test.",
            ("h2", "A limitation that cannot be fully remedied"),
            "The dataset provides **no patient identifiers** (file names are plain indices), so "
            "there is no way to guarantee that one patient's cells remain together. Some degree "
            "of data leakage is therefore almost certainly baked into any split of this dataset, "
            "and reporting the headline figure without this caveat would be misleading.",
        ]),
        ("Model and training", [
            "The classifier is the same architecture used for MoleCheck — **YOLO11s-cls** (5.4M "
            "parameters), transfer-learned on the blood-cell images at 224×224. Validation "
            "accuracy reached **100%** within roughly 30 epochs, which — rather than being "
            "reassuring — is itself a signal to examine the data split more critically.",
        ]),
        ("Results", [
            ("table", ["Metric", "Value"],
             [["Test accuracy", "99.8%"],
              ["Macro-F1", "0.998"],
              ["Errors", "1 of 489 images"]]),
            "On most projects this would be the headline. Here it is the red flag. Cells from a "
            "single slide share staining, lighting, focus, and background, and a high-capacity "
            "model can score near-perfectly by keying on **those** cues rather than the cell "
            "itself. This is the same failure mode the EEG project avoids through subject-level "
            "splitting; it cannot be avoided here because the identifiers are simply absent.",
        ]),
        ("Deployment", [
            "The model was exported to ONNX for the browser demonstration and to TensorFlow Lite "
            "for the Android application (Cell Explorer), both reproducing the original model's "
            "predictions. The user can select a real cell image and classify it on-device.",
        ]),
        ("Limitations", [
            ("bullets", [
                "Not a diagnostic tool — real leukemia diagnosis requires bone-marrow analysis, flow cytometry, and genetic testing.",
                "The 99.8% figure is very likely inflated by the data-leakage issue above, so it should be read as a best case, not a realistic estimate.",
                "A single dataset; real clinical practice presents far greater variability.",
            ]),
        ]),
        ("Future work (v2)", [
            "The next iteration moves to the **C-NMC 2019** dataset, which provides patient "
            "identifiers for roughly fifteen thousand cells. This enables holding out entire "
            "patients — as done in the EEG project — and measuring what the model has genuinely "
            "learned. The expected outcome is a **lower** accuracy than 99.8%, and that lower "
            "figure will be substantially more meaningful.",
        ]),
    ],
}

STOCK = {
    "slug": "stock-risk",
    "title": "Stock Volatility & Sentiment",
    "subtitle": "Does News Sentiment Improve Volatility Prediction?",
    "accent": "#1565c0",
    "tagline": "A model that classifies a stock's coming week as Low, Medium, or High volatility "
               "from price history and news-sentiment features — built primarily to answer one "
               "question through a controlled experiment: does the sentiment signal actually "
               "improve the prediction?",
    "sections": [
        ("Summary", [
            "This project classifies a stock's coming week as **Low, Medium, or High volatility** "
            "— how much it moves, not its direction — from 12 features drawn from price history "
            "and daily news sentiment. It was built primarily to answer one question through a "
            "**controlled experiment**: does the sentiment signal actually improve the "
            "prediction?",
            "The model reaches **57% accuracy** on a three-class problem where chance is 33%, "
            "because volatility clusters over time. The decisive result is the ablation: removing "
            "the sentiment features entirely yielded **57.5%** — marginally **higher** than the "
            "57.1% obtained with sentiment. Sentiment added no predictive value.",
            ("callout", "Not financial advice. This is an educational machine-learning project. "
             "It predicts volatility, not price direction, and nothing here is a recommendation "
             "to buy, sell, or hold any security."),
        ]),
        ("Motivation", [
            "Predicting whether a stock rises or falls tomorrow is close to a coin flip. "
            "Predicting how much it will move is more tractable, because volatility exhibits "
            "**autocorrelation** — calm periods tend to follow calm periods and turbulent ones "
            "follow turbulent ones. A project framed around news sentiment should also **test "
            "whether the sentiment signal earns its place** rather than assuming it does.",
        ]),
        ("Data and features", [
            "Daily prices for 59 stocks were obtained from Yahoo Finance, and ticker-level news "
            "sentiment from a public 2023 dataset (Polygon). From these, **12 features** were "
            "engineered per stock per day — trailing returns, rolling volatility, volume, "
            "drawdown, and a daily sentiment score.",
            ("callout", "No look-ahead bias: every feature uses only past information, the target "
             "is the **next** week's realized volatility, and the train/test split is performed "
             "**by time**, so the test weeks all follow the training weeks."),
        ]),
        ("Model and experiment", [
            "The classifier is a compact **multilayer perceptron** (3,397 parameters, 20 KB) that "
            "maps the 12 features to Low / Medium / High. To test the sentiment signal directly, "
            "an **identical model** was trained a second time on price features only — sentiment "
            "removed — and the two were compared.",
        ]),
        ("Results", [
            ("table", ["Model (on unseen weeks)", "Accuracy"],
             [["Price + sentiment", "57.1%"],
              ["Price only", "57.5%"],
              ["Chance baseline", "33.3%"]]),
            "The model clears the chance baseline comfortably, but adding sentiment made it "
            "**0.4% worse** — no meaningful difference. This is a normal, honest outcome: a "
            "once-daily average of headline sentiment is a coarse, sparse signal, and the "
            "rolling-volatility features already capture most of what is predictable about next "
            "week's turbulence. **Reporting the negative result — rather than omitting the "
            "ablation and claiming sentiment 'works' — is what distinguishes an experiment from a "
            "demonstration.**",
            ("h2", "Error analysis"),
            "The errors fall where expected: the model reads calm weeks (Low, 75% recall) and "
            "turbulent weeks (High, 57%) reasonably well, but the Medium class is difficult (33% "
            "recall) because intermediate volatility sits on a blurred boundary between the other "
            "two. This is an interpretable failure mode rather than a mysterious one.",
        ]),
        ("Deployment", [
            "The model was exported to ONNX for the browser demonstration and to TensorFlow Lite "
            "for the Android application (Risk Explorer). Both reproduce the original model, and "
            "the demonstration lets the user pick a real stock and week and compare the "
            "prediction against what actually happened.",
        ]),
        ("Limitations", [
            ("bullets", [
                "Educational project only — not financial advice and not a recommendation.",
                "It predicts volatility, not direction, and is correct roughly half the time.",
                "A single year of data and a coarse daily sentiment signal.",
            ]),
        ]),
        ("Future work (v2)", [
            "For sentiment to earn its place it must be richer than a daily average: per-headline "
            "embeddings rather than a single number, a multi-year history spanning additional "
            "market regimes, and a test of whether sentiment contributes more to **direction** "
            "prediction than to volatility. Those results will be reported honestly — including "
            "if sentiment still does not help.",
        ]),
    ],
}

PENTEST = {
    "slug": "pentest-agent",
    "title": "Autonomous Pentest Agent",
    "subtitle": "A Reinforcement-Learning Agent for Web Penetration Testing",
    "accent": "#15803d",
    "tagline": "A purpose-built vulnerable web application and a reinforcement-learning agent "
               "that learns, through trial and error, to discover all three planted "
               "vulnerabilities — outperforming a random baseline sixfold. Educational and "
               "fully sandboxed.",
    "sections": [
        ("Summary", [
            "This project pairs a purpose-built vulnerable web application with a "
            "**reinforcement-learning agent** that learns — through trial and error, the paradigm "
            "behind game-playing AI — to discover all three planted vulnerabilities. Once "
            "trained, the agent finds every vulnerability in **4 actions**; a random baseline "
            "requires roughly **25** and frequently misses one. The agent outperforms the "
            "baseline **sixfold** and generates a structured findings report.",
            ("callout", "Educational and sandboxed. All activity targets a purpose-built "
             "vulnerable application on localhost. The techniques are standard OWASP Top 10 "
             "teaching examples and must only be used on systems you own or are explicitly "
             "authorized to test."),
        ]),
        ("Motivation", [
            "Conventional vulnerability scanners are fast but follow a fixed script and cannot "
            "adapt. **Reinforcement learning** can, in principle, learn efficient attack paths, "
            "so this project applies it at a scale small enough to understand and explain "
            "end to end.",
        ]),
        ("The target application", [
            "The target is a ~120-line \"MiniBank\" Flask application on localhost with three "
            "classic vulnerabilities planted deliberately:",
            ("bullets", [
                "SQL injection — a login bypass achievable by injecting into the username field.",
                "Reflected XSS — the search box reflects and executes injected script.",
                "Broken access control (IDOR) — altering an identifier in the URL exposes another user's private record.",
            ]),
        ]),
        ("Method", [
            "Penetration testing follows a natural sequence — reconnaissance, then exploitation — "
            "modeled here as a **Markov decision process**. At each step the agent selects one of "
            "twelve actions (crawl the site, attempt a SQL-injection login, attempt an XSS "
            "search, request another user's profile, or one of several unproductive actions). "
            "Every action is a **real HTTP request** to the live application, and a vulnerability "
            "is counted only when the real response confirms it.",
            "The agent learns with **tabular Q-learning** — a 16×12 table of learned action "
            "values. It receives **+10** for empirically confirming a new vulnerability, **+2** "
            "for performing reconnaissance first, and **−1** per step, so shorter attack paths "
            "score higher. The agent is not told which actions are productive; it explores "
            "(randomly at first) and updates the table from the rewards it receives, converging "
            "over a few hundred episodes.",
        ]),
        ("Results", [
            ("table", ["Agent", "Actions to find all 3", "Found all 3"],
             [["Trained agent", "4", "Every run"],
              ["Random baseline", "~25", "~50% of runs"]]),
            "Across training, mean episode reward rises from negative values (ineffective "
            "exploration that hits the step limit) to approximately **+28**, the reward of the "
            "efficient four-step attack: reconnaissance, then one precise action per "
            "vulnerability. Learning converts undirected exploration into an efficient, "
            "repeatable strategy — roughly **six times faster** than the random baseline.",
        ]),
        ("Automated reporting", [
            "On completion, the agent generates a structured penetration-testing report: each "
            "finding with its severity, OWASP category, impact, and remediation (parameterized "
            "queries, output escaping, proper authorization checks). The report is currently "
            "template-generated, with a clearly defined integration point where a language model "
            "would produce the narrative.",
        ]),
        ("Limitations", [
            ("bullets", [
                "A compact sandbox — three known vulnerabilities, twelve actions, one application — sized for understanding, not a production scanner.",
                "All activity targets a local application built for the purpose, using standard OWASP teaching examples.",
                "The project is intended for learning and defense: understanding how attacks work in order to prevent them.",
            ]),
        ]),
        ("Future work (v2)", [
            "The first defensive component is already published: a detector for AI-driven "
            "database ransomware (JADEPUFFER), which pivots the project from offense to defense. "
            "Subsequent work includes additional vulnerability classes, a second application to "
            "evaluate generalization, and integrating a language model into the reporting and "
            "payload-generation stages.",
        ]),
    ],
}

PROJECTS = [MOLECHECK, ECG, ADHD, LEUKEMIA, STOCK, PENTEST]
