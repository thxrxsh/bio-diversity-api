
# Biodiversity Detection API

A **FastAPI-based backend system** for wildlife monitoring that detects **leopard presence from audio recordings** and generates **real-time alerts** for potential wildlife risk events.

The system processes both **uploaded recordings** and **live audio streams**, performs **machine learning inference**, estimates **distance to the detected animal**, and produces **alert incidents** that can be visualized on a map or dashboard.

---

# Features

- Leopard detection using a trained **TensorFlow/Keras model**
- **Audio preprocessing and windowing** for inference
- **Distance estimation** based on acoustic features
- **Live monitoring sessions**
- **Automated alert generation**
- **Risk scoring and severity classification**
- **Alert-based map visualization**
- **Detection history for recordings and live sessions**
- Clean **FastAPI modular architecture**

---

# System Architecture

The backend follows a modular layered structure:

```
app/
│
├── api/routes        # FastAPI route handlers
│
├── core              # Configuration and shared dependencies
│
├── db                # Database connection
│
├── models            # SQLAlchemy models
│
├── schemas           # Pydantic schemas
│
├── services          # Business logic layer
│
├── main.py           # FastAPI application entrypoint
│
tests/                # Test scripts
model/                # Trained ML model
```

---

# Core Concepts

## Recording Analysis
Users can upload an audio recording which will be:

1. split into **3-second windows**
2. processed by the **ML model**
3. analyzed for **leopard probability**
4. distance estimated
5. summarized into a **recording result**

---

## Live Sessions
A live monitoring session represents a **continuous audio stream** from a device.

Each uploaded chunk:

- is analyzed by the ML model
- stored as a **LiveChunk**
- updates the **LiveSession summary**

If a leopard is detected, the system **creates or updates an alert**.

---

## Alerts

Alerts represent **wildlife incidents** and are generated from **live sessions**.

Each alert contains:

- alert ID
- detection timestamp
- risk score
- severity
- priority
- location
- session reference

Alerts power both:

- **alert lists**
- **map visualizations**

---

# Alert Risk Scoring

Risk score is calculated from:

- leopard confidence
- estimated distance
- distance confidence

Example scoring:

```
confidence contribution
+ distance confidence
+ proximity factor
```

Score range:

```
0 – 100
```

Severity levels:

| Score | Severity |
|-----|-----|
| 85+ | Critical |
| 65+ | High |
| 40+ | Medium |
| <40 | Low |

---

# API Endpoints

## Recordings

Upload and analyze recordings.

```
POST /recordings
GET /recordings/{recording_id}
GET /recordings/{recording_id}/chunks
```

---

## Live Sessions

Manage live monitoring streams.

```
POST /live-sessions
POST /live-sessions/{session_id}/chunks
GET /live-sessions/{session_id}
GET /live-sessions/{session_id}/chunks
POST /live-sessions/{session_id}/end
```

---

## Alerts

Retrieve wildlife incident alerts.

```
GET /alerts
GET /alerts/{alert_id}
```

Alert list example:

```json
{
  "alert_id": "36LVZY",
  "detected_at": "2026-03-07T10:12:21",
  "status": "new",
  "severity": "high",
  "location": {
    "latitude": 7.1123,
    "longitude": 80.5671
  }
}
```

---

## History

Retrieve detection history.

```
GET /history
GET /history/recordings
GET /history/live-sessions
```

---

# Machine Learning Model

The system uses a **TensorFlow / Keras model** stored in:

```
model/best_leopard_model.h5
```

The model predicts:

- leopard
- non-leopard

with probability outputs.

---

# Installation

Clone the repository.

```
git clone https://github.com/thxrxsh/bio-diversity-api.git
cd bio-diversity-api
```

Ensure Python 3.12.7 is available via pyenv.

```
pyenv install 3.12.7   # skip if already installed
pyenv local 3.12.7
```


Create a virtual environment.

```
~/.pyenv/versions/3.12.7/bin/python -m venv venv
source venv/bin/activate
```

Install dependencies.

```
pip install -r requirements.txt
```

---

# Running the API

Start the FastAPI server.

```
uvicorn app.main:app --reload
```

Open API docs:

```
http://127.0.0.1:8000/docs
```

---

# Example Workflow

1. Start live monitoring

```
POST /live-sessions
```

2. Send audio chunks

```
POST /live-sessions/{id}/chunks
```

3. Leopard detected → alert generated

4. Retrieve alerts

```
GET /alerts
```

5. Display alerts on map or dashboard

---

# Testing

Basic tests can be run from the `tests` folder.

Example:

```
python tests/test_inference.py
```

---

# Technologies Used

- FastAPI
- SQLAlchemy
- Pydantic
- TensorFlow / Keras
- Librosa
- NumPy

---

# Future Improvements

Possible enhancements:

- real-time streaming ingestion
- multi-species detection
- GPS clustering
- alert deduplication
- mobile device integration
- geofencing alerts
- wildlife movement analytics

---

# License

Private Project - All Rights Received
