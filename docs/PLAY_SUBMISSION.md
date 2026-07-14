# Google Play submission runbook (RLcapstone apps)

Everything needed to publish the five apps. Steps marked **[YOU]** need your account or your
keystore password; steps marked **[CLAUDE]** I can run for you.

> **Framing strategy (important).** Four apps are health-adjacent and one is finance — categories
> Google reviews strictly. We reduce risk by being unambiguously **educational**: choose the
> **Education** category (not "Medical"), lead every listing with "educational demonstration, not a
> medical device," and keep the in-app disclaimers. These apps genuinely are educational demos, so
> this is honest, not a loophole.

## App inventory

| App folder | Package (applicationId) | Store title | Play category |
|---|---|---|---|
| `app` | `com.capstone.molecheck.mole_check` | MoleCheck (Educational) | Education |
| `app_ecg` | `com.capstone.ecgcheck.ecg_check` | ECG Check (Educational) | Education |
| `app_adhd_eeg` | `com.capstone.adhdeeg.adhd_eeg` | EEG Explorer (Educational) | Education |
| `app_leukemia` | `com.capstone.leukemia.leukemia_check` | Cell Explorer (Educational) | Education |
| `app_stock_risk` | `com.capstone.stockrisk.stock_risk` | Risk Explorer (Educational) | Education |

Package names are already unique and stable. **They are permanent once published — do not change
them after the first upload.**

---

## Step 1 — Create your upload keystore  **[YOU, one-time]**

Play uses **Play App Signing**: you upload with *your* key, Google manages the real signing key.
One upload keystore signs all five apps. In a terminal (keytool ships with the JDK at
`C:\dev\jdk-21.0.11+10\bin`):

```powershell
& "C:\dev\jdk-21.0.11+10\bin\keytool.exe" -genkeypair -v `
  -keystore C:\CAPSTONE\upload-keystore.jks `
  -storetype JKS -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

It will ask you to **create a password** (write it down somewhere safe — losing it is painful) and
a few identity fields (name/org — anything reasonable). The file `C:\CAPSTONE\upload-keystore.jks`
is gitignored and must never be committed or shared.

Then create a `key.properties` file in **each** app's `android/` folder
(`app/android/key.properties`, `app_ecg/android/key.properties`, …). All five are identical:

```properties
storePassword=YOUR_KEYSTORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=upload
storeFile=C:/CAPSTONE/upload-keystore.jks
```

(Use forward slashes in `storeFile`. `key.properties` is gitignored.) The gradle signing config is
already wired in all five apps — it reads this file automatically and falls back to debug signing if
it's missing.

Tell me when the keystore + the five `key.properties` files exist, and I'll build the bundles.

## Step 2 — Build the signed App Bundles  **[CLAUDE, after Step 1]**

For each app: `flutter build appbundle --release` → produces
`build/app/outputs/bundle/release/app-release.aab`. I'll build all five and hand you the `.aab`
files (Play wants `.aab`, not the sideload `.apk`).

## Step 3 — Play Console: create each app  **[YOU]**

For each of the five (Console → **Create app**):
- **App name:** the store title above · **Default language:** English (US)
- **App or game:** App · **Free or paid:** Free
- Accept the developer program declarations.

## Step 4 — Store listing  **[copy below, YOU paste]**

Per app, set **Short description** and **Full description** (copy in Step 8), the **app icon**
(512×512 — use `assets/icon/icon.png`, upscaled), a **feature graphic** (1024×500 — I can generate),
and **≥2 phone screenshots** (I can capture these from the emulator).

## Step 5 — Privacy policy  **[YOU paste one URL]**

Same for all five: **https://rlcapstone.ai/privacy.html** (already live — on-device, collects
nothing).

## Step 6 — Data safety form  **[YOU, answers below]**

Because everything is on-device:
- **Does your app collect or share any required user data types?** → **No.**
- Data collected: **None.** Data shared: **None.**
- **Is all user data encrypted in transit?** → Not applicable (no data leaves the device); if forced
  to answer, "Yes" is safe since there are no network transfers.
- **Do you provide a way to request data deletion?** → Not applicable / No (nothing is collected).

## Step 7 — Content rating, audience, and declarations  **[YOU, answers below]**

- **Content rating questionnaire:** category "Reference / Education"; answer **No** to all
  violence/sexual/profanity/gambling/controlled-substance questions. Expected result: **Everyone /
  PEGI 3.**
- **Target audience & content:** target age **18+** (adults). **Not** "designed for families." This
  is deliberate — these are educational tools for an adult audience and this avoids the extra
  child-safety requirements.
- **Ads:** No · **In-app purchases:** No · **Government app:** No.
- **Health apps declaration (if prompted):** declare the app is an **educational demonstration**,
  **not** a medical device, does not diagnose, and makes no clinical claims. Point to the in-app
  disclaimer and the on-device design.
- **News app:** No · **COVID-19 app:** No.

## Step 8 — Store-listing copy (per app)

Titles are ≤30 chars; short descriptions ≤80; full descriptions ≤4000. Each leads with the
educational framing on purpose.

### MoleCheck (Educational) — `com.capstone.molecheck.mole_check`
**Short:** On-device AI demo that flags a skin-lesion photo as lower or higher risk. Educational.

**Full:**
MoleCheck is an EDUCATIONAL demonstration of on-device machine learning. It is NOT a medical device,
is not FDA-cleared, and cannot diagnose skin cancer or any condition. Do not use it to make any
health decision — if you are concerned about a mole or a skin change, see a dermatologist.

What it does: you choose a photo of a single skin lesion and a small neural network, bundled inside
the app, estimates whether it looks lower-risk or higher-risk. Everything runs on your phone — your
photo is never uploaded, and the app works in airplane mode.

How it was built: the model was trained on public dermatology image datasets and evaluated honestly,
including where it falls short (real smartphone photos are harder than the clinical images models are
usually trained on). Read the full write-up and honest metrics at https://rlcapstone.ai.

This app is part of a student portfolio of educational AI projects. It is a learning tool, not a
diagnostic product.

### ECG Check (Educational) — `com.capstone.ecgcheck.ecg_check`
**Short:** Educational demo: an AI model classifies sample heartbeats on your device. Not medical.

**Full:**
ECG Check is an EDUCATIONAL demonstration of machine learning on electrocardiogram (ECG) signals. It
is NOT a medical device and does not diagnose any heart condition. It classifies pre-recorded sample
heartbeats from a public research database — it does not read your own heart.

What it does: pick a sample heartbeat and a 1D convolutional neural network, running on your device,
sorts it into standard beat categories. The project's real lesson is honest: accuracy that looks high
in validation drops sharply on patients the model has never seen. Full write-up and metrics at
https://rlcapstone.ai.

A learning tool from a student AI portfolio, not a clinical product.

### EEG Explorer (Educational) — `com.capstone.adhdeeg.adhd_eeg`
**Short:** Educational demo: a neural network reads sample EEG recordings on-device. Not diagnostic.

**Full:**
EEG Explorer is an EDUCATIONAL demonstration of machine learning on brain-wave (EEG) recordings. It
is NOT a diagnostic tool. ADHD and every clinical condition are diagnosed by professionals, never
from an app — this app classifies research-cohort recordings and nothing about you.

What it does: choose a sample multi-channel EEG recording and a neural network on your device
classifies it by study group, using a strict subject-level evaluation so the reported performance
reflects genuine generalization. Full write-up at https://rlcapstone.ai.

Part of a student AI portfolio; educational only.

### Cell Explorer (Educational) — `com.capstone.leukemia.leukemia_check`
**Short:** Educational demo: an AI model labels sample blood cells as leukemic or normal on-device.

**Full:**
Cell Explorer is an EDUCATIONAL demonstration of computer vision on blood-cell images. It is NOT a
medical device and does not diagnose leukemia or anything else — real diagnosis needs a
hematologist, bone-marrow analysis, and genetic testing.

What it does: pick a real single-cell image (the samples come from three different labs) and a neural
network on your device labels it leukemic or normal. The project is a case study in honest evaluation
— from a leakage-inflated 99.8% to a patient-split result, to a multi-lab model that generalizes
across microscopes. Full write-up at https://rlcapstone.ai.

A learning tool from a student AI portfolio, not a clinical product.

### Risk Explorer (Educational) — `com.capstone.stockrisk.stock_risk`
**Short:** Educational demo: a model predicts a stock's next-week volatility class. Not advice.

**Full:**
Risk Explorer is an EDUCATIONAL demonstration of machine learning on financial time series. It is NOT
financial advice and NOT a recommendation to buy, sell, or hold anything. It predicts VOLATILITY (how
much a stock might move), not direction, on pre-recorded sample data.

What it does: pick a sample stock-week and a small model on your device predicts a Low / Medium /
High volatility class. The project's honest headline is a negative result: adding news-sentiment
features did not improve the prediction, and the write-up says so. Details at https://rlcapstone.ai.

Part of a student AI portfolio; educational only, not investment advice.

## Step 9 — Release  **[YOU]**

1. Start on the **Internal testing** track (fast, low-stakes) to confirm the bundle installs and the
   listing is accepted, before promoting to **Production**.
2. Upload each app's `.aab`, complete the "Publishing overview" checklist (all green), and submit for
   review.
3. Expect extra review time on the health/finance apps. If one is rejected, the message will cite a
   specific policy — send it to me and we'll adjust the listing/framing rather than resubmitting
   blind. **Don't** rapid-fire resubmit; that's what draws account strikes.

## What I still owe you
- Build the five `.aab`s (after your keystore — Step 1/2).
- Generate feature graphics (1024×500) and capture phone screenshots from the emulator.
- A 512×512 icon per app if the current one needs upscaling.
