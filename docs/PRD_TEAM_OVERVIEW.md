# Product Requirement Document (PRD): Edge-OCR Bus Route Identifier

## 1. Overview
Public buses in India (like APSRTC, BMTC, DTC) display route numbers and destinations on front windshield placards or electronic LED boards. For visually impaired commuters or elderly passengers with low vision, recognizing oncoming buses at crowded bus stops is a major daily hurdle, forcing them to rely on asking bystanders.

The **Edge-OCR Bus Route Identifier** is an assistive vision system designed to solve this problem. When a user points their device camera or presses a wearable trigger, the system takes a picture, extracts the bus route number using real-time edge computer vision, matches it against offline city route databases, and announces the bus number and destination out loud through audio and vibration feedback in **under 1.5 seconds**, even without internet access.

---

## 2. Tech Used and Its Functions

| Technology / Library | Purpose & Function |
| :--- | :--- |
| **Python 3.11** | Core programming language powering the entire backend pipeline and data processing. |
| **OpenCV (`cv2`)** | **Image Preprocessing**: Converts frames to grayscale, cleans lighting glare using CLAHE (adaptive histogram equalization), and highlights text with adaptive binarization so dark glass and sun reflections don't distort letters. |
| **Tesseract OCR v5.4.0** | **Optical Character Recognition**: Reads text from the preprocessed bus placard. Configured with single-line mode (`--psm 7`) and alphanumeric whitelisting for high-speed edge text extraction. |
| **Flask** | **Application Server**: Serves the lightweight web interface and provides REST API endpoints (`/api/identify`, `/api/benchmark`, `/api/config`) to process images and return performance metrics. |
| **Web Speech API** | **Audio Announcement**: Synthesizes clear voice read-outs (`"Bus 12 to Ramavarappadu"`) directly through the commuter's earphones or device speaker in an Indian English accent (`en-IN`). |
| **Offline CSV Route Databases** | **Zero-Latency Route Matching**: Pre-indexed city route dictionaries (Vijayawada, Delhi, Bengaluru) loaded into memory at startup to find destinations without needing mobile data. |
| **Vercel Serverless & WSGI** | **Cloud Deployment**: Hosts the web dashboard live on the cloud with custom WSGI path routing (`VercelPathFix`) for fast access from any browser. |
| **Hardware GPIO (`gpiozero`)** | **Wearable Edge Support**: Interfaces with physical push-buttons and vibration motors for tactile haptic feedback on devices like Raspberry Pi Zero 2 W. |

---

## 3. Key Features

1. **Sub-1.5-Second Response Time**:
   - The entire loop—from image capture and OpenCV enhancement to OCR reading, database lookup, and speech generation—executes in under 1.5 seconds.
2. **Offline-First Multi-City Operation**:
   - Works fully offline without an internet connection. Contains pre-loaded route datasets for Indian transit systems (APSRTC Vijayawada, BMTC Bengaluru, DTC Delhi).
3. **Fuzzy Route Error Correction**:
   - Handles noisy or partially smudged route boards. If OCR misreads a character (e.g. reading `1lJ` instead of `11J`), fuzzy matching corrects it to the closest known valid route.
4. **Dual Feedback (Voice & Haptics)**:
   - **Voice**: Speaks the route and destination clearly (`"Bus 11J to Jakkampudi YSR Colony"`).
   - **Haptic Vibration**: 
     - 1 short pulse = Bus confirmed.
     - 2 quick pulses = Low confidence / unclear photo.
     - 1 long pulse = No text detected (try again).
5. **Transit Ticket Web Dashboard**:
   - Features a high-contrast transit ticket interface, animated amber LED matrix board, live OpenCV stage breakdown, latency receipt, and an automated batch audit benchmark.
6. **Zero Fabricated Metrics**:
   - Every confidence score, latency timestamp, and intermediate frame is measured and retrieved from real execution buffers.

---

## 4. Target Audience

1. **Visually Impaired Commuters**: Individuals who cannot read distant or fast-moving bus boards and require hands-free, autonomous transit assistance.
2. **Elderly & Low-Vision Citizens**: Commuters with cataracts, macular degeneration, or reduced visual clarity in night/glare conditions.
3. **Daily Public Transit Users in Unfamiliar Cities**: Commuters who need instant confirmation of where a numbered bus is heading without asking strangers.
4. **Assistive Tech Developers & Hardware Engineers**: Teams building smart canes, smart glasses, or wearable transit badges.

---

## 5. Novelty (What Makes It Unique?)

1. **True Edge Architecture (No Expensive GPUs Needed)**:
   - Unlike heavy AI models (ChatGPT Vision, Gemini, or large YOLO models) that require expensive cloud servers, cloud subscriptions, and high-speed 5G, this runs entirely on lightweight local hardware (such as a $15 Raspberry Pi Zero 2 W or standard laptop).
2. **Deterministic & Hallucination-Free**:
   - AI vision models can hallucinate routes that do not exist. This system uses strict regex pattern filters paired with verified municipal transit databases, guaranteeing that only verified routes are announced.
3. **Anti-Glare Preprocessing Pipeline**:
   - Designed specifically for real outdoor conditions: headlights at night, dirty windshield reflections, and midday sunlight glare are neutralized using OpenCV CLAHE before OCR occurs.
4. **Authentic Transit-Centric User Experience**:
   - Combines tactile vibrations, clear Indian-accented speech, and an amber LED transit board designed for quick, accessible comprehension.

---

## 6. Primary Use Cases

- **Use Case 1: Waiting at a Crowded Bus Stop**:
  A visually impaired commuter hears a bus approaching. They press a wearable button or point their phone towards the sound. Within 1.5 seconds, their earphone announces: *"Bus 12 to Ramavarappadu"*, accompanied by a single short vibration confirming a verified match.
- **Use Case 2: Night-Time / Glare Commuting**:
  At night or under harsh halogen streetlights where route placards are overexposed or reflective, OpenCV CLAHE normalizes the image contrast, allowing Tesseract to read the board accurately.
- **Use Case 3: Offline Transit in Low-Network Areas**:
  At bus depots or rural transit hubs where cellular data drops, the device functions 100% locally with its built-in in-memory route dictionary.
- **Use Case 4: Field Testing & Benchmarking**:
  Transit authorities or engineering teams can drop batches of photos into the web dashboard's Batch Test Harness to verify system accuracy and latency across hundreds of bus photos in real time.
